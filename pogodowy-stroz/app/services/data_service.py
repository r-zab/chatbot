# app/services/data_service.py
import json
import unicodedata
import difflib
import logging
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from app.api.imgw_client import ImgwApiClient


class DataService:
    def __init__(self):
        self.imgw_client = ImgwApiClient()
        self.geolocator = Nominatim(user_agent="pogodowy_stroz_bot_v3")

        # Ścieżki absolutne
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "data"

        # Słowa do ignorowania (żeby "Pogoda" nie była traktowana jak miasto)
        self.STOPWORDS = {
            'pogoda', 'pogode', 'pogody', 'jaka', 'jest', 'bedzie', 'temperatura',
            'w', 'na', 'z', 'do', 'od', 'dla', 'koło', 'obok',
            'ostrzezenia', 'ostrzeżenie', 'alert', 'alarm',
            'stan', 'stany', 'wody', 'poziom', 'rzeka', 'rzeki', 'wodowskaz',
            'czy', 'burza', 'grad', 'wiatr', 'zrobisz', 'kanapke'
        }

        try:
            self.terc_dict = self._load_json(data_dir / "terc_dict.json")
            self.simc_dict = self._load_json(data_dir / "simc_dict.json")
            self.map_simc_to_synop = self._load_json(data_dir / "map_simc_to_imgw_synop.json")

            try:
                self.map_hydro = self._load_json(data_dir / "map_hydro.json")
            except:
                self.map_hydro = {}

            try:
                self.station_coords = self._load_json(data_dir / "station_coords.json")
            except:
                self.station_coords = {}

            print("SUKCES: Załadowano dane.")
        except Exception as e:
            print(f"BŁĄD DANYCH: {e}")
            self.terc_dict = {}
            self.simc_dict = {}
            self.map_simc_to_synop = {}
            self.map_hydro = {}
            self.station_coords = {}

    def _load_json(self, path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)

    def _normalize(self, text: str):
        if not text: return ""
        text = text.lower()
        # Usuwanie polskich znaków
        text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
        # Usuwanie znaków interpunkcyjnych (np. pytajnik)
        text = text.replace("?", "").replace(".", "").replace(",", "").strip()
        return text

    def _generate_candidates(self, text: str):
        norm_text = self._normalize(text)
        words = [w for w in norm_text.split() if w not in self.STOPWORDS]
        candidates = []

        # 1. Pojedyncze słowa
        candidates.extend(words)

        # 2. Pary słów (bigramy)
        if len(words) > 1:
            for i in range(len(words) - 1):
                candidates.append(f"{words[i]} {words[i + 1]}")

        return list(set(candidates))

    def get_nearest_station(self, city_name: str) -> dict | None:
        if not self.station_coords or city_name in self.STOPWORDS: return None
        try:
            location = self.geolocator.geocode(f"{city_name}, Polska")
            if not location: return None

            user_coords = (location.latitude, location.longitude)
            nearest_id, min_dist, nearest_name = None, float('inf'), ""

            for s_id, data in self.station_coords.items():
                s_coords = (data['lat'], data['lon'])
                dist = geodesic(user_coords, s_coords).km
                if dist < min_dist:
                    min_dist, nearest_id, nearest_name = dist, s_id, data['name']

            if nearest_id:
                return {"type": "nearest", "id": nearest_id, "station_name": nearest_name, "user_city": city_name,
                        "distance": round(min_dist, 1)}
        except:
            return None
        return None

    def validate_and_get_id(self, entities: dict, intent: str, original_text: str = "") -> dict | None:
        """Zwraca obiekt {id, name, type}."""
        nlp_candidates = []
        if entities.get('placeName'):
            nlp_candidates.extend([self._normalize(p) for p in entities['placeName']])
        text_candidates = self._generate_candidates(original_text)
        all_candidates = nlp_candidates + text_candidates

        # --- POGODA ---
        if intent == 'pogoda':
            all_cities = list(self.simc_dict.keys())
            for word in all_candidates:
                if len(word) < 3: continue
                matches = difflib.get_close_matches(word, all_cities, n=1, cutoff=0.85)
                if matches:
                    best_city = matches[0]
                    simc_id = self.simc_dict[best_city]
                    if simc_id in self.map_simc_to_synop:
                        # Znaleziono stację wprost
                        return {"type": "direct", "id": self.map_simc_to_synop[simc_id], "name": best_city.title()}

            potential_city = max(all_candidates, key=len) if all_candidates else None
            if potential_city:
                return self.get_nearest_station(potential_city)

        # --- OSTRZEŻENIA ---
        elif intent == 'ostrzeżenia':
            all_powiats = list(self.terc_dict.keys())
            for word in all_candidates:
                keys = [word, f"powiat {word}"]
                for key in keys:
                    matches = difflib.get_close_matches(key, all_powiats, n=1, cutoff=0.8)
                    if matches:
                        matched_name = matches[0]
                        # Zwracamy ID oraz ładną nazwę powiatu
                        return {"type": "teryt", "id": self.terc_dict[matched_name], "name": matched_name.title()}

        # --- HYDRO ---
        elif intent == 'hydro':
            all_hydro = list(self.map_hydro.keys())
            for word in all_candidates:
                if len(word) < 3: continue
                # ZMIANA: Dla krótkich nazw (Odra) wymagamy 95% zgodności, dla długich 80%
                cutoff = 0.95 if len(word) < 5 else 0.8
                matches = difflib.get_close_matches(word, all_hydro, n=1, cutoff=cutoff)
                if matches:
                    return {"type": "hydro", "id": self.map_hydro[matches[0]], "name": matches[0].title()}

        return None

    async def fetch_data(self, intent: str, location_data: dict) -> str:
        try:
            loc_id = location_data['id']
            loc_name = location_data.get('name', 'Nieznane')

            if intent == 'pogoda':
                prefix = ""
                if location_data.get('type') == 'nearest':
                    prefix = f"📍 Brak stacji w: **{location_data['user_city'].title()}**.\n📉 Dane z najbliższej stacji: **{location_data['station_name']}** ({location_data['distance']} km stąd).\n"

                data = await self.imgw_client.get_synop_data(loc_id)
                if isinstance(data, list): data = data[0] if data else {}

                return prefix + f"🌡️ {data.get('temperatura', '?')}°C, 💨 {data.get('predkosc_wiatru', 0)} m/s, 🌧️ {data.get('suma_opadu', 0)} mm"

            elif intent == 'hydro':
                data = await self.imgw_client.get_hydro_data(loc_id)
                if isinstance(data, list): data = data[0] if data else {}
                return f"💧 Rzeka: {data.get('rzeka', '?')}\n📍 Stacja: {data.get('stacja', '?')}\n🌊 Stan wody: {data.get('stan_wody', '?')} cm"

            elif intent == 'ostrzeżenia':
                warnings = await self.imgw_client.get_meteo_warnings()
                if isinstance(warnings, dict): return "Błąd API Ostrzeżeń."

                found = []
                for w in warnings:
                    codes = w.get('powiaty_kod', [])
                    if isinstance(codes, str): codes = [codes]
                    if loc_id in codes:
                        found.append(f"⚠️ {w.get('zjawisko', 'Alert')} (st. {w.get('stopien', 1)})")

                # ZMIANA: Wyświetlamy nazwę powiatu zamiast kodu
                return "\n".join(found) if found else f"✅ Brak ostrzeżeń dla: {loc_name}."

        except Exception as e:
            return f"Błąd pobierania: {e}"
        return "Nieznana intencja."