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
        self.geolocator = Nominatim(user_agent="pogodowy_stroz_bot_v5")

        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "data"

        # STOPWORDS
        self.STOPWORDS = {
            'w', 'na', 'z', 'do', 'od', 'dla', 'koło', 'obok', 'przy', 'pod', 'nad',
            'o', 'i', 'a', 'czy', 'jak', 'jaka', 'jaki', 'jakie', 'ile',
            'jest', 'bedzie', 'będzie', 'było', 'była', 'sa', 'są',
            'podaj', 'pokaz', 'pokaż', 'sprawdz', 'sprawdź', 'zobacz', 'daj', 'powiedz',
            'pogoda', 'pogode', 'pogody', 'pogodzie', 'pogodę',
            'temperatura', 'temperaturze', 'temperaturę', 'temperature',
            'prognoza', 'prognozie', 'prognozę',
            'ostrzezenia', 'ostrzeżenia', 'ostrzeżenie', 'ostrzezenie',
            'alert', 'alerty', 'alarm', 'alarmy',
            'stan', 'stany', 'stanu', 'stanów',
            'woda', 'wody', 'wodzie', 'wodę',
            'poziom', 'poziomu', 'poziomie',
            'rzeka', 'rzeki', 'rzece', 'rzekę', 'rzeką',
            'wodowskaz', 'wodowskazu',
            'jutro', 'dzis', 'dziś', 'dzisiaj', 'teraz',
            'stopni', 'stopien', 'stopień',
            'predkosc', 'prędkość', 'kierunek',
            'wiatr', 'wiatru', 'wietrze',
        }

        # 🔥 MAPOWANIE ODMIAN RZEK → forma podstawowa (znormalizowana)
        self.RIVER_LEMMAS = {
            # Wisła (wszystkie odmiany!)
            'wisle': 'wisla', 'wisły': 'wisla', 'wiśle': 'wisla',
            'wisłą': 'wisla', 'wisłę': 'wisla', 'wisla': 'wisla',
            'wisła': 'wisla', 'wiślę': 'wisla',
            # San
            'sanie': 'san', 'sanu': 'san', 'sanem': 'san',
            # Odra
            'odrze': 'odra', 'odry': 'odra', 'odrą': 'odra',
            # Warta
            'warcie': 'warta', 'warty': 'warta', 'wartą': 'warta',
            # Narew
            'narwi': 'narew', 'narwią': 'narew', 'narwię': 'narew',
            # Bug
            'bugu': 'bug', 'bugiem': 'bug',
            # Noteć
            'noteci': 'notec', 'notecią': 'notec', 'noteć': 'notec',
            # Pilica
            'pilicy': 'pilica', 'pilicą': 'pilica', 'pilicę': 'pilica',
            # Dunajec
            'dunajcu': 'dunajec', 'dunajca': 'dunajec', 'dunajcem': 'dunajec',
            # Nysa
            'nysie': 'nysa', 'nysy': 'nysa', 'nysą': 'nysa',
            # Bóbr
            'bobrze': 'bobr', 'bobru': 'bobr', 'bóbr': 'bobr', 'bobr': 'bobr',
            # Wieprz
            'wieprza': 'wieprz', 'wieprzu': 'wieprz', 'wierzem': 'wieprz',
            # Prosna
            'prośnie': 'prosna', 'prosny': 'prosna',
            # Bzura
            'bzurze': 'bzura', 'bzury': 'bzura',
            # Brda
            'brdzie': 'brda', 'brdy': 'brda',
            # Gwda
            'gwdzie': 'gwda', 'gwdy': 'gwda',
            # Drwęca
            'drwęcy': 'drweca', 'drwecą': 'drweca', 'drweca': 'drweca',
            # Raba
            'rabie': 'raba', 'raby': 'raba',
            # Poprad
            'popradzie': 'poprad', 'popradu': 'poprad',
            # Soła
            'sole': 'sola', 'soły': 'sola', 'soła': 'sola',
            # Skawa
            'skawie': 'skawa', 'skawy': 'skawa',
            # Ner
            'nerze': 'ner', 'neru': 'ner',
            # Barycz
            'baryczy': 'barycz', 'baryczą': 'barycz',
            # Tanew
            'tanwi': 'tanew', 'tanwią': 'tanew',
            # Kamienna
            'kamiennej': 'kamienna', 'kamienną': 'kamienna',
            # Widawka
            'widawce': 'widawka', 'widawki': 'widawka',
        }

        # 🔥🔥🔥 KLUCZOWE: HARDCODED ID dla głównych rzek
        # To jest NADRZĘDNE wobec map_hydro.json!
        # Sprawdź w API IMGW jakie są prawidłowe ID dla tych rzek
        self.MAIN_RIVERS_IDS = {
            # Format: 'nazwa_znormalizowana': 'id_z_api_imgw'
            # Te ID musisz sprawdzić w swoim map_hydro.json lub w API!
            # Poniżej są przykładowe - MUSISZ je zweryfikować

            # Wisła - główna rzeka, NIE Wiślina!
            'wisla': None,  # Zostanie wypełnione z map_hydro
            'odra': None,
            'warta': None,
            'bug': None,
            'narew': None,
            'san': None,
            'notec': None,
            'pilica': None,
            'dunajec': None,
            'bobr': None,
            'nysa': None,
            'wieprz': None,
            'prosna': None,
            'bzura': None,
            'brda': None,
            'gwda': None,
            'drweca': None,
            'raba': None,
            'poprad': None,
            'sola': None,
            'skawa': None,
            'ner': None,
            'barycz': None,
            'tanew': None,
            'kamienna': None,
            'widawka': None,
        }

        # Ładowanie danych
        try:
            raw_terc = self._load_json(data_dir / "terc_dict.json")
            self.terc_dict = {self._normalize(k): v for k, v in raw_terc.items()}

            raw_simc = self._load_json(data_dir / "simc_dict.json")
            self.simc_dict = {self._normalize(k): v for k, v in raw_simc.items()}

            self.map_simc_to_synop = self._load_json(data_dir / "map_simc_to_imgw_synop.json")

            try:
                raw_hydro = self._load_json(data_dir / "map_hydro.json")
                self.map_hydro = {self._normalize(k): v for k, v in raw_hydro.items()}

                # 🔥 Wypełnij MAIN_RIVERS_IDS z map_hydro
                self._populate_main_rivers()

            except Exception as e:
                print(f"⚠️ Błąd ładowania map_hydro: {e}")
                self.map_hydro = {}

            try:
                self.station_coords = self._load_json(data_dir / "station_coords.json")
            except:
                self.station_coords = {}

            print(f"✅ Załadowano: {len(self.simc_dict)} miast, {len(self.map_hydro)} rzek")

        except Exception as e:
            print(f"❌ BŁĄD: {e}")
            self.terc_dict = {}
            self.simc_dict = {}
            self.map_simc_to_synop = {}
            self.map_hydro = {}
            self.station_coords = {}

    def _populate_main_rivers(self):
        """
        🔥 Wypełnia MAIN_RIVERS_IDS z map_hydro.json
        Szuka DOKŁADNYCH dopasowań dla głównych rzek.
        """
        print("🏞️ Mapowanie głównych rzek:")

        for river_name in list(self.MAIN_RIVERS_IDS.keys()):
            # Szukaj dokładnego dopasowania w map_hydro
            if river_name in self.map_hydro:
                self.MAIN_RIVERS_IDS[river_name] = self.map_hydro[river_name]
                print(f"   ✅ {river_name} → {self.map_hydro[river_name]}")
            else:
                # Spróbuj z polskimi znakami
                alternatives = [
                    river_name,
                    river_name.replace('a', 'ą'),
                    river_name.replace('e', 'ę'),
                    river_name.replace('o', 'ó'),
                    river_name.replace('c', 'ć'),
                    river_name.replace('n', 'ń'),
                    river_name.replace('s', 'ś'),
                    river_name.replace('z', 'ź'),
                    river_name.replace('z', 'ż'),
                    river_name.replace('l', 'ł'),
                ]

                found = False
                for alt in alternatives:
                    norm_alt = self._normalize(alt)
                    if norm_alt in self.map_hydro:
                        self.MAIN_RIVERS_IDS[river_name] = self.map_hydro[norm_alt]
                        print(f"   ✅ {river_name} → {self.map_hydro[norm_alt]} (via {alt})")
                        found = True
                        break

                if not found:
                    print(f"   ⚠️ {river_name} - nie znaleziono w map_hydro!")

    def _load_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _normalize(self, text: str) -> str:
        """Normalizuje tekst: małe litery, bez polskich znaków."""
        if not text:
            return ""
        text = text.lower().strip()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        text = text.replace("?", "").replace(".", "").replace(",", "").replace("!", "")
        return text.strip()

    def _normalize_river(self, name: str) -> str:
        """Normalizuje odmianę nazwy rzeki do formy podstawowej."""
        norm = self._normalize(name)
        return self.RIVER_LEMMAS.get(norm, norm)

    def _generate_candidates(self, text: str) -> list[str]:
        """Generuje kandydatów lokalizacji z tekstu."""
        norm_text = self._normalize(text)
        words = [
            w for w in norm_text.split()
            if w not in self.STOPWORDS and len(w) >= 2  # 🔥 Zmienione na >= 2 dla "Bug", "Ner"
        ]

        candidates = []

        # Bigramy
        if len(words) > 1:
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i + 1]}"
                candidates.append(bigram)

        # Pojedyncze słowa
        candidates.extend(words)

        # Usuń duplikaty
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        print(f"   📝 Kandydaci: {unique}")
        return unique

    def get_nearest_station(self, city_name: str) -> dict | None:
        """Znajduje najbliższą stację pogodową."""
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
        print(f"\n   🔎 validate_and_get_id(intent={intent})")

        # Zbierz kandydatów
        nlp_candidates = []
        if entities.get('placeName'):
            nlp_candidates.extend([self._normalize(p) for p in entities['placeName']])
        if entities.get('geogName'):
            nlp_candidates.extend([self._normalize(g) for g in entities['geogName']])

        text_candidates = self._generate_candidates(original_text)
        all_candidates = nlp_candidates + text_candidates
        all_candidates = list(dict.fromkeys(all_candidates))

        print(f"      Kandydaci: {all_candidates}")

        # ==================== HYDRO ====================
        if intent == 'hydro':
            for candidate in all_candidates:
                if len(candidate) < 2:
                    continue

                # 🔥 KROK 1: Normalizuj odmianę (np. "Wiśle" → "wisla")
                normalized = self._normalize_river(candidate)
                print(f"      Próba: '{candidate}' → '{normalized}'")

                # 🔥 KROK 2: NAJPIERW sprawdź główne rzeki (HARDCODED)
                # To zapobiega fuzzy matching "wisla" → "wislina"!
                if normalized in self.MAIN_RIVERS_IDS:
                    river_id = self.MAIN_RIVERS_IDS[normalized]
                    if river_id:
                        print(f"      ✅ GŁÓWNA RZEKA: {normalized} → {river_id}")
                        return {
                            "type": "hydro",
                            "id": river_id,
                            "name": normalized.title()
                        }
                    else:
                        print(f"      ⚠️ Główna rzeka '{normalized}' nie ma ID w map_hydro!")

                # 🔥 KROK 3: Dokładne dopasowanie w map_hydro
                if normalized in self.map_hydro:
                    print(f"      ✅ Dokładne: {normalized}")
                    return {
                        "type": "hydro",
                        "id": self.map_hydro[normalized],
                        "name": normalized.title()
                    }

                # 🔥 KROK 4: Fuzzy matching TYLKO dla nieznanych rzek
                # I TYLKO jeśli to NIE jest główna rzeka!
                if normalized not in self.MAIN_RIVERS_IDS:
                    all_hydro = list(self.map_hydro.keys())

                    # 🔥 WYŻSZY PRÓG - 95% podobieństwa!
                    cutoff = 0.95

                    matches = difflib.get_close_matches(normalized, all_hydro, n=1, cutoff=cutoff)
                    if matches:
                        matched = matches[0]
                        # 🔥 Dodatkowa walidacja - nie dopasowuj do głównych rzek przez fuzzy!
                        if matched not in self.MAIN_RIVERS_IDS:
                            print(f"      ✅ Fuzzy: {normalized} → {matched}")
                            return {
                                "type": "hydro",
                                "id": self.map_hydro[matched],
                                "name": matched.title()
                            }

            print(f"      ❌ Nie znaleziono rzeki")
            return None

        # ==================== POGODA ====================
        elif intent == 'pogoda':
            all_cities = list(self.simc_dict.keys())

            for candidate in all_candidates:
                if len(candidate) < 3:
                    continue

                # Dokładne dopasowanie
                if candidate in all_cities:
                    simc_id = self.simc_dict[candidate]
                    if simc_id in self.map_simc_to_synop:
                        return {
                            "type": "direct",
                            "id": self.map_simc_to_synop[simc_id],
                            "name": candidate.title()
                        }

                # Fuzzy
                matches = difflib.get_close_matches(candidate, all_cities, n=1, cutoff=0.85)
                if matches:
                    best = matches[0]
                    simc_id = self.simc_dict[best]
                    if simc_id in self.map_simc_to_synop:
                        print(f"      ✅ Miasto: {best}")
                        return {
                            "type": "direct",
                            "id": self.map_simc_to_synop[simc_id],
                            "name": best.title()
                        }

            # Fallback - najbliższa stacja
            if all_candidates:
                valid = [c for c in all_candidates if c not in self.STOPWORDS and len(c) >= 4]
                if valid:
                    potential = max(valid, key=len)
                    print(f"      🔄 Geolokalizacja: {potential}")
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
                        print(f"      ✅ Powiat: {matched}")
                        return {
                            "type": "teryt",
                            "id": self.terc_dict[matched],
                            "name": matched.title()
                        }

            return None

        return None

    async def fetch_data(self, intent: str, location_data: dict) -> str:
        """Pobiera dane z API IMGW."""
        try:
            loc_id = location_data['id']
            loc_name = location_data.get('name', 'Nieznane')

            if intent == 'pogoda':
                prefix = ""
                if location_data.get('type') == 'nearest':
                    user_city = location_data.get('user_city', '?').title()
                    station_name = location_data.get('station_name', '?')
                    distance = location_data.get('distance', '?')
                    prefix = f"📍 Najbliższa stacja: **{station_name}** ({distance} km od {user_city}).\n\n"

                data = await self.imgw_client.get_synop_data(loc_id)
                if isinstance(data, list):
                    data = data[0] if data else {}

                temp = data.get('temperatura', '?')
                wind = data.get('predkosc_wiatru', 0)
                rain = data.get('suma_opadu', 0)
                return f"{prefix}🌡️ {temp}°C, 💨 {wind} m/s, 🌧️ {rain} mm"

            elif intent == 'hydro':
                data = await self.imgw_client.get_hydro_data(loc_id)
                if isinstance(data, list):
                    data = data[0] if data else {}

                river = data.get('rzeka', loc_name)
                station = data.get('stacja', '?')
                water_level = data.get('stan_wody', '?')
                return f"💧 Rzeka: **{river}**, Stacja: {station}, Stan: **{water_level} cm**"

            elif intent == 'ostrzeżenia':
                warnings = await self.imgw_client.get_meteo_warnings()
                if isinstance(warnings, dict):
                    return "❌ Błąd API ostrzeżeń."

                found = []
                for w in warnings:
                    codes = w.get('powiaty_kod', [])
                    if isinstance(codes, str):
                        codes = [codes]
                    if loc_id in codes:
                        zjawisko = w.get('zjawisko', 'Alert')
                        stopien = w.get('stopien', 1)
                        found.append(f"⚠️ {zjawisko} (stopień {stopien})")

                if found:
                    return "\n".join(found)
                return f"✅ Brak ostrzeżeń dla: **{loc_name}**."

        except Exception as e:
            print(f"❌ Błąd: {e}")
            return f"❌ Błąd: {e}"

        return "❓ Nieznana intencja."