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
        self.geolocator = Nominatim(user_agent="pogodowy_stroz_bot")

        # Ścieżki absolutne
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "data"

        try:
            self.terc_dict = self._load_json(data_dir / "terc_dict.json")
            self.simc_dict = self._load_json(data_dir / "simc_dict.json")
            self.map_simc_to_synop = self._load_json(data_dir / "map_simc_to_imgw_synop.json")

            # Ładowanie opcjonalnych plików
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
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _normalize(self, text: str):
        if not text: return ""
        text = text.lower()
        text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
        return text.strip()

    def get_nearest_station(self, city_name: str) -> dict | None:
        if not self.station_coords: return None
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

    def validate_and_get_id(self, entities: dict, intent: str, original_text: str = "") -> str | dict | None:
        """Waliduje i zwraca ID. Przyjmuje encje i tekst."""

        # 1. Zbieramy kandydatów
        candidates = []
        if entities.get('placeName'):
            candidates.extend([self._normalize(p) for p in entities['placeName']])
        if original_text:
            norm_text = self._normalize(original_text)
            candidates.extend(norm_text.split())

        # 2. Logika dla POGODY
        if intent == 'pogoda':
            all_cities = list(self.simc_dict.keys())
            # A. Szukanie w słowniku SIMC
            for word in candidates:
                if len(word) < 3: continue
                matches = difflib.get_close_matches(word, all_cities, n=1, cutoff=0.85)
                if matches:
                    best_city = matches[0]
                    simc_id = self.simc_dict[best_city]
                    if simc_id in self.map_simc_to_synop:
                        return self.map_simc_to_synop[simc_id]

            # B. Najbliższa stacja (Geopy)
            potential_city = next((c for c in candidates if len(c) > 3), None)
            if potential_city:
                return self.get_nearest_station(potential_city)

        # 3. Logika dla OSTRZEŻEŃ
        elif intent == 'ostrzeżenia':
            all_powiats = list(self.terc_dict.keys())
            for word in candidates:
                if len(word) < 3: continue
                keys = [word, f"powiat {word}"]
                for key in keys:
                    matches = difflib.get_close_matches(key, all_powiats, n=1, cutoff=0.8)
                    if matches: return self.terc_dict[matches[0]]

        # 4. Logika dla HYDRO
        elif intent == 'hydro':
            all_hydro = list(self.map_hydro.keys())
            for word in candidates:
                if len(word) < 3: continue
                matches = difflib.get_close_matches(word, all_hydro, n=1, cutoff=0.8)
                if matches: return self.map_hydro[matches[0]]

        return None

    async def fetch_data(self, intent: str, location_id: str | dict) -> str:
        try:
            if intent == 'pogoda':
                station_id = location_id
                prefix = ""
                if isinstance(location_id, dict) and location_id.get('type') == 'nearest':
                    station_id = location_id['id']
                    prefix = f"📍 Brak stacji w {location_id['user_city'].title()}. Dane z: **{location_id['station_name']}** ({location_id['distance']}km).\n"

                data = await self.imgw_client.get_synop_data(station_id)
                if isinstance(data, list): data = data[0] if data else {}

                return prefix + f"🌡️ {data.get('temperatura', '?')}°C, 💨 {data.get('predkosc_wiatru', 0)} m/s, 🌧️ {data.get('suma_opadu', 0)} mm"

            elif intent == 'hydro':
                data = await self.imgw_client.get_hydro_data(location_id)
                if isinstance(data, list): data = data[0] if data else {}
                return f"💧 {data.get('rzeka', '?')} ({data.get('stacja', '?')}): {data.get('stan_wody', '?')} cm"

            elif intent == 'ostrzeżenia':
                warnings = await self.imgw_client.get_meteo_warnings()
                if isinstance(warnings, dict): return "Błąd API Ostrzeżeń."

                found = []
                for w in warnings:
                    codes = w.get('powiaty_kod', [])
                    if isinstance(codes, str): codes = [codes]
                    if location_id in codes:
                        found.append(f"⚠️ {w.get('zjawisko', 'Alert')} (st. {w.get('stopien', 1)})")

                return "\n".join(found) if found else f"✅ Brak ostrzeżeń dla powiatu ({location_id})."

        except Exception as e:
            return f"Błąd pobierania: {e}"
        return "Nieznana intencja."