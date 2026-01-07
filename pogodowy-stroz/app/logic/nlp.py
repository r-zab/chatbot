# app/logic/nlp.py

import spacy
from collections import defaultdict
from typing import Optional, Tuple, Dict, List

try:
    from app.services.llm_service import LLMService
except ImportError:
    LLMService = None


class NLPService:
    def __init__(self, use_llm: bool = True, llm_provider: str = "ollama"):
        self.use_llm = use_llm
        self.llm_service: Optional[LLMService] = None
        self.llm_available = False

        if use_llm and LLMService:
            self._init_llm(llm_provider)

        # ========== SMALL TALK ==========
        self.GREETINGS = {
            'cześć', 'czesc', 'czesd', 'hej', 'siema', 'elo', 'yo', 'hejo',
            'witaj', 'witam', 'dzień dobry', 'dzien dobry', 'dobry wieczór',
            'dobry wieczor', 'dobranoc', 'dobry', 'dziendobry',
            'hello', 'hi', 'halo', 'siemka', 'siemano', 'joł', 'jol',
            'hejka', 'hejko', 'cześc', 'czesc', 'cze'
        }

        self.GOODBYES = {
            'dzięki', 'dzieki', 'dziekuje', 'dziękuję', 'dziekuję', 'dziękuje',
            'thanks', 'thx', 'ok', 'okej', 'okay', 'oki', 'okey',
            'pa', 'papa', 'do widzenia', 'dowidzenia', 'dowidenia', 'dowodzenia',
            'nara', 'na razie', 'narazie', 'narka',
            'do zobaczenia', 'dozobaczenia', 'trzymaj się', 'trzymaj sie',
            'dobra', 'git', 'spoko', 'super', 'fajnie', 'elegancko',
            'koniec', 'wystarczy', 'to tyle', 'tyle','dobra koniec', 'ok to tyle', 'to tyle', 'koniec',
            'wystarczy', 'to wszystko', 'to na tyle',
        }

        self.THANKS = {
            'dzięki', 'dzieki', 'dziekuje', 'dziękuję', 'dziekuję',
            'thanks', 'thx', 'wielkie dzięki', 'super dzięki',
            'dzięks', 'dziex', 'thanksy'
        }

        self.CONFUSED = {
            'co', 'co?', 'słucham', 'slucham', 'nie rozumiem',
            'help', 'pomoc', 'pomocy', '?', '??', '???',
            'jak', 'jak to', 'jak to działa', 'jak to dziala',
            'co umiesz', 'co potrafisz', 'czym jesteś', 'czym jestes',
            'kim jesteś', 'kim jestes', 'kto to', 'co to'
        }

        self.CANT_DO_KEYWORDS = {
            'zrób', 'zrob', 'zrobić', 'zrobic', 'wygeneruj', 'generuj', 'stwórz', 'stworz',
            'narysuj', 'namaluj', 'pokaż', 'pokaz', 'wyświetl', 'wyswietl',
            'napisz', 'opowiedz', 'zaśpiewaj', 'zaspiewaj', 'zagraj',
            'oblicz', 'policz', 'przelicz', 'przetłumacz', 'przetlumacz',
            'znajdź', 'znajdz', 'wyszukaj', 'google', 'szukaj',
            'zamów', 'zamow', 'kup', 'zarezerwuj', 'zadzwoń', 'zadzwon',
            'wyślij', 'wyslij', 'email', 'mail', 'sms',
            'otwórz', 'otworz', 'uruchom', 'włącz', 'wlacz', 'wyłącz', 'wylacz'
        }

        self.CANT_DO_OBJECTS = {
            'obraz', 'obrazek', 'zdjęcie', 'zdjecie', 'foto', 'rysunek', 'grafika',
            'kanapka', 'kanapkę', 'kanapke', 'jedzenie', 'kawa', 'herbata', 'pizza',
            'piosenka', 'piosenkę', 'piosenke', 'muzyka', 'film', 'wideo', 'video',
            'kod', 'program', 'aplikacja', 'strona', 'gra',
            'żart', 'zart', 'dowcip', 'historię', 'historie', 'bajka', 'opowieść',
            'mail', 'email', 'wiadomość', 'wiadomosc', 'sms'
        }

        self.NONSENSE_PATTERNS = {
            'asdf', 'qwer', 'zxcv', 'aaa', 'bbb', 'ccc', 'ddd',
            'xxx', 'yyy', 'zzz', 'abc', 'test', 'testing',
            'haha', 'hehe', 'hihi', 'lol', 'lmao', 'xd', 'xdd',
            'blabla', 'lalala', 'dadada', 'nanana', 'tralala'
        }

        # 🔥 SŁOWA KLUCZOWE DLA PROGNOZY
        self.FORECAST_KEYWORDS = {
            'jutro', 'pojutrze', 'za tydzień', 'za tydzien', 'w weekend',
            'w sobotę', 'w sobote', 'w niedzielę', 'w niedziele',
            'za godzinę', 'za godzine', 'za 2 godziny', 'wieczorem',
            'rano', 'w nocy', 'prognoza na', 'będzie padać', 'bedzie padac',
            'będzie wiać', 'bedzie wiac', 'czy będzie', 'czy bedzie',
            'przewidywana', 'przewidywany', 'spodziewana', 'spodziewany',
            'w przyszłym tygodniu', 'w przyszlym tygodniu',
            'na tydzień', 'na tydzien', 'na weekend',
        }

        # 🔥 SŁOWA DO PYTANIA O LISTĘ STACJI
        self.LIST_KEYWORDS = {
            'lista', 'listę', 'liste', 'wszystkie', 'jakie',
            'które', 'ktore', 'pokaz', 'pokaż', 'wymień', 'wymien',
            'stacje', 'stacji', 'stacja', 'punkty', 'punktów', 'punktow',
            'wodowskazy', 'wodowskazów', 'wodowskazow',
            'pomiarowe', 'pomiarowych', 'dostępne', 'dostepne',
        }

        # 🔥 SŁOWA DO PYTANIA O POWIATY (NOWE!)
        self.COUNTY_LIST_KEYWORDS = {
            'powiaty', 'powiatów', 'powiatow', 'powiat',
            'które powiaty', 'ktore powiaty',
            'jakie powiaty', 'dla jakich powiatów',
            'lista powiatów', 'lista powiatow', 'listę powiatów',
            'wszystkie powiaty', 'pełna lista', 'pelna lista',
            'więcej powiatów', 'wiecej powiatow',
            'pozostałe powiaty', 'pozostale powiaty',
            'gdzie jeszcze', 'gdzie obowiązuje', 'gdzie obowiazuje',
            'dotknięte', 'dotkniete', 'objęte', 'objete',
        }

        # ========== RZEKI ==========
        self.KNOWN_RIVERS = {
            'wisła', 'wisla', 'wiśle', 'wisle', 'wisły', 'wisly',
            'odra', 'odrze', 'odry',
            'warta', 'warcie', 'warty',
            'bug', 'bugu', 'bugiem',
            'san', 'sanie', 'sanu',
            'narew', 'narwi', 'narwią',
            'noteć', 'notec', 'noteci',
            'pilica', 'pilicy',
            'dunajec', 'dunajcu',
            'nysa', 'nysie',
            'bobr', 'bóbr', 'bobrze',
            'wieprz', 'wieprza',
            'brda', 'brdzie',
            'gwda', 'gwdzie',
            'prosna', 'prośnie',
            'bzura', 'bzurze',
            'raba', 'rabie',
            'skawa', 'skawie',
            'poprad', 'popradzie',
            'soła', 'sola', 'sole',
            'drwęca', 'drweca',
            'ner', 'nerze',
            'barycz', 'baryczy',
            'tanew', 'tanwi',
            'biebrza', 'biebrzy',
            'pisa', 'pisie',
            'łyna', 'lyna',
            'słupia', 'slupia',
            'parsęta', 'parseta',
            'rega', 'redze',
            'radunia', 'raduni',
            'bystrzyca', 'bystrzyce'
        }

        # 🔥 JEZIORA I ZBIORNIKI
        self.KNOWN_LAKES = {
            'mamry', 'śniardwy', 'sniardwy', 'niegocin', 'jeziorak',
            'łebsko', 'lebsko', 'drawsko', 'miedwie', 'jamno',
            'gopło', 'goplo', 'wigry', 'hańcza', 'hancza',
            'solina', 'solinskie', 'solińskie',
            'zegrzyński', 'zegrzynski', 'zegrze',
            'włocławski', 'wloclawski', 'włocławek', 'wloclawek',
            'czorsztyński', 'czorsztynski', 'czorsztyn',
            'rożnowski', 'roznowski', 'rożnów', 'roznow',
            'dobczycki', 'dobczyce',
            'żywiecki', 'zywiecki', 'żywiec', 'zywiec',
            'otmuchowski', 'otmuchów', 'otmuchow',
            'nyski', 'nysa',
            'turawski', 'turawa',
            'koronowski', 'koronowo',
        }

        # 🔥 BAŁTYK
        self.BALTIC_KEYWORDS = {
            'bałtyk', 'baltyk', 'bałtyku', 'baltyku', 'bałtycki', 'baltycki',
            'morze', 'morza', 'morzu',
            'zatoka', 'zatoki', 'zatoce',
            'zalew', 'zalewu', 'zalewem',
            'wiślany', 'wislany', 'szczeciński', 'szczecinski',
        }

        # ========== WOJEWÓDZTWA ==========
        self.VOIVODESHIPS = {
            'dolnośląskie', 'dolnoslaskie', 'dolnośląska', 'dolnoslaska',
            'kujawsko-pomorskie', 'kujawsko-pomorska',
            'lubelskie', 'lubelska',
            'lubuskie', 'lubuska',
            'łódzkie', 'lodzkie', 'łódzka', 'lodzka',
            'małopolskie', 'malopolskie', 'małopolska', 'malopolska',
            'mazowieckie', 'mazowiecka',
            'opolskie', 'opolska',
            'podkarpackie', 'podkarpacka',
            'podlaskie', 'podlaska',
            'pomorskie', 'pomorska',
            'śląskie', 'slaskie', 'śląska', 'slaska',
            'świętokrzyskie', 'swietokrzyskie', 'świętokrzyska', 'swietokrzyska',
            'warmińsko-mazurskie', 'warminsko-mazurskie', 'warmińsko-mazurska',
            'wielkopolskie', 'wielkopolska',
            'zachodniopomorskie', 'zachodniopomorska'
        }

        # 🔥 REGIONY
        self.REGIONS = {
            'śląsk', 'slask', 'mazowsze', 'podlasie', 'wielkopolska',
            'małopolska', 'malopolska', 'pomorze', 'kaszuby', 'kujawy',
            'warmia', 'mazury', 'podhale', 'lubelszczyzna', 'opolszczyzna',
            'podkarpacie', 'galicja',
        }

        # ========== SŁOWA KLUCZOWE Z WAGAMI ==========
        self.KEYWORDS = {
            'ostrzeżenia': {
                'ostrzeżenie': 3, 'ostrzezenie': 3,
                'alert': 3, 'alerty': 3, 'alertów': 3,
                'zagrożenie': 3, 'zagrozenie': 3,
                'niebezpieczeństwo': 3, 'niebezpieczenstwo': 3,
                'uwaga': 2,
                'burza': 2, 'nawałnica': 3, 'nawalnica': 3,
                'wichura': 3, 'trąba': 3, 'traba': 3,
                'grad': 2, 'ulewa': 2, 'zawieja': 2, 'zamieć': 2,
                'mróz': 1, 'mroz': 1, 'przymrozek': 1,
                'gołoledź': 2, 'gololedz': 2,
                'upał': 2, 'upal': 2,
                'meteo': 2, 'imgw': 2,
                'porywy': 2, 'silny': 1,
            },
            'hydro': {
                'woda': 3, 'wody': 3, 'wodzie': 3,
                'rzeka': 3, 'rzeki': 3, 'rzeką': 3, 'rzece': 3,
                'stan': 2, 'stanu': 2, 'stany': 2,
                'poziom': 3, 'poziomu': 3, 'poziomie': 3,
                'wodowskaz': 3, 'wodowskazu': 3,
                'powódź': 3, 'powodz': 3, 'powodzi': 3,
                'podtopienie': 3, 'wezbranie': 3,
                'hydro': 3, 'hydrologia': 3, 'hydrologiczny': 3,
                'potok': 2, 'strumień': 2, 'strumien': 2,
                'wisła': 3, 'wisla': 3, 'wiśle': 3, 'wisle': 3,
                'odra': 3, 'odrze': 3,
                'warta': 3, 'warcie': 3,
                'bug': 3, 'bugu': 3,
                'narew': 3, 'narwi': 3,
                'san': 3, 'sanie': 3, 'sanu': 3,
                'przepływ': 3, 'przeplyw': 3,
                'jezioro': 3, 'jeziora': 3, 'jeziorze': 3,
                'zbiornik': 3, 'zbiornika': 3, 'zbiorniku': 3,
                'zalew': 3, 'zalewu': 3,
                'bałtyk': 3, 'baltyk': 3, 'morze': 3, 'morza': 3,
                'mamry': 3, 'śniardwy': 3, 'sniardwy': 3,
            },
            'hydro_lista': {
                'lista': 3, 'listę': 3, 'liste': 3,
                'wszystkie': 2, 'jakie': 2,
                'stacje': 3, 'stacji': 3,
                'wodowskazy': 3, 'punkty': 2,
                'dostępne': 2, 'dostepne': 2,
            },
            'pogoda': {
                'pogoda': 3, 'pogody': 3, 'pogodę': 3, 'pogode': 3,
                'prognoza': 3, 'prognozy': 3,
                'temperatura': 3, 'temperatury': 3, 'temperaturę': 3,
                'stopni': 3, 'stopień': 3, 'stopien': 3,
                'ciepło': 2, 'cieplo': 2, 'zimno': 2,
                'ciśnienie': 2, 'cisnienie': 2,
                'wilgotność': 2, 'wilgotnosc': 2,
                'słońce': 2, 'slonce': 2, 'słonecznie': 2,
                'chmura': 2, 'chmury': 2, 'zachmurzenie': 2,
                'deszcz': 2, 'deszczu': 2, 'pada': 2, 'padać': 2,
                'śnieg': 1, 'snieg': 1, 'opad': 1, 'opady': 1,
                'dziś': 2, 'dzis': 2, 'dzisiaj': 2, 'teraz': 2,
                'aktualnie': 2, 'obecnie': 2,
                'jaka': 2, 'jaki': 2, 'jakie': 2, 'ile': 2,
                'wiatr': 2, 'wiatru': 2, 'wieje': 2,
            },
        }

        self.BIGRAM_BONUSES = {
            'pogoda': [
                ('prędkość', 'wiatr'), ('predkosc', 'wiatr'),
                ('kierunek', 'wiatr'),
                ('jaka', 'pogoda'), ('jaki', 'wiatr'),
                ('ile', 'stopni'),
            ],
            'ostrzeżenia': [
                ('silny', 'wiatr'), ('mocny', 'wiatr'),
            ],
            'hydro': [
                ('stan', 'woda'), ('stan', 'wody'),
                ('poziom', 'woda'), ('poziom', 'wody'),
                ('stan', 'rzeka'), ('stan', 'rzeki'),
                ('stan', 'jezioro'), ('stan', 'jeziora'),
                ('stan', 'morze'), ('stan', 'morza'),
            ],
            'hydro_lista': [
                ('lista', 'stacji'), ('lista', 'stacje'),
                ('jakie', 'stacje'), ('wszystkie', 'stacje'),
            ],
        }

        try:
            self.nlp = spacy.load("pl_core_news_sm")
        except OSError:
            print("⚠️ Brak modelu spaCy!")
            self.nlp = None

    def _init_llm(self, provider: str):
        try:
            self.llm_service = LLMService(provider=provider)
            print(f"✅ LLM Service zainicjalizowany (provider: {provider})")
        except Exception as e:
            print(f"⚠️ Nie udało się zainicjalizować LLM: {e}")
            self.llm_service = None

    async def check_llm_availability(self) -> bool:
        if not self.llm_service:
            return False
        try:
            self.llm_available = await self.llm_service.is_available()
            status = "✅ dostępny" if self.llm_available else "❌ niedostępny"
            print(f"🤖 LLM status: {status}")
            return self.llm_available
        except Exception:
            self.llm_available = False
            return False

    def _normalize_text(self, text: str) -> str:
        import unicodedata
        text = text.lower().strip()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        return text.replace("?", "").replace("!", "").replace(".", "").replace(",", "").strip()

    def is_small_talk(self, text: str) -> Tuple[bool, Optional[str]]:
        text_lower = text.lower().strip()
        text_norm = self._normalize_text(text_lower)

        if text_norm in self.GREETINGS or text_lower in self.GREETINGS:
            return True, "greeting"
        if text_norm in self.GOODBYES or text_lower in self.GOODBYES:
            return True, "goodbye"
        if text_norm in self.THANKS or text_lower in self.THANKS:
            return True, "thanks"
        if text_norm in self.CONFUSED or text_lower in self.CONFUSED:
            return True, "help"
        if text_norm in self.NONSENSE_PATTERNS:
            return True, "nonsense"
        if len(text_norm) <= 6 and len(set(text_norm.replace(" ", ""))) <= 2:
            return True, "nonsense"
        return False, None

    def is_cant_do_request(self, text: str) -> bool:
        text_lower = text.lower()
        words = text_lower.split()

        has_action = any(word in self.CANT_DO_KEYWORDS for word in words)
        has_object = any(word in self.CANT_DO_OBJECTS for word in words)

        if has_action and has_object:
            return True

        cant_do_phrases = [
            "zrób mi", "zrob mi", "wygeneruj", "narysuj", "namaluj",
            "opowiedz mi", "zaśpiewaj", "zagraj", "znajdź mi",
            "kup mi", "zamów", "zadzwoń", "wyślij",
        ]
        for phrase in cant_do_phrases:
            if phrase in text_lower:
                weather_words = ['pogoda', 'pogodę', 'temperatur', 'wiatr', 'deszcz']
                hydro_words = ['wod', 'rzek', 'stan', 'poziom']
                if not any(w in text_lower for w in weather_words + hydro_words):
                    return True
        return False

    def is_forecast_request(self, text: str) -> bool:
        """Sprawdza czy użytkownik pyta o prognozę."""
        text_lower = text.lower()

        forecast_phrases = [
            'jutro', 'pojutrze', 'za tydzień', 'za tydzien',
            'w weekend', 'w sobotę', 'w sobote', 'w niedzielę', 'w niedziele',
            'w poniedziałek', 'w poniedzialek', 'we wtorek', 'w środę', 'w srode',
            'w czwartek', 'w piątek', 'w piatek',
            'za godzinę', 'za godzine', 'za 2 godziny', 'za dwie godziny',
            'wieczorem', 'rano', 'w nocy', 'po południu', 'po poludniu',
            'prognoza na', 'będzie padać', 'bedzie padac',
            'czy będzie', 'czy bedzie', 'będzie wiało', 'bedzie wialo',
            'w przyszłym tygodniu', 'w przyszlym tygodniu',
            'na tydzień', 'na tydzien', 'na weekend',
            'przewidywana', 'spodziewana',
        ]

        for phrase in forecast_phrases:
            if phrase in text_lower:
                return True
        return False

    def is_station_list_request(self, text: str) -> bool:
        """Sprawdza czy użytkownik pyta o listę stacji."""
        text_lower = text.lower()

        list_phrases = [
            'lista stacji', 'liste stacji', 'listę stacji',
            'jakie stacje', 'które stacje', 'ktore stacje',
            'wszystkie stacje', 'dostępne stacje', 'dostepne stacje',
            'lista wodowskazów', 'liste wodowskazow',
            'jakie wodowskazy', 'wszystkie wodowskazy',
            'punkty pomiarowe', 'lista punktów',
            'pokaż stacje', 'pokaz stacje',
            'wymień stacje', 'wymien stacje',
        ]

        for phrase in list_phrases:
            if phrase in text_lower:
                return True

        words = set(text_lower.split())
        list_words = {'lista', 'listę', 'liste', 'jakie', 'które', 'ktore', 'wszystkie', 'pokaz', 'pokaż', 'wymień',
                      'wymien'}
        station_words = {'stacje', 'stacji', 'wodowskazy', 'wodowskazów', 'punkty', 'punktów'}

        if list_words & words and station_words & words:
            return True

        return False

    def is_county_list_request(self, text: str) -> bool:
        """🔥 Sprawdza czy użytkownik pyta o listę powiatów z ostrzeżeń."""
        text_lower = text.lower()

        # Frazy bezpośrednie
        county_phrases = [
            'podaj powiaty', 'pokaż powiaty', 'pokaz powiaty',
            'lista powiatów', 'lista powiatow', 'listę powiatów',
            'jakie powiaty', 'które powiaty', 'ktore powiaty',
            'wszystkie powiaty', 'pełna lista', 'pelna lista',
            'więcej powiatów', 'wiecej powiatow',
            'pozostałe powiaty', 'pozostale powiaty',
            'dla jakich powiatów', 'dla jakich powiatow',
            'gdzie obowiązuje', 'gdzie obowiazuje',
            'gdzie jest ostrzeżenie', 'gdzie jest ostrzezenie',
            'gdzie są ostrzeżenia', 'gdzie sa ostrzezenia',
            'dotknięte powiaty', 'dotkniete powiaty',
            'objęte powiaty', 'objete powiaty',
            'w których powiatach', 'w ktorych powiatach',
            'wymień powiaty', 'wymien powiaty',
        ]

        for phrase in county_phrases:
            if phrase in text_lower:
                return True

        # Kombinacje słów
        words = set(text_lower.split())
        action_words = {'podaj', 'pokaż', 'pokaz', 'lista', 'listę', 'liste',
                        'jakie', 'które', 'ktore', 'wszystkie', 'wymień', 'wymien',
                        'pełna', 'pelna', 'więcej', 'wiecej', 'pozostałe', 'pozostale'}
        county_words = {'powiaty', 'powiatów', 'powiatow', 'powiat', 'powiatach'}

        if action_words & words and county_words & words:
            return True

        # Samo "powiaty" jako kontynuacja rozmowy
        if text_lower.strip() in ['powiaty', 'powiatów', 'powiatow', 'które', 'ktore', 'jakie']:
            return True

        return False

    def _lemmatize_text(self, text: str) -> List[str]:
        if not self.nlp:
            return text.lower().split()
        doc = self.nlp(text)
        return [token.lemma_.lower() for token in doc if not token.is_punct]

    async def recognize_intent_async(self, text: str) -> Tuple[Optional[str], Dict]:
        # 1. Small talk
        is_st, st_type = self.is_small_talk(text)
        if is_st:
            return None, {"source": "small_talk", "type": st_type}

        # 2. Prośby spoza funkcji bota
        if self.is_cant_do_request(text):
            return None, {"source": "cant_do"}

        # 3. Pytanie o prognozę
        if self.is_forecast_request(text):
            return "forecast_unavailable", {"source": "rules"}

        # 🔥 4. Pytanie o listę powiatów (NOWE!)
        if self.is_county_list_request(text):
            return "warnings_powiaty", {"source": "rules"}

        # 5. Pytanie o listę stacji
        if self.is_station_list_request(text):
            return "hydro_lista", {"source": "rules"}

        # 6. Próbuj LLM jeśli dostępny
        llm_intent = None
        llm_conf = 0.0
        llm_entities = {}

        if self.use_llm and self.llm_service and self.llm_available:
            try:
                llm_result = await self.llm_service.classify_intent(text)
                llm_intent = llm_result.get("intent")
                llm_conf = float(llm_result.get("confidence", 0.0) or 0.0)
                llm_entities = llm_result.get("entities", {}) or {}

                if llm_intent and llm_conf >= 0.5:
                    print(f"🤖 LLM: '{text}' → {llm_intent} (conf: {llm_conf:.2f})")
                else:
                    llm_intent = None
            except Exception as e:
                print(f"⚠️ LLM error: {e}")
                llm_intent = None

        # 7. Reguły
        rules_intent = self._recognize_intent_rules(text)

        # Logika wyboru
        if llm_intent and llm_conf >= 0.7:
            return llm_intent, {
                "source": "llm",
                "confidence": llm_conf,
                "entities": llm_entities,
            }

        if llm_intent and rules_intent and rules_intent != llm_intent and 0.5 <= llm_conf < 0.7:
            return rules_intent, {"source": "rules"}

        if llm_intent and llm_conf >= 0.5 and not rules_intent:
            return llm_intent, {
                "source": "llm",
                "confidence": llm_conf,
                "entities": llm_entities,
            }

        return rules_intent, {"source": "rules"}

    def recognize_intent(self, text: str) -> Optional[str]:
        is_st, _ = self.is_small_talk(text)
        if is_st:
            return None
        if self.is_cant_do_request(text):
            return None
        if self.is_forecast_request(text):
            return "forecast_unavailable"
        if self.is_county_list_request(text):
            return "warnings_powiaty"
        if self.is_station_list_request(text):
            return "hydro_lista"
        return self._recognize_intent_rules(text)

    def _recognize_intent_rules(self, text: str) -> Optional[str]:
        lemmas = self._lemmatize_text(text)
        text_lower = text.lower()

        water_body_bonus = 0
        for river in self.KNOWN_RIVERS:
            if river in text_lower:
                water_body_bonus = 3
                break
        for lake in self.KNOWN_LAKES:
            if lake in text_lower:
                water_body_bonus = 3
                break
        for baltic in self.BALTIC_KEYWORDS:
            if baltic in text_lower:
                water_body_bonus = 3
                break

        scores = defaultdict(float)

        if water_body_bonus > 0:
            scores["hydro"] += water_body_bonus

        for word in lemmas:
            for intent, keywords in self.KEYWORDS.items():
                if word in keywords:
                    scores[intent] += keywords[word]

        for i in range(len(lemmas) - 1):
            bigram = (lemmas[i], lemmas[i + 1])
            for intent, bigram_list in self.BIGRAM_BONUSES.items():
                if bigram in bigram_list:
                    scores[intent] += 3.0

        print(f"🔍 Rules: '{text}' → {dict(scores)}")

        if not scores:
            return None

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        if max_score < 2.0:
            return None

        if abs(scores.get("hydro", 0) - scores.get("pogoda", 0)) < 1.0:
            if any(word in lemmas for word in ["woda", "rzeka", "poziom", "wodowskaz", "jezioro", "morze"]):
                return "hydro"

        if water_body_bonus > 0:
            return "hydro"

        return best_intent

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        locations = {"placeName": [], "geogName": []}
        text_lower = text.lower()

        for region in self.REGIONS:
            if region in text_lower:
                if region not in locations["geogName"]:
                    locations["geogName"].append(region)

        for voivodeship in self.VOIVODESHIPS:
            if voivodeship in text_lower:
                if voivodeship not in locations["geogName"]:
                    locations["geogName"].append(voivodeship)

        for river in self.KNOWN_RIVERS:
            if river in text_lower:
                base = self._get_river_base_form(river)
                if base and base not in locations["geogName"]:
                    locations["geogName"].append(base)

        for lake in self.KNOWN_LAKES:
            if lake in text_lower:
                if lake not in locations["geogName"]:
                    locations["geogName"].append(lake)

        for baltic in self.BALTIC_KEYWORDS:
            if baltic in text_lower:
                if "bałtyk" not in locations["geogName"] and "baltyk" not in locations["geogName"]:
                    locations["geogName"].append("bałtyk")
                break

        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                name = ent.lemma_ if ent.lemma_ else ent.text
                name = name.strip()
                if name.lower() in [r.lower() for r in locations["geogName"]]:
                    continue
                if ent.label_ == "placeName":
                    if name not in locations["placeName"]:
                        locations["placeName"].append(name)
                elif ent.label_ == "geogName":
                    if name not in locations["geogName"]:
                        locations["geogName"].append(name)

        return locations

    def _get_river_base_form(self, river: str) -> str:
        RIVER_LEMMAS = {
            "wiśle": "wisła", "wisle": "wisła", "wisły": "wisła",
            "wisly": "wisła", "wisla": "wisła",
            "sanie": "san", "sanu": "san",
            "odrze": "odra", "odry": "odra",
            "warcie": "warta", "warty": "warta",
            "narwi": "narew", "narwią": "narew",
            "bugu": "bug", "bugiem": "bug",
            "noteci": "noteć", "notec": "noteć",
            "pilicy": "pilica", "dunajcu": "dunajec",
            "nysie": "nysa", "nysy": "nysa",
            "bobrze": "bóbr", "bobr": "bóbr",
            "wieprza": "wieprz", "brdzie": "brda",
            "gwdzie": "gwda", "biebrzy": "biebrza",
            "nerze": "ner",
        }
        return RIVER_LEMMAS.get(river.lower(), river.lower())

    def extract_voivodeship(self, text: str) -> str | None:
        """🔥 Wyciąga województwo z tekstu (z obsługą literówek i słów pisanych razem)."""
        text_lower = text.lower()

        # 🔥 Słowa pisane razem → województwa
        merged_words = {
            'dolnymmazowieckim': 'mazowieckie',
            'namazowszu': 'mazowieckie',
            'wmazowieckim': 'mazowieckie',
            'dolnyslaskim': 'dolnoslaskie',
            'nadolnymslasku': 'dolnoslaskie',
            'wdolnoslaskim': 'dolnoslaskie',
            'wmalopolskim': 'malopolskie',
            'wmalopolsce': 'malopolskie',
            'wwielkopolskim': 'wielkopolskie',
            'wwielkopolsce': 'wielkopolskie',
            'wslaskim': 'slaskie',
            'naslasku': 'slaskie',
            'warminskomazurskim': 'warminsko-mazurskie',
            'wwarminskomazurskim': 'warminsko-mazurskie',
            'kujawskopomorskim': 'kujawsko-pomorskie',
            'wkujawskopomorskim': 'kujawsko-pomorskie',
            'wlubelskim': 'lubelskie',
            'nalubelszczyznie': 'lubelskie',
            'wpodlaskim': 'podlaskie',
            'napodlasiu': 'podlaskie',
            'wpomorskim': 'pomorskie',
            'napomorzu': 'pomorskie',
        }

        for merged, voiv in merged_words.items():
            if merged in text_lower.replace(' ', ''):
                return voiv

        # Sprawdź wszystkie warianty z myślnikami
        voivodeship_patterns = {
            'warminsko-mazurskie': 'warminsko-mazurskie',
            'warminsko mazurskie': 'warminsko-mazurskie',
            'warmińsko-mazurskie': 'warminsko-mazurskie',
            'warmińsko mazurskie': 'warminsko-mazurskie',
            'kujawsko-pomorskie': 'kujawsko-pomorskie',
            'kujawsko pomorskie': 'kujawsko-pomorskie',
            'zachodnio-pomorskie': 'zachodniopomorskie',
            'zachodnio pomorskie': 'zachodniopomorskie',
        }

        for pattern, normalized in voivodeship_patterns.items():
            if pattern in text_lower:
                return normalized

        # Sprawdź standardowe województwa
        for voiv in self.VOIVODESHIPS:
            if voiv in text_lower:
                return voiv

        return None

    def has_multiple_intents(self, text: str) -> bool:
        """
        Sprawdza czy użytkownik pyta o wiele rzeczy naraz.
        np. "Pogoda i ostrzeżenia Warszawa"
        """
        text_lower = text.lower()

        # Słowa łączące
        connectors = [' i ', ' oraz ', ' a także ', ' plus ', ' a ']

        has_connector = any(c in text_lower for c in connectors)

        if not has_connector:
            return False

        # Sprawdź czy są słowa z RÓŻNYCH intencji
        pogoda_words = {'pogoda', 'pogode', 'pogody', 'temperatura', 'temperatury',
                        'wiatr', 'wiatru', 'deszcz', 'deszczu', 'stopni', 'cieplo', 'zimno'}
        hydro_words = {'woda', 'wody', 'wodzie', 'rzeka', 'rzeki', 'stan', 'stanu',
                       'poziom', 'poziomu', 'wisla', 'wisła', 'odra', 'warta'}
        alert_words = {'ostrzezenia', 'ostrzeżenia', 'ostrzezenie', 'ostrzeżenie',
                       'alerty', 'alert', 'burza', 'burze', 'zagrozenie', 'zagrożenie'}

        words = set(text_lower.split())

        # Sprawdź ile kategorii intencji jest w tekście
        has_pogoda = bool(words & pogoda_words)
        has_hydro = bool(words & hydro_words)
        has_alert = bool(words & alert_words)

        # Jeśli są słowa z więcej niż jednej kategorii = wiele intencji
        intent_count = sum([has_pogoda, has_hydro, has_alert])

        if intent_count >= 2:
            print(f"   ⚠️ Wykryto wiele intencji: pogoda={has_pogoda}, hydro={has_hydro}, alert={has_alert}")
            return True

        return False