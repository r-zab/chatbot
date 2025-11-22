# app/services/data_service.py
import json
import unicodedata
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
            print("SUKCES: Załadowano dane TERYT i IMGW.")
        except FileNotFoundError:
            print("BŁĄD: Brak plików danych. Uruchom skrypty prepare_teryt.py i create_station_map.py.")
            self.terc_dict = {}
            self.simc_dict = {}
            self.map_simc_to_synop = {}

    def _load_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _normalize(self, text: str):
        text = text.lower()
        text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
        return text.strip()

    def validate_and_get_id(self, entities: dict, intent: str, original_text: str = "") -> str | None:
        """Znajduje ID stacji (dla pogody) lub kod TERYT powiatu (dla ostrzeżeń)."""
        candidates = []

        # 1. Kandydaci z NLP (spaCy)
        if entities.get('placeName'):
            candidates.extend([self._normalize(p) for p in entities['placeName']])

        # 2. Kandydaci z tekstu ("na piechotę")
        if original_text:
            normalized_full = self._normalize(original_text)
            candidates.append(normalized_full)
            candidates.extend(normalized_full.split())

        # 3. Walidacja w zależności od intencji
        if intent == 'ostrzeżenia':
            # Dla ostrzeżeń szukamy POWIATU w słowniku TERC
            for place in candidates:
                # Sprawdzamy wprost nazwę, np. "powiat poznanski"
                if place in self.terc_dict:
                    return self.terc_dict[place]

                # Sprawdzamy z dopiskiem "powiat", np. użytkownik wpisał "Poznań" -> szukamy "powiat poznan"
                # (bo ostrzeżenia są per powiat, a nie per miasto)
                place_with_prefix = f"powiat {place}"
                if place_with_prefix in self.terc_dict:
                    return self.terc_dict[place_with_prefix]

        elif intent == 'pogoda':
            for place in candidates:
                if place in self.simc_dict:
                    simc_id = self.simc_dict[place]
                    if simc_id in self.map_simc_to_synop:
                        return self.map_simc_to_synop[simc_id]

        # Fallback dla hydro (na sztywno dla przykładu, bo brak mapy rzek)
        if intent == 'hydro':
            if 'warszaw' in original_text.lower(): return '152210170'

        return None

    async def fetch_data(self, intent: str, location_id: str) -> str:
        try:
            if intent == 'pogoda':
                data = await self.imgw_client.get_synop_data(location_id)
                return f"📍 Pogoda w {data['stacja']}: {data.get('temperatura', '?')}°C, " \
                       f"wiatr: {data.get('predkosc_wiatru', 0)} m/s, ciśnienie: {data.get('cisnienie', '?')} hPa."

            elif intent == 'hydro':
                data = await self.imgw_client.get_hydro_data(location_id)
                return f"💧 Stan wody ({data.get('rzeka', 'rzeka')}, stacja {data.get('stacja', '?')}): " \
                       f"{data.get('stan_wody', '?')} cm."

            elif intent == 'ostrzeżenia':
                # location_id to tutaj kod TERYT powiatu (np. "3021" dla powiatu poznańskiego)
                all_warnings = await self.imgw_client.get_meteo_warnings()

                # Endpoint /meteo/worn zwraca listę obiektów. Musimy znaleźć te pasujące do naszego TERYT.
                found_alerts = []

                # UWAGA: Struktura JSON z IMGW /meteo/worn jest specyficzna.
                # Zazwyczaj obiekt ma pole 'kod_teryt' lub podobne.
                # Tutaj iterujemy i sprawdzamy czy nasz location_id jest w danych ostrzeżenia.

                if isinstance(all_warnings, dict) and 'komunikat' in all_warnings:
                    return f"IMGW zwraca komunikat techniczny: {all_warnings['komunikat']}"

                count = 0
                for warning in all_warnings:
                    # Sprawdzamy czy kod powiatu jest w liście powiatów tego ostrzeżenia
                    # (IMGW często zwraca listę 'powiaty': ['kod1', 'kod2'...])
                    teryt_list = warning.get('powiaty_kod', [])

                    # Czasem jest to string, czasem lista
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
                    return f"✅ Brak aktywnych ostrzeżeń meteo dla powiatu (TERYT: {location_id})."

        except Exception as e:
            return f"Błąd pobierania danych: {str(e)}"

        return "Nieznana intencja."