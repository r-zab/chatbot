# app/services/data_service.py

import json
import unicodedata
import difflib
from pathlib import Path
from typing import Optional

from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from app.api.imgw_client import ImgwApiClient


class DataService:
    def __init__(self):
        self.imgw_client = ImgwApiClient()
        self.geolocator = Nominatim(user_agent="pogodowy_stroz_bot_v6")

        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "data"

        # KODY ZJAWISK LODOWYCH
        self.ICE_PHENOMENA = {
            "0": "brak zjawisk",
            "01": "śryż", "1": "śryż",
            "02": "kra", "2": "kra",
            "03": "lód brzegowy", "3": "lód brzegowy",
            "04": "pokrywa lodowa", "4": "pokrywa lodowa",
            "05": "zator lodowy", "5": "zator lodowy",
            "06": "lód brzegowy i śryż", "6": "lód brzegowy i śryż",
            "07": "lód brzegowy i kra", "7": "lód brzegowy i kra",
            "08": "śryż i kra", "8": "śryż i kra",
            "09": "zator śryżowy", "9": "zator śryżowy",
            "32": "lód zatokowy",
            "41": "woda na lodzie",
            "42": "lód pływający (wolny od brzegów)",
            "43": "lód zmurszały (dziurawy)",
        }

        # STOPWORDS
        self.STOPWORDS = {
            "w", "na", "z", "do", "od", "dla", "koło", "obok", "przy", "pod", "nad",
            "o", "i", "a", "czy", "jak", "jaka", "jaki", "jakie", "ile",
            "jest", "bedzie", "będzie", "było", "była", "sa", "są",
            "podaj", "pokaz", "pokaż", "sprawdz", "sprawdź", "zobacz", "daj", "powiedz",
            "pogoda", "pogode", "pogody", "pogodzie", "pogodę",
            "temperatura", "temperaturze", "temperaturę",
            "prognoza", "prognozie", "prognozę",
            "ostrzezenia", "ostrzeżenia", "ostrzeżenie", "ostrzezenie",
            "alert", "alerty", "alarm", "alarmy",
            "stan", "stany", "stanu", "stanów",
            "woda", "wody", "wodzie", "wodę",
            "poziom", "poziomu", "poziomie",
            "rzeka", "rzeki", "rzece", "rzekę", "rzeką",
            "wodowskaz", "wodowskazu",
            "jutro", "dzis", "dziś", "dzisiaj", "teraz",
        }

        # MAPOWANIE ODMIAN RZEK
        self.RIVER_LEMMAS = {
            "wisle": "wisla", "wisly": "wisla", "wisla": "wisla",
            "wiśle": "wisla", "wisły": "wisla", "wisła": "wisla",
            "odrze": "odra", "odry": "odra", "odrą": "odra",
            "warcie": "warta", "warty": "warta", "wartą": "warta",
            "sanie": "san", "sanu": "san", "sanem": "san",
            "narwi": "narew", "narwią": "narew",
            "bugu": "bug", "bugiem": "bug",
            "noteci": "notec", "notecią": "notec", "noteć": "notec",
            "pilicy": "pilica", "pilicą": "pilica",
            "dunajcu": "dunajec", "dunajca": "dunajec",
            "bobrze": "bobr", "bobru": "bobr", "bóbr": "bobr",
            "nysie": "nysa", "nysy": "nysa",
            "wieprza": "wieprz", "wieprzu": "wieprz",
            "brdzie": "brda", "brdy": "brda",
            "gwdzie": "gwda", "gwdy": "gwda",
            "biebrzy": "biebrza", "biebrzą": "biebrza",
        }

        # GŁÓWNE RZEKI -> ID stacji
        self.MAIN_RIVERS = {
            "wisla": "149180140", "odra": "153140020", "warta": "151180130",
            "bug": "150240010", "narew": "152230090", "san": "150210210",
            "notec": "153170100", "pilica": "151190090", "dunajec": "149200140",
            "bobr": "152150020", "nysa": "150170060", "wieprz": "151230010",
            "brda": "153170140", "gwda": "153160210", "bzura": "152190050",
            "raba": "149200090", "skawa": "149190290", "poprad": "149200220",
            "sola": "150190160", "drweca": "153190120", "ner": "151190040",
            "barycz": "151160140", "tanew": "150220160", "biebrza": "153220170",
            "pisa": "153210190", "lyna": "154200030", "slupia": "154170010",
            "parseta": "154150040", "rega": "153150050", "radunia": "154180060",
            "elblag": "154190060", "regalica": "153140190", "wieprza": "154160150",
        }

        # WOJEWÓDZTWA
        self.VOIVODESHIPS = {
            "dolnoslaskie": "02", "dolnoslaska": "02",
            "kujawsko-pomorskie": "04", "kujawsko-pomorska": "04",
            "lubelskie": "06", "lubelska": "06",
            "lubuskie": "08", "lubuska": "08",
            "lodzkie": "10", "lodzka": "10",
            "malopolskie": "12", "malopolska": "12",
            "mazowieckie": "14", "mazowiecka": "14",
            "opolskie": "16", "opolska": "16",
            "podkarpackie": "18", "podkarpacka": "18",
            "podlaskie": "20", "podlaska": "20",
            "pomorskie": "22", "pomorska": "22",
            "slaskie": "24", "slaska": "24",
            "swietokrzyskie": "26", "swietokrzyska": "26",
            "warminsko-mazurskie": "28", "warminsko-mazurska": "28",
            "wielkopolskie": "30", "wielkopolska": "30",
            "zachodniopomorskie": "32", "zachodniopomorska": "32",
        }

        # STOLICE WOJEWÓDZTW
        self.VOIVODESHIP_CAPITALS = {
            "dolnoslaskie": "wroclaw",
            "kujawsko-pomorskie": "bydgoszcz",
            "lubelskie": "lublin",
            "lubuskie": "zielona gora",
            "lodzkie": "lodz",
            "malopolskie": "krakow",
            "mazowieckie": "warszawa",
            "opolskie": "opole",
            "podkarpackie": "rzeszow",
            "podlaskie": "bialystok",
            "pomorskie": "gdansk",
            "slaskie": "katowice",
            "swietokrzyskie": "kielce",
            "warminsko-mazurskie": "olsztyn",
            "wielkopolskie": "poznan",
            "zachodniopomorskie": "szczecin",
        }

        # 🔥 ZNANE ZAGRANICZNE MIASTA (do odrzucenia)
        self.FOREIGN_CITIES = {
            # Stolice europejskie
            "londyn", "london", "paryz", "paris", "berlin", "madryt", "madrid",
            "rzym", "roma", "rome", "wiedeń", "wien", "vienna", "praga", "prague",
            "bratysława", "bratislava", "budapeszt", "budapest", "bukareszt", "bucharest",
            "sofia", "ateny", "athens", "lizbona", "lisbon", "amsterdam", "bruksela",
            "brussels", "kopenhaga", "copenhagen", "sztokholm", "stockholm", "oslo",
            "helsinki", "dublin", "edynburg", "edinburgh", "glasgow", "manchester",
            "liverpool", "birmingham", "barcelona", "walencja", "valencia", "sewilla",
            "mediolan", "milan", "neapol", "naples", "florencja", "florence", "wenecja",
            "venice", "monachium", "munich", "frankfurt", "hamburg", "kolonia", "cologne",

            # Stolice światowe
            "waszyngton", "washington", "nowy jork", "new york", "los angeles",
            "chicago", "toronto", "ottawa", "meksyk", "mexico", "hawana", "havana",
            "buenos aires", "sao paulo", "rio de janeiro", "lima", "bogota", "santiago",
            "pekin", "beijing", "szanghaj", "shanghai", "tokio", "tokyo", "seul", "seoul",
            "bangkok", "singapur", "singapore", "hongkong", "hong kong", "tajpej", "taipei",
            "delhi", "mumbaj", "mumbai", "kalkuta", "kolkata", "dubaj", "dubai",
            "kair", "cairo", "kapsztad", "cape town", "johannesburg", "nairobi",
            "sydney", "melbourne", "canberra", "auckland", "wellington",
            "moskwa", "moscow", "petersburg", "sankt petersburg", "kijow", "kyiv", "kiev",
            "mińsk", "minsk", "wilno", "vilnius", "ryga", "riga", "tallin", "tallinn",

            # Popularne miasta turystyczne
            "dubai", "las vegas", "miami", "san francisco", "boston", "seattle",
            "vancouver", "montreal", "hawaje", "hawaii", "bali", "phuket", "maldives",
            "malediwy", "cancun", "ibiza", "majorka", "mallorca", "teneryfa", "tenerife",

            # 🔥 NOWE: Dodatkowe miasta
            "pafos", "paphos", "cypr", "cyprus", "nikozja", "nicosia",
            "larnaka", "larnaca", "limasol", "limassol",
            "zagrzeb", "zagreb", "belgrad", "beograd", "belgrade",
            "skopje", "podgorica", "tirana", "sarajewo", "sarajevo",
            "kiszyniow", "chisinau",
        }

        # WARIANTY WOJEWÓDZTW
        self.VOIVODESHIP_VARIANTS = {
            'warminsko-mazurskie': '28', 'warminsko mazurskie': '28',
            'warminskomazurskie': '28', 'warminsko-mazurskiego': '28',
            'warminsko mazurskiego': '28', 'warminskomazurskiego': '28',
            'warmińsko-mazurskie': '28', 'warmińsko mazurskie': '28',
            'warmińsko-mazurskiego': '28', 'warmińsko mazurskiego': '28',
            'warminsko mazurksiego': '28', 'warmińsko mazurksiego': '28',
            'warmia mazury': '28', 'warmia-mazury': '28',
            'warminskomazurskim': '28', 'wwarminskomazurskim': '28',
            'kujawsko-pomorskie': '04', 'kujawsko pomorskie': '04',
            'kujawskopomorskie': '04', 'kujawsko-pomorskiego': '04',
            'kujawsko pomorskiego': '04', 'kujawskopomorskiego': '04',
            'kujawy pomorze': '04', 'kujawy-pomorze': '04',
            'kujawskopomorskim': '04', 'wkujawskopomorskim': '04',
            'zachodniopomorskie': '32', 'zachodnio-pomorskie': '32',
            'zachodnio pomorskie': '32', 'zachodniopomorskiego': '32',
            'dolnoslaskie': '02', 'dolnośląskie': '02',
            'dolnoslaskiego': '02', 'dolnośląskiego': '02',
            'dolnyslaskim': '02', 'dolnymslasku': '02',
            'nadolnymslasku': '02', 'wdolnoslaskim': '02',
            'mazowieckie': '14', 'mazowieckiego': '14',
            'mazowieckim': '14', 'wmazowieckim': '14',
            'dolnymmazowieckim': '14', 'namazowszu': '14',
            'malopolskie': '12', 'małopolskie': '12',
            'malopolskiego': '12', 'małopolskiego': '12',
            'wmalopolskim': '12', 'wmalopolsce': '12',
            'wielkopolskie': '30', 'wielkopolskiego': '30',
            'wwielkopolskim': '30', 'wwielkopolsce': '30',
            'slaskie': '24', 'śląskie': '24',
            'slaskiego': '24', 'śląskiego': '24',
            'wslaskim': '24', 'naslasku': '24',
            'lubelskie': '06', 'lubelskiego': '06',
            'wlubelskim': '06', 'nalubelszczyznie': '06',
            'podlaskie': '20', 'podlaskiego': '20',
            'wpodlaskim': '20', 'napodlasiu': '20',
            'pomorskie': '22', 'pomorskiego': '22',
            'wpomorskim': '22', 'napomorzu': '22',
            'lodzkie': '10', 'łódzkie': '10',
            'opolskie': '16', 'podkarpackie': '18',
            'swietokrzyskie': '26', 'świętokrzyskie': '26',
            'lubuskie': '08',
        }

        self.CITY_TO_TERYT = {}

        # ALIASY REGIONÓW
        self.REGION_ALIASES = {
            "lubelszczyzna": "lubelskie", "lubelszczyzny": "lubelskie",
            "lubelszczyznie": "lubelskie", "lubelszczyzne": "lubelskie",
            "mazowsze": "mazowieckie", "mazowsza": "mazowieckie", "mazowszu": "mazowieckie",
            "podlasie": "podlaskie", "podlasia": "podlaskie", "podlasiu": "podlaskie",
            "slask": "slaskie", "slaska": "slaskie", "slasku": "slaskie",
            "śląsk": "slaskie", "śląska": "slaskie", "śląsku": "slaskie",
            "wielkopolska": "wielkopolskie", "wielkopolski": "wielkopolskie",
            "malopolska": "malopolskie", "małopolska": "malopolskie",
            "pomorze": "pomorskie", "pomorza": "pomorskie",
            "kaszuby": "pomorskie", "kujawy": "kujawsko-pomorskie",
            "warmia": "warminsko-mazurskie", "mazury": "warminsko-mazurskie",
            "podhale": "malopolskie", "podkarpacie": "podkarpackie",
            "opolszczyzna": "opolskie", "opolszczyzny": "opolskie",
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
            except Exception:
                self.map_hydro = {}

            try:
                self.station_coords = self._load_json(data_dir / "station_coords.json")
            except Exception:
                self.station_coords = {}

            self._build_city_to_teryt_map()

            # 🔥 POPRAWKA BUG 2: Normalizuj klucze VOIVODESHIP_VARIANTS
            self.VOIVODESHIP_VARIANTS_NORM = {
                self._normalize(k): v for k, v in self.VOIVODESHIP_VARIANTS.items()
            }

            print(
                f"✅ DataService: 🏙️ {len(self.simc_dict)} miast, "
                f"🗺️ {len(self.terc_dict)} powiatów, "
                f"🌊 {len(self.map_hydro)} stacji hydro"
            )

        except Exception as e:
            print(f"❌ BŁĄD: {e}")
            self.terc_dict = {}
            self.terc_reverse = {}
            self.simc_dict = {}
            self.map_simc_to_synop = {}
            self.map_hydro = {}
            self.station_coords = {}
            self.VOIVODESHIP_VARIANTS_NORM = {}

    def _build_city_to_teryt_map(self):
        for key, teryt in self.terc_dict.items():
            if key.startswith("m. "):
                city_name = self._normalize(key[3:])
                self.CITY_TO_TERYT[city_name] = teryt
            elif key.startswith("powiat "):
                county_name = self._normalize(key[7:])
                if county_name not in self.CITY_TO_TERYT:
                    self.CITY_TO_TERYT[county_name] = teryt

    def _load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
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

    def _degrees_to_direction(self, degrees) -> str | None:
        if degrees is None or degrees == "":
            return None
        try:
            deg = float(degrees)
        except (ValueError, TypeError):
            return None
        deg = deg % 360
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = int((deg + 22.5) / 45) % 8
        return directions[index]

    def _decode_ice_phenomenon(self, code) -> str | None:
        if code is None or code == "" or code == "null":
            return None
        code_str = str(code).strip()
        if code_str == "0":
            return None
        return self.ICE_PHENOMENA.get(code_str, f"zjawisko {code_str}")

    def _decode_overgrowth(self, code) -> str | None:
        if code is None or code == "" or code == "null" or code == "0":
            return None
        code_str = str(code).strip().zfill(3)
        if len(code_str) != 3:
            return None
        try:
            d, p, w = int(code_str[0]), int(code_str[1]), int(code_str[2])
        except ValueError:
            return None
        if d == 0 and p == 0 and w == 0:
            return None
        levels = {0: "brak", 1: "1/3", 2: "2/3", 3: "całkowite"}
        parts = []
        if d > 0:
            parts.append(f"denna: {levels[d]}")
        if p > 0:
            parts.append(f"pływająca: {levels[p]}")
        if w > 0:
            parts.append(f"wystająca: {levels[w]}")
        return ", ".join(parts) if parts else None

    def _generate_candidates(self, text: str) -> list[str]:
        norm_text = self._normalize(text)
        words = [
            w for w in norm_text.split() if w not in self.STOPWORDS and len(w) >= 2
        ]

        candidates: list[str] = []

        for phrase_len in [3, 2]:
            for i in range(len(words) - phrase_len + 1):
                phrase = " ".join(words[i:i + phrase_len])
                if phrase in self.REGION_ALIASES:
                    candidates.append(phrase)

        if len(words) > 1:
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i + 1]}"
                candidates.append(bigram)

        candidates.extend(words)

        for word in words:
            if word in self.REGION_ALIASES:
                candidates.insert(0, word)

        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    def get_nearest_station(self, city_name: str) -> dict | None:
        """Znajduje najbliższą stację TYLKO dla polskich lokalizacji."""
        if not self.station_coords:
            return None

        normalized = self._normalize(city_name)

        # 🔥 POPRAWKA BUG 3: Blacklista słów które nie powinny być geolokalizowane
        GEOCODE_BLACKLIST = {
            # Akweny (to powinno iść do hydro)
            "baltyk", "baltyku", "baltycki", "baltyckie",
            "morze", "morza", "morzem",
            # Ogólne słowa
            "polska", "polski", "polskie", "europe", "europa",
        }

        if normalized in GEOCODE_BLACKLIST:
            print(f"   ⚠️ '{city_name}' na blackliście geocodingu")
            return None

        if normalized in self.STOPWORDS or len(city_name) < 3:
            return None

        try:
            # Szukaj TYLKO w Polsce
            location = self.geolocator.geocode(f"{city_name}, Polska", country_codes=['pl'])

            if not location:
                print(f"   ⚠️ '{city_name}' nie znaleziono w Polsce")
                return None

            # Dodatkowa walidacja: Sprawdź czy to naprawdę Polska
            address = location.raw.get('display_name', '').lower()
            if 'polska' not in address and 'poland' not in address:
                print(f"   ⚠️ '{city_name}' nie jest w Polsce: {address}")
                return None

            user_coords = (location.latitude, location.longitude)

            # Sprawdź czy współrzędne są w granicach Polski
            # Polska: lat 49.0-54.9, lon 14.1-24.2
            if not (49.0 <= user_coords[0] <= 54.9 and 14.1 <= user_coords[1] <= 24.2):
                print(f"   ⚠️ '{city_name}' poza granicami Polski: {user_coords}")
                return None

            nearest_id, min_dist, nearest_name = None, float("inf"), ""
            for s_id, data in self.station_coords.items():
                s_coords = (data["lat"], data["lon"])
                dist = geodesic(user_coords, s_coords).km
                if dist < min_dist:
                    min_dist = dist
                    nearest_id = s_id
                    nearest_name = data["name"]

            # Jeśli najbliższa stacja jest dalej niż 150km, to pewnie błąd
            if min_dist > 150:
                print(f"   ⚠️ Najbliższa stacja zbyt daleko ({min_dist} km) - prawdopodobnie błędna lokalizacja")
                return None

            if nearest_id:
                return {
                    "type": "nearest",
                    "id": nearest_id,
                    "station_name": nearest_name,
                    "user_city": city_name,
                    "distance": round(min_dist, 1),
                }
        except Exception as e:
            print(f"⚠️ Błąd geolokalizacji: {e}")
            return None
        return None

    # ==================== VALIDATE AND GET ID ====================

    def validate_and_get_id(
            self, entities: dict, intent: str, original_text: str = ""
    ) -> dict | None:
        """Waliduje lokalizację i zwraca obiekt {id, name, type}."""
        nlp_candidates: list[str] = []
        if entities.get("placeName"):
            nlp_candidates.extend([self._normalize(p) for p in entities["placeName"]])
        if entities.get("geogName"):
            nlp_candidates.extend([self._normalize(g) for g in entities["geogName"]])

        text_candidates = self._generate_candidates(original_text)
        all_candidates = nlp_candidates + text_candidates
        all_candidates = list(dict.fromkeys(all_candidates))

        print(f"   🔍 Kandydaci (przed aliasami): {all_candidates}")

        # Rozdziel słowa pisane razem
        expanded_candidates = []
        for c in all_candidates:
            expanded_candidates.append(c)
            if len(c) > 12 and ' ' not in c:
                separated = self._try_separate_words(c)
                if separated:
                    expanded_candidates.append(separated)
        all_candidates = list(dict.fromkeys(expanded_candidates))

        # Zamień aliasy regionów
        resolved_candidates: list[str] = []
        for c in all_candidates:
            norm_c = self._normalize(c)
            if norm_c in self.REGION_ALIASES:
                alias_target = self._normalize(self.REGION_ALIASES[norm_c])
                resolved_candidates.insert(0, alias_target)
                print(f"   🗺️ Alias: '{c}' → '{alias_target}'")
            resolved_candidates.append(norm_c)

        all_candidates = list(dict.fromkeys(resolved_candidates))
        print(f"   🔍 Kandydaci (po aliasach): {all_candidates}")

        # ==================== HYDRO ====================
        if intent == "hydro":
            for candidate in all_candidates:
                if len(candidate) < 2:
                    continue
                normalized = self._normalize_river(candidate)

                if normalized in self.MAIN_RIVERS:
                    return {
                        "type": "hydro_river",
                        "id": self.MAIN_RIVERS[normalized],
                        "name": normalized.title(),
                        "river_name": normalized,
                    }

                if normalized in self.map_hydro:
                    return {
                        "type": "hydro",
                        "id": self.map_hydro[normalized],
                        "name": normalized.title(),
                    }

                for key in self.map_hydro.keys():
                    if key.startswith(normalized + " ") or normalized in key.split():
                        return {
                            "type": "hydro",
                            "id": self.map_hydro[key],
                            "name": key.title(),
                        }
            return None

        # ==================== POGODA ====================
        elif intent == "pogoda":
            # Najpierw sprawdź województwa
            for candidate in all_candidates:
                if candidate in self.VOIVODESHIPS:
                    capital = self.VOIVODESHIP_CAPITALS.get(candidate)
                    if capital and capital in self.simc_dict:
                        simc_id = self.simc_dict[capital]
                        if simc_id in self.map_simc_to_synop:
                            return {
                                "type": "voivodeship_capital",
                                "id": self.map_simc_to_synop[simc_id],
                                "name": capital.title(),
                                "voivodeship": candidate.title(),
                            }

            # Sprawdź zagraniczne miasta
            for candidate in all_candidates:
                if candidate in self.FOREIGN_CITIES:
                    print(f"   🌍 Wykryto zagraniczne miasto: {candidate}")
                    return {"type": "foreign", "name": candidate.title()}

            # Wyszukiwanie miast
            all_cities = list(self.simc_dict.keys())
            for candidate in all_candidates:
                if len(candidate) < 3:
                    continue
                if candidate in self.VOIVODESHIPS:
                    continue

                if candidate in all_cities:
                    simc_id = self.simc_dict[candidate]
                    if simc_id in self.map_simc_to_synop:
                        return {
                            "type": "direct",
                            "id": self.map_simc_to_synop[simc_id],
                            "name": candidate.title(),
                        }

                match = self._safe_fuzzy_match(candidate, all_cities)
                if match:
                    simc_id = self.simc_dict[match]
                    if simc_id in self.map_simc_to_synop:
                        return {
                            "type": "direct",
                            "id": self.map_simc_to_synop[simc_id],
                            "name": match.title(),
                        }

            # Geolokalizacja jako fallback
            if all_candidates:
                valid = [
                    c for c in all_candidates
                    if c not in self.STOPWORDS
                       and len(c) >= 4
                       and c not in self.VOIVODESHIPS
                       and c not in self.REGION_ALIASES
                ]
                if valid:
                    potential = max(valid, key=len)
                    return self.get_nearest_station(potential)
            return None

        # ==================== OSTRZEŻENIA ====================
        elif intent == "ostrzeżenia":
            # 🔥 POPRAWKA BUG 2: Sprawdź warianty województw używając znormalizowanego słownika
            for candidate in all_candidates:
                if candidate in self.VOIVODESHIP_VARIANTS_NORM:
                    voiv_code = self.VOIVODESHIP_VARIANTS_NORM[candidate]
                    for name, code in self.VOIVODESHIPS.items():
                        if code == voiv_code:
                            return {
                                "type": "voivodeship",
                                "id": voiv_code,
                                "name": name.title(),
                            }

                if candidate in self.VOIVODESHIPS:
                    return {
                        "type": "voivodeship",
                        "id": self.VOIVODESHIPS[candidate],
                        "name": candidate.title(),
                    }

            # Powiaty
            all_powiats = list(self.terc_dict.keys())
            for candidate in all_candidates:
                if candidate in self.VOIVODESHIPS:
                    continue

                keys_to_try = [candidate, f"powiat {candidate}", f"m. {candidate}"]

                for key in keys_to_try:
                    if key in all_powiats:
                        return {
                            "type": "teryt",
                            "id": self.terc_dict[key],
                            "name": key.title(),
                        }

                    match = self._safe_fuzzy_match(key, all_powiats)
                    if match:
                        return {
                            "type": "teryt",
                            "id": self.terc_dict[match],
                            "name": match.title(),
                        }

            return None

        return None

    def _safe_fuzzy_match(self, candidate: str, options: list[str]) -> str | None:
        """Bezpieczne fuzzy matching z ostrzejszymi kryteriami."""
        if len(candidate) < 3:
            return None

        matches = difflib.get_close_matches(candidate, options, n=1, cutoff=0.88)

        if not matches:
            return None

        best_match = matches[0]

        len_diff = abs(len(candidate) - len(best_match))
        if len_diff > 2:
            print(f"   ⚠️ Odrzucono fuzzy match: '{candidate}' → '{best_match}' (różnica długości: {len_diff})")
            return None

        if candidate[0] != best_match[0]:
            print(f"   ⚠️ Odrzucono fuzzy match: '{candidate}' → '{best_match}' (różne pierwsze litery)")
            return None

        if len(candidate) < 5 and len_diff > 1:
            print(f"   ⚠️ Odrzucono fuzzy match: '{candidate}' → '{best_match}' (zbyt krótkie słowo)")
            return None

        print(f"   ✅ Fuzzy match: '{candidate}' → '{best_match}'")
        return best_match

    def _try_separate_words(self, text: str) -> str | None:
        """Próbuje rozdzielić słowa pisane razem."""
        text_lower = text.lower()

        separations = {
            'dolnymmazowieckim': 'mazowieckie',
            'gorymazowieckim': 'mazowieckie',
            'namazowszu': 'mazowieckie',
            'wmazowieckim': 'mazowieckie',
            'dolnyslaskim': 'dolnoslaskie',
            'wdolnoslaskim': 'dolnoslaskie',
            'nadolnymslasku': 'dolnoslaskie',
            'malopolskim': 'malopolskie',
            'wmalopolskim': 'malopolskie',
            'wmalopolsce': 'malopolskie',
            'wielkopolskim': 'wielkopolskie',
            'wwielkopolskim': 'wielkopolskie',
            'wwielkopolsce': 'wielkopolskie',
            'slaskim': 'slaskie',
            'wslaskim': 'slaskie',
            'naslask': 'slaskie',
            'naslasku': 'slaskie',
            'warminskomazurskim': 'warminsko-mazurskie',
            'wwarminskomazurskim': 'warminsko-mazurskie',
            'kujawskopomorskim': 'kujawsko-pomorskie',
            'wkujawskopomorskim': 'kujawsko-pomorskie',
            'lubelskim': 'lubelskie',
            'wlubelskim': 'lubelskie',
            'nalubelszczyznie': 'lubelskie',
            'podlaskim': 'podlaskie',
            'wpodlaskim': 'podlaskie',
            'napodlasiu': 'podlaskie',
            'pomorskim': 'pomorskie',
            'wpomorskim': 'pomorskie',
            'napomorzu': 'pomorskie',
        }

        for pattern, result in separations.items():
            if pattern in text_lower:
                return result

        return None

    # ==================== FETCH DATA ====================

    async def fetch_data(self, intent: str, location_data: dict) -> str:
        try:
            # 🔥 POPRAWKA BUG 1: Sprawdź typ PRZED pobraniem id!
            loc_type = location_data.get("type", "")
            loc_name = location_data.get("name", "Nieznane")

            # Obsługa zagranicznych miast
            if loc_type == "foreign":
                return (
                    f"🌍 {loc_name} znajduje się poza Polską.\n\n"
                    "📡 Obsługuję tylko lokalizacje w Polsce.\n"
                    "Dane pochodzą z IMGW (Instytut Meteorologii i Gospodarki Wodnej).\n\n"
                    "Podaj polskie miasto, np.:\n"
                    "• Warszawa, Kraków, Gdańsk\n"
                    "• Wrocław, Poznań, Łódź"
                )

            # Teraz bezpiecznie pobierz id
            loc_id = location_data.get("id")
            if not loc_id:
                return "❌ Brak danych dla tej lokalizacji."

            # POGODA
            if intent == "pogoda":
                prefix = ""
                city_for_warnings = loc_name

                if loc_type == "voivodeship_capital":
                    voivodeship = location_data.get("voivodeship", "")
                    prefix = f"🗺️ Pogoda dla woj. {voivodeship} (stolica: {loc_name}):\n\n"
                elif loc_type == "nearest":
                    user_city = location_data.get("user_city", "?").title()
                    station_name = location_data.get("station_name", "?")
                    distance = location_data.get("distance", "?")
                    prefix = f"📍 Najbliższa stacja: {station_name} ({distance} km od {user_city})\n\n"
                    city_for_warnings = user_city

                data = await self.imgw_client.get_synop_data(loc_id)
                if isinstance(data, list):
                    data = data[0] if data else {}

                station = data.get("stacja", loc_name)
                temp = data.get("temperatura", "?")
                wind_speed = data.get("predkosc_wiatru", "?")
                wind_dir_deg = data.get("kierunek_wiatru", None)
                rain = data.get("suma_opadu", "?")
                pressure = data.get("cisnienie", None)
                humidity = data.get("wilgotnosc_wzgledna", None)
                date = data.get("data_pomiaru", "")
                hour = data.get("godzina_pomiaru", "")

                wind_direction = self._degrees_to_direction(wind_dir_deg)

                response = f"{prefix}📍 {station}\n"
                response += f"🌡️ Temperatura: {temp}°C\n"
                response += f"💨 Wiatr: {wind_speed} m/s"
                if wind_direction:
                    response += f" ({wind_direction})"
                response += f"\n☔ Opady: {rain} mm"

                if pressure and pressure != "null":
                    response += f"\n🔽 Ciśnienie: {pressure} hPa"
                if humidity and humidity != "null":
                    response += f"\n💧 Wilgotność: {humidity}%"

                if date and hour:
                    response += f"\n\n🕐 Pomiar: {date}, godz. {hour}:00"
                    response += "\n📡 (dane aktualne, nie prognoza)"

                try:
                    warnings, warning_location = await self.get_warnings_for_city(city_for_warnings)
                    if warnings:
                        warning_text = self._format_weather_warnings(warnings, warning_location or city_for_warnings)
                        response += warning_text
                except Exception as e:
                    print(f"⚠️ Nie udało się sprawdzić ostrzeżeń: {e}")

                return response

            # HYDRO
            elif intent == "hydro":
                if loc_type == "hydro_river":
                    river_name = location_data.get("river_name", loc_name)
                    return await self._fetch_river_data(river_name, loc_id)
                return await self._fetch_single_hydro_station(loc_id, loc_name)

            # OSTRZEŻENIA
            elif intent == "ostrzeżenia":
                response, _ = await self.fetch_warnings_with_data(location_data)
                return response

        except Exception as e:
            print(f"❌ Błąd: {e}")
            return f"❌ Błąd pobierania danych: {e}"

        return "❓ Nieznana intencja."

    # Pozostałe metody bez zmian...
    async def get_warnings_for_city(self, city_name: str) -> tuple[list[dict], str]:
        """Sprawdza czy są aktywne ostrzeżenia dla danego miasta."""
        try:
            normalized_city = self._normalize(city_name)

            teryt_code = None
            location_name = city_name

            if normalized_city in self.CITY_TO_TERYT:
                teryt_code = self.CITY_TO_TERYT[normalized_city]
                location_name = normalized_city.title()
            else:
                all_cities = list(self.CITY_TO_TERYT.keys())
                matches = difflib.get_close_matches(normalized_city, all_cities, n=1, cutoff=0.8)
                if matches:
                    matched_city = matches[0]
                    teryt_code = self.CITY_TO_TERYT[matched_city]
                    location_name = matched_city.title()

            if not teryt_code:
                voivodeship_prefix = self._get_voivodeship_for_city(normalized_city)
                if voivodeship_prefix:
                    return await self._get_warnings_by_voivodeship_prefix(voivodeship_prefix)
                return [], ""

            warnings = await self.imgw_client.get_meteo_warnings()

            if not isinstance(warnings, list):
                return [], ""

            found_warnings = []
            for w in warnings:
                teryt_codes = w.get("teryt", [])
                if isinstance(teryt_codes, str):
                    teryt_codes = [teryt_codes]

                if teryt_code in teryt_codes:
                    found_warnings.append(w)
                    continue

                voiv_prefix = teryt_code[:2] if teryt_code else None
                if voiv_prefix:
                    for code in teryt_codes:
                        if code.startswith(voiv_prefix) and code == teryt_code:
                            found_warnings.append(w)
                            break

            return found_warnings, location_name

        except Exception as e:
            print(f"⚠️ Błąd pobierania ostrzeżeń dla miasta: {e}")
            return [], ""

    def _get_voivodeship_for_city(self, city_name: str) -> Optional[str]:
        for voiv, capital in self.VOIVODESHIP_CAPITALS.items():
            if self._normalize(capital) == city_name:
                return self.VOIVODESHIPS.get(voiv)

        if city_name in self.CITY_TO_TERYT:
            teryt = self.CITY_TO_TERYT[city_name]
            return teryt[:2] if teryt else None

        return None

    async def _get_warnings_by_voivodeship_prefix(self, prefix: str) -> tuple[list[dict], str]:
        try:
            warnings = await self.imgw_client.get_meteo_warnings()

            if not isinstance(warnings, list):
                return [], ""

            found_warnings = []
            for w in warnings:
                teryt_codes = w.get("teryt", [])
                if isinstance(teryt_codes, str):
                    teryt_codes = [teryt_codes]

                for code in teryt_codes:
                    if code.startswith(prefix):
                        found_warnings.append(w)
                        break

            voiv_name = ""
            for name, code in self.VOIVODESHIPS.items():
                if code == prefix:
                    voiv_name = name.title()
                    break

            return found_warnings, voiv_name

        except Exception as e:
            print(f"⚠️ Błąd: {e}")
            return [], ""

    def _format_weather_warnings(self, warnings: list[dict], location_name: str) -> str:
        if not warnings:
            return ""

        unique_warnings = []
        seen_keys = set()

        for w in warnings:
            nazwa = w.get("nazwa_zdarzenia", "Alert")
            stopien = w.get("stopien", "?")
            key = f"{nazwa}_{stopien}"

            if key not in seen_keys:
                seen_keys.add(key)
                unique_warnings.append({
                    "nazwa": nazwa,
                    "stopien": stopien,
                    "do": w.get("obowiazuje_do", ""),
                })

        if not unique_warnings:
            return ""

        alert_text = "\n\n" + "─" * 35 + "\n"
        alert_text += "⚠️ UWAGA! Aktywne ostrzeżenia:\n"

        for w in unique_warnings[:3]:
            alert_text += f"   🔸 {w['nazwa']} (stopień {w['stopien']})"
            if w['do']:
                do_short = w['do'][:16] if len(w['do']) > 16 else w['do']
                alert_text += f" do {do_short}"
            alert_text += "\n"

        if len(unique_warnings) > 3:
            alert_text += f"   ... i {len(unique_warnings) - 3} więcej\n"

        alert_text += f"\n💡 Wpisz \"ostrzeżenia {location_name}\" aby zobaczyć szczegóły."

        return alert_text

    def _select_best_stations(self, stations: list, max_count: int = 3) -> list:
        if len(stations) <= max_count:
            return stations

        scored = []
        for s in stations:
            score = 0
            ice = s.get("zjawisko_lodowe")
            if ice and ice != "0" and ice != "" and ice != "null":
                score += 100
            if s.get("przelyw") and s.get("przelyw") != "null":
                score += 10
            if s.get("temperatura_wody") and s.get("temperatura_wody") != "null":
                score += 5
            try:
                flow = float(s.get("przelew", 0) or 0)
                score += min(flow / 10, 50)
            except Exception:
                pass
            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_count]]

    async def fetch_warnings_with_data(self, location_data: dict) -> tuple[str, list]:
        try:
            loc_id = location_data["id"]
            loc_name = location_data.get("name", "Nieznane")
            loc_type = location_data.get("type", "")

            warnings = await self.imgw_client.get_meteo_warnings()

            if isinstance(warnings, dict):
                return "⚠️ Błąd API ostrzeżeń.", []
            if not isinstance(warnings, list):
                return "⚠️ Nieoczekiwany format danych.", []

            found_warnings: list[dict] = []
            found_texts: list[str] = []

            if loc_type == "voivodeship":
                voivodeship_prefix = loc_id

                for w in warnings:
                    teryt_codes = w.get("teryt", [])
                    if isinstance(teryt_codes, str):
                        teryt_codes = [teryt_codes]

                    matching_codes = [
                        code for code in teryt_codes
                        if code.startswith(voivodeship_prefix)
                    ]

                    if matching_codes:
                        warning_copy = w.copy()
                        warning_copy["teryt"] = matching_codes
                        found_warnings.append(warning_copy)

                        nazwa = w.get("nazwa_zdarzenia", "Alert")
                        stopien = w.get("stopien", "?")
                        od = w.get("obowiazuje_od", "")
                        do = w.get("obowiazuje_do", "")
                        tresc = w.get("tresc", "")
                        prawdop = w.get("prawdopodobienstwo", "")

                        powiat_names: list[str] = []
                        for code in matching_codes:
                            if code in self.terc_reverse:
                                powiat_names.append(self.terc_reverse[code])

                        alert = f"⚠️ {nazwa} (stopień {stopien})"

                        if powiat_names:
                            display_count = 5
                            alert += f"\n📍 Powiaty: {', '.join(powiat_names[:display_count])}"
                            if len(powiat_names) > display_count:
                                remaining = len(powiat_names) - display_count
                                alert += f" (+{remaining} więcej)"
                                alert += "\n💡 Wpisz \"podaj powiaty\" aby zobaczyć pełną listę"

                        if prawdop:
                            alert += f"\n📊 Prawdopodobieństwo: {prawdop}%"
                        if od:
                            alert += f"\n🕐 Od: {od}"
                        if do:
                            alert += f"\n🕐 Do: {do}"
                        if tresc:
                            if len(tresc) > 450:
                                cut_pos = tresc.rfind('.', 380, 450)
                                if cut_pos == -1:
                                    cut_pos = 450
                                tresc = tresc[:cut_pos].rstrip('.') + "..."
                            alert += f"\n📝 {tresc}"

                        alert_key = f"{nazwa}_{stopien}"
                        if not any(alert_key in a for a in found_texts):
                            found_texts.append(alert)

            else:
                for w in warnings:
                    teryt_codes = w.get("teryt", [])
                    if isinstance(teryt_codes, str):
                        teryt_codes = [teryt_codes]

                    if loc_id in teryt_codes:
                        found_warnings.append(w)

                        nazwa = w.get("nazwa_zdarzenia", "Alert")
                        stopien = w.get("stopien", "?")
                        od = w.get("obowiazuje_od", "")
                        do = w.get("obowiazuje_do", "")
                        tresc = w.get("tresc", "")
                        prawdop = w.get("prawdopodobienstwo", "")

                        alert = f"⚠️ {nazwa} (stopień {stopien})"
                        if prawdop:
                            alert += f"\n📊 Prawdopodobieństwo: {prawdop}%"
                        if od:
                            alert += f"\n🕐 Od: {od}"
                        if do:
                            alert += f"\n🕐 Do: {do}"
                        if tresc:
                            if len(tresc) > 450:
                                cut_pos = tresc.rfind('.', 380, 450)
                                if cut_pos == -1:
                                    cut_pos = 450
                                tresc = tresc[:cut_pos].rstrip('.') + "..."
                            alert += f"\n📝 {tresc}"
                        found_texts.append(alert)

            if found_texts:
                if loc_type == "voivodeship":
                    header = f"⚠️ Ostrzeżenia dla województwa {loc_name}:\n\n"
                else:
                    header = f"⚠️ Ostrzeżenia dla {loc_name}:\n\n"
                return header + "\n\n".join(found_texts), found_warnings

            return f"✅ Brak aktywnych ostrzeżeń dla {loc_name}.", []

        except Exception as e:
            print(f"❌ Błąd: {e}")
            return f"❌ Błąd pobierania danych: {e}", []

    async def get_station_list(self, water_body: str) -> str:
        try:
            normalized = self._normalize_river(water_body)
            stations = await self.imgw_client.get_hydro_by_river(normalized)

            if not stations:
                stations = await self.imgw_client.get_hydro_by_river(water_body)

            if not stations:
                return f"❌ Nie znalazłem stacji dla akwenu \"{water_body}\"."

            water_body_name = stations[0].get("rzeka", water_body.title())
            total = len(stations)

            response = f"📋 Lista stacji: {water_body_name} ({total} stacji)\n"
            response += "=" * 40 + "\n\n"

            by_voivodeship: dict[str, list] = {}
            for s in stations:
                voiv = s.get("wojewodztwo", "nieznane") or "nieznane"
                if voiv not in by_voivodeship:
                    by_voivodeship[voiv] = []
                by_voivodeship[voiv].append(s.get("stacja", "?"))

            for voiv in sorted(by_voivodeship.keys()):
                station_names = sorted(by_voivodeship[voiv])
                response += f"📍 {voiv.title()}:\n"
                for name in station_names:
                    response += f"   • {name}\n"
                response += "\n"

            response += "💡 Wpisz np. \"Wisła stacja Toruń\" aby zobaczyć szczegóły."

            return response

        except Exception as e:
            print(f"❌ Błąd pobierania listy stacji: {e}")
            return f"❌ Błąd pobierania listy stacji: {e}"

    async def _fetch_river_data(self, river_name: str, fallback_id: str) -> str:
        try:
            stations = await self.imgw_client.get_hydro_by_river(river_name)
            if not stations:
                return await self._fetch_single_hydro_station(fallback_id, river_name)

            river_display = stations[0].get("rzeka", river_name.title())
            total_count = len(stations)

            best_stations = self._select_best_stations(stations, max_count=3)

            response = f"🌊 {river_display} - {total_count} stacji pomiarowych\n"
            response += "-" * 35 + "\n\n"

            for i, station in enumerate(best_stations):
                response += self._format_hydro_station(station, compact=(i > 0))
                if i < len(best_stations) - 1:
                    response += "\n"

            if total_count > 3:
                response += f"\n\n📌 Pozostałe stacje: {total_count - 3}"
                response += "\n💡 Podaj nazwę stacji dla szczegółów lub wpisz \"lista stacji\"."

            return response

        except Exception as e:
            print(f"❌ Błąd pobierania rzeki: {e}")
            return await self._fetch_single_hydro_station(fallback_id, river_name)

    async def _fetch_single_hydro_station(self, station_id: str, name: str) -> str:
        data = await self.imgw_client.get_hydro_data(station_id)
        if isinstance(data, list):
            data = data[0] if data else {}
        return self._format_hydro_station(data, compact=False)

    def _format_hydro_station(self, data: dict, compact: bool = False) -> str:
        river = data.get("rzeka", "?")
        station = data.get("stacja", "?")
        voivodeship = data.get("wojewodztwo", "")
        water_level = data.get("stan_wody", "?")
        water_temp = data.get("temperatura_wody", None)
        flow = data.get("przelyw", None)
        date = data.get("stan_wody_data_pomiaru", "")
        ice_code = data.get("zjawisko_lodowe", None)
        overgrowth_code = data.get("zjawisko_zarastania", None)

        if compact:
            loc_info = f"📍 {station}"
            if voivodeship:
                loc_info += f" ({voivodeship})"
            response = f"{loc_info}\n"
            response += f"   💧 Stan: {water_level} cm"
            if flow and flow != "null":
                response += f", 🌊 przepływ: {flow} m³/s"
            if water_temp and water_temp != "null":
                response += f", 🌡️ temp: {water_temp}°C"
            ice_desc = self._decode_ice_phenomenon(ice_code)
            if ice_desc:
                response += f"\n   🧊 Lód: {ice_desc}"
            return response

        response = f"🌊 {river}\n"
        response += f"📍 Stacja: {station}"
        if voivodeship:
            response += f" ({voivodeship})"
        response += "\n\n"
        response += f"💧 Stan wody: {water_level} cm\n"
        if flow and flow != "null":
            response += f"🌊 Przepływ: {flow} m³/s\n"
        if water_temp and water_temp != "null":
            response += f"🌡️ Temp. wody: {water_temp}°C\n"
        ice_desc = self._decode_ice_phenomenon(ice_code)
        if ice_desc:
            response += f"🧊 Zjawisko lodowe: {ice_desc}\n"
        overgrowth_desc = self._decode_overgrowth(overgrowth_code)
        if overgrowth_desc:
            response += f"🌿 Zarastanie: {overgrowth_desc}\n"

        if date:
            response += f"\n🕐 Pomiar: {date}"

        return response

    def _extract_city_from_long_text(self, text: str) -> str | None:
        """Wyciąga nazwę miasta z długiego zdania."""
        # Lista znanych miast
        known_cities = list(self.simc_dict.keys())
        text_lower = self._normalize(text)

        for city in known_cities:
            if city in text_lower:
                return city
        return None