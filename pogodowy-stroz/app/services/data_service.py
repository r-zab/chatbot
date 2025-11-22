# app/services/data_service.py
import json
import unicodedata
import difflib
from pathlib import Path
from app.api.imgw_client import ImgwApiClient

class DataService:
    def __init__(self):
        self.imgw_client = ImgwApiClient()

        # Ścieżki do plików JSON (absolutne)
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "data"

        try:
            self.terc_dict = self._load_json(data_dir / "terc_dict.json")
            self.simc_dict = self._load_json(data_dir / "simc_dict.json")
            self.map_simc_to_synop = self._load_json(data_dir / "map_simc_to_imgw_synop.json")
            self.map_hydro = self._load_json(data_dir / "map_hydro.json")
            print("SUKCES: Załadowano wszystkie słowniki danych (SIMC, TERC, Mapy).")
        except FileNotFoundError as e:
            print(f"BŁĄD: Brak pliku danych: {e}. Upewnij się, że wygenerowano pliki JSON.")
            self.terc_dict = {}
            self.simc_dict = {}
            self.map_simc_to_synop = {}
            self.map_hydro = {}

    def _load_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _normalize(self, text: str):
        if not text: return ""
        text = text.lower()
        text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
        return text.strip()

    def validate_and_get_id(self, original_text: str, intent: str) -> str | None:
        """
        Metoda 'pancerna'. Przyjmuje tekst użytkownika i intencję.
        Zwraca ID (stacji synoptycznej, hydro lub kod powiatu TERYT) lub None.
        """
        normalized_text = self._normalize(original_text)
        words = normalized_text.split()

        # Lista potencjalnych kandydatów z tekstu (pojedyncze słowa + cały tekst)
        # Dla lepszego działania można by generować n-gramy, ale tu wystarczy proste podejście + difflib
        candidates = words + [normalized_text]

        if intent == 'pogoda':
            # 1. Szukanie dokładne w simc_dict
            for word in candidates:
                if word in self.simc_dict:
                    simc_id = self.simc_dict[word]
                    if simc_id in self.map_simc_to_synop:
                        return self.map_simc_to_synop[simc_id]

            # 2. Fuzzy match (jeśli nie znaleziono dokładnie)
            # Szukamy najlepszego dopasowania dla każdego słowa w kluczach simc_dict
            # Uwaga: To może być wolne dla ogromnych słowników, ale simc_dict ma "tylko" miasta
            # Optymalizacja: Szukamy tylko jeśli słowo ma sensowną długość > 3
            all_cities = list(self.simc_dict.keys())
            for word in candidates:
                if len(word) > 3:
                    matches = difflib.get_close_matches(word, all_cities, n=1, cutoff=0.85)
                    if matches:
                        best_city = matches[0]
                        simc_id = self.simc_dict[best_city]
                        if simc_id in self.map_simc_to_synop:
                            return self.map_simc_to_synop[simc_id]

        elif intent == 'ostrzeżenia':
            # Szukamy w terc_dict. Klucze to np. "powiat poznanski", "poznan", "warszawa"
            # Musimy sprawdzić wariacje: "powiat X" oraz samo "X"

            for word in candidates:
                # Sprawdzamy wprost
                if word in self.terc_dict:
                    return self.terc_dict[word]

                # Sprawdzamy z prefixem "powiat"
                powiat_key = f"powiat {word}"
                if powiat_key in self.terc_dict:
                    return self.terc_dict[powiat_key]

                # Fuzzy match dla powiatów
                all_powiats = list(self.terc_dict.keys())
                matches = difflib.get_close_matches(word, all_powiats, n=1, cutoff=0.8)
                if matches:
                    return self.terc_dict[matches[0]]

                matches_powiat = difflib.get_close_matches(powiat_key, all_powiats, n=1, cutoff=0.8)
                if matches_powiat:
                    return self.terc_dict[matches_powiat[0]]

        elif intent == 'hydro':
            # Szukamy w map_hydro (klucze to rzeki i stacje)
            for word in candidates:
                if word in self.map_hydro:
                    return self.map_hydro[word]

            # Fuzzy match dla hydro
            all_hydro_keys = list(self.map_hydro.keys())
            for word in candidates:
                 if len(word) > 3:
                    matches = difflib.get_close_matches(word, all_hydro_keys, n=1, cutoff=0.8)
                    if matches:
                        return self.map_hydro[matches[0]]

        return None

    async def fetch_data(self, intent: str, location_id: str) -> str:
        try:
            if intent == 'pogoda':
                data = await self.imgw_client.get_synop_data(location_id)
                return f"📍 Pogoda w {data['stacja']}: {data.get('temperatura', '?')}°C, " \
                       f"wiatr: {data.get('predkosc_wiatru', 0)} m/s, ciśnienie: {data.get('cisnienie', '?')} hPa."

            elif intent == 'hydro':
                data = await self.imgw_client.get_hydro_data(location_id)
                # FIX: The hydro endpoint sometimes returns a list of objects if multiple measurements?
                # Or maybe just one object. Let's handle both or inspect the data structure.
                # Checking the response structure from IMGW hydro endpoint...
                # /hydro/id/{id} returns a SINGLE object:
                # {"id_stacji": "...", "stacja": "...", "rzeka": "...", "stan_wody": "...", "stan_wody_data_pomiaru": "..."}

                # BUT, sometimes if there are issues it might be different.
                # However, the error in the logs was "AttributeError: 'list' object has no attribute 'get'"
                # This suggests `data` is a list.

                if isinstance(data, list):
                    if len(data) > 0:
                        data = data[0]
                    else:
                        return "Brak danych hydrologicznych dla tej stacji."

                return f"💧 Stan wody ({data.get('rzeka', 'rzeka')}, stacja {data.get('stacja', '?')}): " \
                       f"{data.get('stan_wody', '?')} cm."

            elif intent == 'ostrzeżenia':
                # location_id to tutaj kod TERYT powiatu (np. "3021" dla powiatu poznańskiego)
                all_warnings = await self.imgw_client.get_meteo_warnings()

                # Endpoint /meteo/worn zwraca listę obiektów. Musimy znaleźć te pasujące do naszego TERYT.
                found_alerts = []

                if isinstance(all_warnings, dict) and 'komunikat' in all_warnings:
                    # IMGW czasem zwraca obiekt z komunikatem o błędzie/statusie
                    return f"IMGW zwraca komunikat techniczny: {all_warnings['komunikat']}"

                count = 0
                for warning in all_warnings:
                    # Sprawdzamy czy kod powiatu jest w liście powiatów tego ostrzeżenia
                    # (IMGW często zwraca listę 'powiaty': ['kod1', 'kod2'...])
                    # API IMGW dla meteo/worn ma pole 'powiaty_kod' które jest listą LUB stringiem
                    teryt_list = warning.get('powiaty_kod', [])

                    if isinstance(teryt_list, str):
                        teryt_list = [teryt_list]

                    if location_id in teryt_list:
                        lvl = warning.get('stopien', '1')
                        type_name = warning.get('zjawisko', 'Nieznane zjawisko')
                        prawdopodobienstwo = warning.get('prawdopodobienstwo', '?')
                        found_alerts.append(f"⚠️ {type_name} (Stopień {lvl}, prawdob.: {prawdopodobienstwo}%)")
                        count += 1

                if count > 0:
                    return f"Znaleziono {count} aktywne ostrzeżenia dla Twojego powiatu:\n" + "\n".join(found_alerts)
                else:
                    # Jeśli mamy pewność co do powiatu, ale brak ostrzeżeń
                    return f"✅ Brak aktywnych ostrzeżeń meteo dla powiatu (TERYT: {location_id})."

        except Exception as e:
            return f"Błąd pobierania danych: {str(e)}"

        return "Nieznana intencja."
