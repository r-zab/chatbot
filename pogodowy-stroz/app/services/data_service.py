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

        # KODY ZJAWISK LODOWYCH (z dokumentacji IMGW)
        self.ICE_PHENOMENA = {
            '0': 'brak zjawisk',
            '01': 'śryż',
            '1': 'śryż',
            '02': 'kra',
            '2': 'kra',
            '03': 'lód brzegowy',
            '3': 'lód brzegowy',
            '04': 'pokrywa lodowa',
            '4': 'pokrywa lodowa',
            '05': 'zator lodowy',
            '5': 'zator lodowy',
            '06': 'lód brzegowy i śryż',
            '6': 'lód brzegowy i śryż',
            '07': 'lód brzegowy i kra',
            '7': 'lód brzegowy i kra',
            '08': 'śryż i kra',
            '8': 'śryż i kra',
            '09': 'zator śryżowy',
            '9': 'zator śryżowy',
            '32': 'lód zatokowy',
            '41': 'woda na lodzie',
            '42': 'lód pływający (wolny od brzegów)',
            '43': 'lód zmurszały (dziurawy)',
        }

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
            'elblagu': 'elblag', 'elbląg': 'elblag', 'elblągu': 'elblag',
            'regalicy': 'regalica', 'regalicą': 'regalica',
            'wieprzy': 'wieprza', 'wieprzą': 'wieprza',
        }

        # GŁÓWNE RZEKI -> ID stacji (reprezentatywna stacja)
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
            'elblag': '154190060',
            'regalica': '153140190',
            'wieprza': '154160150',
        }

        # WOJEWÓDZTWA - prefiksy kodów TERYT
        self.VOIVODESHIPS = {
            'dolnoslaskie': '02',
            'dolnoslaska': '02',
            'kujawsko-pomorskie': '04',
            'kujawsko-pomorska': '04',
            'lubelskie': '06',
            'lubelska': '06',
            'lubuskie': '08',
            'lubuska': '08',
            'lodzkie': '10',
            'lodzka': '10',
            'malopolskie': '12',
            'malopolska': '12',
            'mazowieckie': '14',
            'mazowiecka': '14',
            'opolskie': '16',
            'opolska': '16',
            'podkarpackie': '18',
            'podkarpacka': '18',
            'podlaskie': '20',
            'podlaska': '20',
            'pomorskie': '22',
            'pomorska': '22',
            'slaskie': '24',
            'slaska': '24',
            'swietokrzyskie': '26',
            'swietokrzyska': '26',
            'warminsko-mazurskie': '28',
            'warminsko-mazurska': '28',
            'wielkopolskie': '30',
            'wielkopolska': '30',
            'zachodniopomorskie': '32',
            'zachodniopomorska': '32',
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

            print(
                f"✅ DataService: 🏙️ {len(self.simc_dict)} miast, 🗺️ {len(self.terc_dict)} powiatów, 🌊 {len(self.map_hydro)} stacji hydro")

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
            "N", "NE", "E", "SE",
            "S", "SW", "W", "NW"
        ]

        index = int((deg + 22.5) / 45) % 8
        return directions[index]

    def _decode_ice_phenomenon(self, code) -> str:
        """Dekoduje kod zjawiska lodowego."""
        if code is None or code == '' or code == 'null':
            return None

        code_str = str(code).strip()

        if code_str == '0':
            return None

        return self.ICE_PHENOMENA.get(code_str, f"zjawisko {code_str}")

    def _decode_overgrowth(self, code) -> str:
        """Dekoduje kod zarastania."""
        if code is None or code == '' or code == 'null' or code == '0':
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

        levels = {0: 'brak', 1: '1/3', 2: '2/3', 3: 'całkowite'}
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

        print(f"   🔍 Kandydaci: {all_candidates}")

        # ==================== HYDRO ====================
        if intent == 'hydro':
            for candidate in all_candidates:
                if len(candidate) < 2:
                    continue

                normalized = self._normalize_river(candidate)
                print(f"   🌊 Sprawdzam rzekę: '{candidate}' -> '{normalized}'")

                if normalized in self.MAIN_RIVERS:
                    print(f"   ✅ Znaleziono główną rzekę: {normalized}")
                    return {
                        "type": "hydro_river",
                        "id": self.MAIN_RIVERS[normalized],
                        "name": normalized.title(),
                        "river_name": normalized
                    }

                if normalized in self.map_hydro:
                    return {
                        "type": "hydro",
                        "id": self.map_hydro[normalized],
                        "name": normalized.title()
                    }

                for key in self.map_hydro.keys():
                    if key.startswith(normalized + " ") or normalized in key.split():
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

            if all_candidates:
                valid = [c for c in all_candidates if c not in self.STOPWORDS and len(c) >= 4]
                if valid:
                    potential = max(valid, key=len)
                    return self.get_nearest_station(potential)

            return None

        # ==================== OSTRZEŻENIA ====================
        elif intent == 'ostrzeżenia':
            # Najpierw sprawdź województwa
            for candidate in all_candidates:
                if candidate in self.VOIVODESHIPS:
                    return {
                        "type": "voivodeship",
                        "id": self.VOIVODESHIPS[candidate],
                        "name": candidate.title()
                    }

            # Potem powiaty
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

    def _select_best_stations(self, stations: list, max_count: int = 3) -> list:
        """
        Wybiera najważniejsze stacje do wyświetlenia.
        Priorytet: stacje z zjawiskami lodowymi, wysokim przepływem, lub z pełnymi danymi.
        """
        if len(stations) <= max_count:
            return stations

        scored = []
        for s in stations:
            score = 0

            # Zjawisko lodowe - wysoki priorytet
            ice = s.get('zjawisko_lodowe')
            if ice and ice != '0' and ice != '' and ice != 'null':
                score += 100

            # Kompletność danych
            if s.get('przelyw') and s.get('przelyw') != 'null':
                score += 10
            if s.get('temperatura_wody') and s.get('temperatura_wody') != 'null':
                score += 5

            # Wyższy przepływ = ważniejsza stacja
            try:
                flow = float(s.get('przelyw', 0) or 0)
                score += min(flow / 10, 50)  # max 50 punktów za przepływ
            except:
                pass

            scored.append((score, s))

        # Sortuj malejąco po score
        scored.sort(key=lambda x: x[0], reverse=True)

        return [s for _, s in scored[:max_count]]

    async def fetch_data(self, intent: str, location_data: dict) -> str:
        """Pobiera dane z API IMGW i formatuje odpowiedź."""
        try:
            loc_id = location_data['id']
            loc_name = location_data.get('name', 'Nieznane')
            loc_type = location_data.get('type', '')

            # ==================== POGODA ====================
            if intent == 'pogoda':
                prefix = ""
                if loc_type == 'nearest':
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

                response = f"{prefix}📍 {station}\n"
                response += f"🌡️ Temperatura: {temp}°C\n"
                response += f"💨 Wiatr: {wind_speed} m/s"

                if wind_direction:
                    response += f" ({wind_direction})"

                response += f"\n☔ Opady: {rain} mm"

                if pressure and pressure != 'null' and pressure is not None:
                    response += f"\n🔽 Ciśnienie: {pressure} hPa"
                if humidity and humidity != 'null' and humidity is not None:
                    response += f"\n💧 Wilgotność: {humidity}%"

                if date and hour:
                    response += f"\n\n🕐 Pomiar: {date}, godz. {hour}:00"

                return response

            # ==================== HYDRO ====================
            elif intent == 'hydro':
                if loc_type == 'hydro_river':
                    river_name = location_data.get('river_name', loc_name)
                    return await self._fetch_river_data(river_name, loc_id)

                return await self._fetch_single_hydro_station(loc_id, loc_name)

            # ==================== OSTRZEŻENIA ====================
            elif intent == 'ostrzeżenia':
                warnings = await self.imgw_client.get_meteo_warnings()

                if isinstance(warnings, dict):
                    return "⚠️ Błąd API ostrzeżeń."

                if not isinstance(warnings, list):
                    return "⚠️ Nieoczekiwany format danych."

                found = []

                # Obsługa województwa - znajdź wszystkie ostrzeżenia dla powiatów w tym województwie
                if loc_type == 'voivodeship':
                    voivodeship_prefix = loc_id

                    for w in warnings:
                        teryt_codes = w.get('teryt', [])
                        if isinstance(teryt_codes, str):
                            teryt_codes = [teryt_codes]

                        # Sprawdź czy jakikolwiek kod TERYT należy do tego województwa
                        matching_codes = [code for code in teryt_codes if code.startswith(voivodeship_prefix)]

                        if matching_codes:
                            nazwa = w.get('nazwa_zdarzenia', 'Alert')
                            stopien = w.get('stopien', '?')
                            od = w.get('obowiazuje_od', '')
                            do = w.get('obowiazuje_do', '')
                            tresc = w.get('tresc', '')
                            prawdop = w.get('prawdopodobienstwo', '')

                            # Znajdź nazwy powiatów dla tego ostrzeżenia
                            powiat_names = []
                            for code in matching_codes:
                                if code in self.terc_reverse:
                                    powiat_names.append(self.terc_reverse[code])

                            alert = f"⚠️ {nazwa} (stopień {stopien})"

                            if powiat_names:
                                alert += f"\n📍 Powiaty: {', '.join(powiat_names[:5])}"
                                if len(powiat_names) > 5:
                                    alert += f" (+{len(powiat_names) - 5} więcej)"

                            if prawdop:
                                alert += f"\n📊 Prawdopodobieństwo: {prawdop}%"
                            if od:
                                alert += f"\n🕐 Od: {od}"
                            if do:
                                alert += f"\n🕐 Do: {do}"
                            if tresc:
                                if len(tresc) > 200:
                                    tresc = tresc[:200] + "..."
                                alert += f"\n📝 {tresc}"

                            # Unikaj duplikatów tego samego typu ostrzeżenia
                            alert_key = f"{nazwa}_{stopien}"
                            if not any(alert_key in str(a) for a in found):
                                found.append(alert)

                # Obsługa pojedynczego powiatu
                else:
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
                                alert += f"\n📊 Prawdopodobieństwo: {prawdop}%"
                            if od:
                                alert += f"\n🕐 Od: {od}"
                            if do:
                                alert += f"\n🕐 Do: {do}"
                            if tresc:
                                if len(tresc) > 200:
                                    tresc = tresc[:200] + "..."
                                alert += f"\n📝 {tresc}"

                            found.append(alert)

                if found:
                    if loc_type == 'voivodeship':
                        header = f"⚠️ Ostrzeżenia dla województwa {loc_name}:\n\n"
                    else:
                        header = f"⚠️ Ostrzeżenia dla {loc_name}:\n\n"
                    return header + "\n\n".join(found)

                return f"✅ Brak aktywnych ostrzeżeń dla {loc_name}."

        except Exception as e:
            print(f"❌ Błąd: {e}")
            return f"❌ Błąd pobierania danych: {e}"

        return "❓ Nieznana intencja."

    async def _fetch_river_data(self, river_name: str, fallback_id: str) -> str:
        """Pobiera dane dla całej rzeki (wybrane stacje)."""
        try:
            stations = await self.imgw_client.get_hydro_by_river(river_name)

            if not stations:
                return await self._fetch_single_hydro_station(fallback_id, river_name)

            river_display = stations[0].get('rzeka', river_name.title())
            total_count = len(stations)

            # Wybierz max 3 najważniejsze stacje
            best_stations = self._select_best_stations(stations, max_count=3)

            response = f"🌊 {river_display} - {total_count} stacji pomiarowych\n"
            response += "-" * 35 + "\n\n"

            for i, station in enumerate(best_stations):
                response += self._format_hydro_station(station, compact=(i > 0))
                if i < len(best_stations) - 1:
                    response += "\n"

            if total_count > 3:
                response += f"\n\n📌 Pozostałe stacje: {total_count - 3}"
                response += "\n💡 Podaj nazwę stacji dla szczegółów."

            return response

        except Exception as e:
            print(f"❌ Błąd pobierania rzeki: {e}")
            return await self._fetch_single_hydro_station(fallback_id, river_name)

    async def _fetch_single_hydro_station(self, station_id: str, name: str) -> str:
        """Pobiera dane dla pojedynczej stacji hydrologicznej."""
        data = await self.imgw_client.get_hydro_data(station_id)
        if isinstance(data, list):
            data = data[0] if data else {}

        return self._format_hydro_station(data, compact=False)

    def _format_hydro_station(self, data: dict, compact: bool = False) -> str:
        """Formatuje dane stacji hydrologicznej."""
        river = data.get('rzeka', '?')
        station = data.get('stacja', '?')
        voivodeship = data.get('wojewodztwo', '')
        water_level = data.get('stan_wody', '?')
        water_temp = data.get('temperatura_wody', None)
        flow = data.get('przelyw', None)
        date = data.get('stan_wody_data_pomiaru', '')

        ice_code = data.get('zjawisko_lodowe', None)
        overgrowth_code = data.get('zjawisko_zarastania', None)

        if compact:
            # Wersja skrócona - jedna linia główna + opcjonalnie lód
            loc_info = f"📍 {station}"
            if voivodeship:
                loc_info += f" ({voivodeship})"

            response = f"{loc_info}\n"
            response += f"  💧 Stan: {water_level} cm"

            if flow and flow != 'null':
                response += f", 🌊 przepływ: {flow} m³/s"

            if water_temp and water_temp != 'null':
                response += f", 🌡️ temp: {water_temp}°C"

            ice_desc = self._decode_ice_phenomenon(ice_code)
            if ice_desc:
                response += f"\n  🧊 Lód: {ice_desc}"

            return response

        # Wersja pełna (pierwsza stacja lub pojedyncza)
        response = f"🌊 {river}\n"
        response += f"📍 Stacja: {station}"
        if voivodeship:
            response += f" ({voivodeship})"
        response += "\n\n"

        response += f"💧 Stan wody: {water_level} cm\n"

        if flow and flow != 'null':
            response += f"🌊 Przepływ: {flow} m³/s\n"

        if water_temp and water_temp != 'null':
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