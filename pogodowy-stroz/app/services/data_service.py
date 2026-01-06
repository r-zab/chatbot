# app/services/data_service.py
import json
import unicodedata
import difflib
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from app.api.imgw_client import ImgwApiClient


class DataService:
    def __init__(self):
        self.imgw_client = ImgwApiClient()
        self.geolocator = Nominatim(user_agent="pogodowy_stroz_bot_v6")

        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "data"

        # STOPWORDS
        self.STOPWORDS = {
            'w', 'na', 'z', 'do', 'od', 'dla', 'koło', 'obok', 'przy', 'pod', 'nad',
            'o', 'i', 'a', 'czy', 'jak', 'jaka', 'jaki', 'jakie', 'ile',
            'jest', 'bedzie', 'będzie', 'było', 'była', 'sa', 'są',
            'podaj', 'pokaz', 'pokaż', 'sprawdz', 'sprawdź', 'zobacz', 'daj', 'powiedz',
            'pogoda', 'pogode', 'pogody', 'pogodzie', 'pogodę',
            'temperatura', 'temperaturze', 'temperaturę',
            'prognoza', 'prognozie', 'prognozę',
            'ostrzezenia', 'ostrzeżenia', 'ostrzeżenie', 'ostrzezenie',
            'alert', 'alerty', 'alarm', 'alarmy',
            'stan', 'stany', 'stanu', 'stanów',
            'woda', 'wody', 'wodzie', 'wodę',
            'poziom', 'poziomu', 'poziomie',
            'rzeka', 'rzeki', 'rzece', 'rzekę', 'rzeką',
            'wodowskaz', 'wodowskazu',
            'jutro', 'dzis', 'dziś', 'dzisiaj', 'teraz',
        }

        # MAPOWANIE ODMIAN RZEK
        self.RIVER_LEMMAS = {
            'wisle': 'wisla', 'wisly': 'wisla', 'wisla': 'wisla',
            'wiśle': 'wisla', 'wisły': 'wisla', 'wisła': 'wisla',
            'odrze': 'odra', 'odry': 'odra', 'odrą': 'odra',
            'warcie': 'warta', 'warty': 'warta', 'wartą': 'warta',
            'sanie': 'san', 'sanu': 'san', 'sanem': 'san',
            'narwi': 'narew', 'narwią': 'narew',
            'bugu': 'bug', 'bugiem': 'bug',
            'noteci': 'notec', 'notecią': 'notec', 'noteć': 'notec',
            'pilicy': 'pilica', 'pilicą': 'pilica',
            'dunajcu': 'dunajec', 'dunajca': 'dunajec',
            'bobrze': 'bobr', 'bobru': 'bobr', 'bóbr': 'bobr',
            'nysie': 'nysa', 'nysy': 'nysa',
            'wieprza': 'wieprz', 'wieprzu': 'wieprz',
            'brdzie': 'brda', 'brdy': 'brda',
            'gwdzie': 'gwda', 'gwdy': 'gwda',
            'biebrzy': 'biebrza', 'biebrzą': 'biebrza',
        }

        # GŁÓWNE RZEKI (hardcoded)
        self.MAIN_RIVERS = {
            'wisla': '149180140',
            'odra': '153140020',
            'warta': '151180130',
            'bug': '150240010',
            'narew': '152230090',
            'san': '150210210',
            'notec': '153170100',
            'pilica': '151190090',
            'dunajec': '149200140',
            'bobr': '152150020',
            'nysa': '150170060',
            'wieprz': '151230010',
            'brda': '153170140',
            'gwda': '153160210',
            'bzura': '152190050',
            'raba': '149200090',
            'skawa': '149190290',
            'poprad': '149200220',
            'sola': '150190160',
            'drweca': '153190120',
            'ner': '151190040',
            'barycz': '151160140',
            'tanew': '150220160',
            'biebrza': '153220170',
            'pisa': '153210190',
            'lyna': '154200030',
            'slupia': '154170010',
            'parseta': '154150040',
            'rega': '153150050',
            'radunia': '154180060',
        }

        # Ładowanie danych
        try:
            raw_terc = self._load_json(data_dir / "terc_dict.json")
            self.terc_dict = {self._normalize(k): v for k, v in raw_terc.items()}
            self.terc_reverse = {v: k for k, v in raw_terc.items()}

            raw_simc = self._load_json(data_dir / "simc_dict.json")
            self.simc_dict = {self._normalize(k): v for k, v in raw_simc.items()}

            self.map_simc_to_synop = self._load_json(data_dir / "map_simc_to_imgw_synop.json")

            try:
                raw_hydro = self._load_json(data_dir / "map_hydro.json")
                self.map_hydro = {self._normalize(k): v for k, v in raw_hydro.items()}
            except:
                self.map_hydro = {}

            try:
                self.station_coords = self._load_json(data_dir / "station_coords.json")
            except:
                self.station_coords = {}

            print(f"✅ DataService: {len(self.simc_dict)} miast, {len(self.terc_dict)} powiatów")

        except Exception as e:
            print(f"❌ BŁĄD: {e}")
            self.terc_dict = {}
            self.terc_reverse = {}
            self.simc_dict = {}
            self.map_simc_to_synop = {}
            self.map_hydro = {}
            self.station_coords = {}

    def _load_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _normalize(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        text = text.replace("?", "").replace(".", "").replace(",", "").replace("!", "")
        text = text.replace("ł", "l")
        return text.strip()

    def _normalize_river(self, name: str) -> str:
        norm = self._normalize(name)
        return self.RIVER_LEMMAS.get(norm, norm)

    def _degrees_to_direction(self, degrees) -> str:
        """Konwertuje stopnie na kierunek wiatru."""
        if degrees is None or degrees == '':
            return None

        try:
            deg = float(degrees)
        except (ValueError, TypeError):
            return None

        deg = deg % 360

        directions = [
            "Północ",
            "Północny Wschód",
            "Wschód",
            "Południowy Wschód",
            "Południe",
            "Południowy Zachód",
            "Zachód",
            "Północny Zachód"
        ]

        index = int((deg + 22.5) / 45) % 8
        return directions[index]

    def _generate_candidates(self, text: str) -> list[str]:
        norm_text = self._normalize(text)
        words = [
            w for w in norm_text.split()
            if w not in self.STOPWORDS and len(w) >= 2
        ]

        candidates = []

        if len(words) > 1:
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i + 1]}"
                candidates.append(bigram)

        candidates.extend(words)

        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        return unique

    def get_nearest_station(self, city_name: str) -> dict | None:
        if not self.station_coords:
            return None

        if self._normalize(city_name) in self.STOPWORDS or len(city_name) < 3:
            return None

        try:
            location = self.geolocator.geocode(f"{city_name}, Polska")
            if not location:
                return None

            user_coords = (location.latitude, location.longitude)
            nearest_id, min_dist, nearest_name = None, float('inf'), ""

            for s_id, data in self.station_coords.items():
                s_coords = (data['lat'], data['lon'])
                dist = geodesic(user_coords, s_coords).km
                if dist < min_dist:
                    min_dist = dist
                    nearest_id = s_id
                    nearest_name = data['name']

            if nearest_id:
                return {
                    "type": "nearest",
                    "id": nearest_id,
                    "station_name": nearest_name,
                    "user_city": city_name,
                    "distance": round(min_dist, 1)
                }
        except Exception as e:
            print(f"   ⚠️ Błąd geolokalizacji: {e}")
            return None

        return None

    def validate_and_get_id(self, entities: dict, intent: str, original_text: str = "") -> dict | None:
        """Waliduje lokalizację i zwraca obiekt {id, name, type}."""
        nlp_candidates = []
        if entities.get('placeName'):
            nlp_candidates.extend([self._normalize(p) for p in entities['placeName']])
        if entities.get('geogName'):
            nlp_candidates.extend([self._normalize(g) for g in entities['geogName']])

        text_candidates = self._generate_candidates(original_text)
        all_candidates = nlp_candidates + text_candidates
        all_candidates = list(dict.fromkeys(all_candidates))

        # ==================== HYDRO ====================
        if intent == 'hydro':
            for candidate in all_candidates:
                if len(candidate) < 2:
                    continue

                normalized = self._normalize_river(candidate)

                if normalized in self.MAIN_RIVERS:
                    return {
                        "type": "hydro",
                        "id": self.MAIN_RIVERS[normalized],
                        "name": normalized.title()
                    }

                if normalized in self.map_hydro:
                    return {
                        "type": "hydro",
                        "id": self.map_hydro[normalized],
                        "name": normalized.title()
                    }

                for key in self.map_hydro.keys():
                    if key.startswith(normalized + " "):
                        return {
                            "type": "hydro",
                            "id": self.map_hydro[key],
                            "name": key.title()
                        }

            return None

        # ==================== POGODA ====================
        elif intent == 'pogoda':
            all_cities = list(self.simc_dict.keys())

            for candidate in all_candidates:
                if len(candidate) < 3:
                    continue

                if candidate in all_cities:
                    simc_id = self.simc_dict[candidate]
                    if simc_id in self.map_simc_to_synop:
                        return {
                            "type": "direct",
                            "id": self.map_simc_to_synop[simc_id],
                            "name": candidate.title()
                        }

                matches = difflib.get_close_matches(candidate, all_cities, n=1, cutoff=0.85)
                if matches:
                    best = matches[0]
                    simc_id = self.simc_dict[best]
                    if simc_id in self.map_simc_to_synop:
                        return {
                            "type": "direct",
                            "id": self.map_simc_to_synop[simc_id],
                            "name": best.title()
                        }

            # Fallback - geolokalizacja
            if all_candidates:
                valid = [c for c in all_candidates if c not in self.STOPWORDS and len(c) >= 4]
                if valid:
                    potential = max(valid, key=len)
                    return self.get_nearest_station(potential)

            return None

        # ==================== OSTRZEŻENIA ====================
        elif intent == 'ostrzeżenia':
            all_powiats = list(self.terc_dict.keys())

            for candidate in all_candidates:
                keys_to_try = [
                    candidate,
                    f"powiat {candidate}",
                    f"m. {candidate}",
                ]

                for key in keys_to_try:
                    if key in all_powiats:
                        return {
                            "type": "teryt",
                            "id": self.terc_dict[key],
                            "name": key.title()
                        }

                    matches = difflib.get_close_matches(key, all_powiats, n=1, cutoff=0.80)
                    if matches:
                        matched = matches[0]
                        return {
                            "type": "teryt",
                            "id": self.terc_dict[matched],
                            "name": matched.title()
                        }

            return None

        return None

    async def fetch_data(self, intent: str, location_data: dict) -> str:
        """Pobiera dane z API IMGW i formatuje odpowiedź."""
        try:
            loc_id = location_data['id']
            loc_name = location_data.get('name', 'Nieznane')

            # ==================== POGODA ====================
            if intent == 'pogoda':
                prefix = ""
                if location_data.get('type') == 'nearest':
                    user_city = location_data.get('user_city', '?').title()
                    station_name = location_data.get('station_name', '?')
                    distance = location_data.get('distance', '?')
                    prefix = f"📍 Najbliższa stacja: {station_name} ({distance} km od {user_city})\n\n"

                data = await self.imgw_client.get_synop_data(loc_id)
                if isinstance(data, list):
                    data = data[0] if data else {}

                station = data.get('stacja', loc_name)
                temp = data.get('temperatura', '?')
                wind_speed = data.get('predkosc_wiatru', '?')
                wind_dir_deg = data.get('kierunek_wiatru', None)
                rain = data.get('suma_opadu', '?')
                pressure = data.get('cisnienie', None)
                humidity = data.get('wilgotnosc_wzgledna', None)
                date = data.get('data_pomiaru', '')
                hour = data.get('godzina_pomiaru', '')

                wind_direction = self._degrees_to_direction(wind_dir_deg)

                # 🔥 FORMATOWANIE - kierunek w nowej linii
                response = f"{prefix}🏙️ {station}\n"
                response += f"🌡️ Temperatura: {temp}°C\n"
                response += f"💨 Wiatr: {wind_speed} m/s\n"

                if wind_direction:
                    response += f"🧭 Kierunek: {wind_direction}\n"

                response += f"🌧️ Opady: {rain} mm"

                if pressure and pressure != 'null' and pressure is not None:
                    response += f"\n🔵 Ciśnienie: {pressure} hPa"
                if humidity and humidity != 'null' and humidity is not None:
                    response += f"\n💧 Wilgotność: {humidity}%"

                if date and hour:
                    response += f"\n\n📅 Pomiar: {date}, godz. {hour}:00"

                return response

            # ==================== HYDRO ====================
            elif intent == 'hydro':
                data = await self.imgw_client.get_hydro_data(loc_id)
                if isinstance(data, list):
                    data = data[0] if data else {}

                river = data.get('rzeka', loc_name)
                station = data.get('stacja', '?')
                water_level = data.get('stan_wody', '?')
                water_temp = data.get('temperatura_wody', None)
                date = data.get('data_pomiaru', '')
                hour = data.get('godzina_pomiaru', '')

                response = f"🏞️ {river}\n"
                response += f"📍 Stacja: {station}\n"
                response += f"🌊 Stan wody: {water_level} cm"

                if water_temp and water_temp != 'null':
                    response += f"\n🌡️ Temp. wody: {water_temp}°C"

                if date and hour:
                    response += f"\n\n📅 Pomiar: {date}, godz. {hour}:00"

                return response

            # ==================== OSTRZEŻENIA ====================
            elif intent == 'ostrzeżenia':
                warnings = await self.imgw_client.get_meteo_warnings()

                if isinstance(warnings, dict):
                    return "❌ Błąd API ostrzeżeń."

                if not isinstance(warnings, list):
                    return "❌ Nieoczekiwany format danych."

                found = []

                for w in warnings:
                    teryt_codes = w.get('teryt', [])

                    if isinstance(teryt_codes, str):
                        teryt_codes = [teryt_codes]

                    if loc_id in teryt_codes:
                        nazwa = w.get('nazwa_zdarzenia', 'Alert')
                        stopien = w.get('stopien', '?')
                        od = w.get('obowiazuje_od', '')
                        do = w.get('obowiazuje_do', '')
                        tresc = w.get('tresc', '')
                        prawdop = w.get('prawdopodobienstwo', '')

                        alert = f"⚠️ {nazwa} (stopień {stopien})"

                        if prawdop:
                            alert += f"\n   📊 Prawdopodobieństwo: {prawdop}%"
                        if od:
                            alert += f"\n   🕐 Od: {od}"
                        if do:
                            alert += f"\n   🕐 Do: {do}"
                        if tresc:
                            if len(tresc) > 150:
                                tresc = tresc[:150] + "..."
                            alert += f"\n   📝 {tresc}"

                        found.append(alert)

                if found:
                    header = f"🚨 Ostrzeżenia dla {loc_name}:\n\n"
                    return header + "\n\n".join(found)

                return f"✅ Brak ostrzeżeń dla {loc_name}."

        except Exception as e:
            print(f"❌ Błąd: {e}")
            return f"❌ Błąd pobierania danych: {e}"

        return "❓ Nieznana intencja."