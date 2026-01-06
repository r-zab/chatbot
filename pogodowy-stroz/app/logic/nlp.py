# app/logic/nlp.py
import spacy
from collections import defaultdict


class NLPService:
    def __init__(self):
        # 🔥 ROZBUDOWANY SMALL TALK
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
            'koniec', 'wystarczy', 'to tyle', 'tyle'
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

        # 🔥 NOWE: Rzeczy których bot NIE UMIE
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

        # 🔥 NOWE: Bzdury / nonsens
        self.NONSENSE_PATTERNS = {
            'asdf', 'qwer', 'zxcv', 'aaa', 'bbb', 'ccc', 'ddd',
            'xxx', 'yyy', 'zzz', 'abc', 'test', 'testing',
            'haha', 'hehe', 'hihi', 'lol', 'lmao', 'xd', 'xdd',
            'blabla', 'lalala', 'dadada', 'nanana', 'tralala'
        }

        # Lista znanych rzek (żeby nie mylić z innymi słowami)
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

        # SŁOWA KLUCZOWE Z WAGAMI
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
                'porywy': 2, 'silny': 1
            },
            'hydro': {
                'woda': 3, 'wody': 3,
                'rzeka': 3, 'rzeki': 3, 'rzeką': 3,
                'stan': 2, 'stanu': 2,
                'poziom': 3, 'poziomu': 3,
                'wodowskaz': 3, 'wodowskazu': 3,
                'powódź': 3, 'powodz': 3,
                'podtopienie': 3, 'wezbranie': 3,
                'hydro': 3, 'hydrologia': 3,
                'potok': 2, 'strumień': 2,
                'wisła': 2, 'wisla': 2, 'odra': 2, 'warta': 2,
                'bug': 2, 'narew': 2, 'san': 2, 'noteć': 2, 'notec': 2,
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
                'jutro': 2, 'dziś': 2, 'dzis': 2, 'dzisiaj': 2,
                'jaka': 2, 'jaki': 2, 'jakie': 2, 'ile': 2,
                'wiatr': 2, 'wiatru': 2, 'wieje': 2,
                'prędkość': 3, 'predkosc': 3, 'kierunek': 2,
            }
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
            ]
        }

        try:
            self.nlp = spacy.load("pl_core_news_sm")
        except OSError:
            print("⚠️ Brak modelu spaCy!")
            self.nlp = None

    def _normalize_text(self, text: str) -> str:
        """Normalizuje tekst do porównań."""
        import unicodedata
        text = text.lower().strip()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        return text.replace("?", "").replace("!", "").replace(".", "").replace(",", "").strip()

    def is_small_talk(self, text: str) -> tuple[bool, str | None]:
        """Sprawdza czy tekst to small talk."""
        text_lower = text.lower().strip()
        text_norm = self._normalize_text(text_lower)

        # Powitania
        if text_norm in self.GREETINGS or text_lower in self.GREETINGS:
            return (True, 'greeting')

        # Pożegnania / podziękowania
        if text_norm in self.GOODBYES or text_lower in self.GOODBYES:
            return (True, 'goodbye')

        if text_norm in self.THANKS or text_lower in self.THANKS:
            return (True, 'thanks')

        # Pomoc
        if text_norm in self.CONFUSED or text_lower in self.CONFUSED:
            return (True, 'help')

        # Nonsens
        if text_norm in self.NONSENSE_PATTERNS:
            return (True, 'nonsense')

        # Sprawdź czy to bardzo krótki nonsens (1-3 powtórzone litery)
        if len(text_norm) <= 6 and len(set(text_norm.replace(' ', ''))) <= 2:
            return (True, 'nonsense')

        return (False, None)

    def is_cant_do_request(self, text: str) -> bool:
        """
        🔥 NOWE: Sprawdza czy użytkownik prosi o coś czego bot nie umie.
        np. "zrób mi kanapkę", "wygeneruj obraz"
        """
        text_lower = text.lower()
        words = text_lower.split()

        has_action = any(word in self.CANT_DO_KEYWORDS for word in words)
        has_object = any(word in self.CANT_DO_OBJECTS for word in words)

        # Jeśli jest akcja + obiekt który nie jest pogodą/rzeką
        if has_action and has_object:
            return True

        # Specjalne frazy
        cant_do_phrases = [
            'zrób mi', 'zrob mi', 'wygeneruj', 'narysuj', 'namaluj',
            'opowiedz mi', 'zaśpiewaj', 'zagraj', 'znajdź mi',
            'kup mi', 'zamów', 'zadzwoń', 'wyślij'
        ]

        for phrase in cant_do_phrases:
            if phrase in text_lower:
                # Sprawdź czy to nie jest prośba o pogodę/hydro
                weather_words = ['pogoda', 'pogodę', 'temperatur', 'wiatr', 'deszcz']
                hydro_words = ['wod', 'rzek', 'stan', 'poziom']

                if not any(w in text_lower for w in weather_words + hydro_words):
                    return True

        return False

    def _lemmatize_text(self, text: str) -> list[str]:
        """Zamienia tekst na listę lemmatów."""
        if not self.nlp:
            return text.lower().split()

        doc = self.nlp(text)
        return [token.lemma_.lower() for token in doc if not token.is_punct]

    def recognize_intent(self, text: str) -> str | None:
        """Rozpoznaje intencję."""
        # Sprawdź small talk
        is_st, st_type = self.is_small_talk(text)
        if is_st:
            print(f"🔍 NLP: Small talk ({st_type})")
            return None

        # 🔥 Sprawdź czy to prośba o coś czego nie umiemy
        if self.is_cant_do_request(text):
            print(f"🔍 NLP: Can't do request")
            return None

        lemmas = self._lemmatize_text(text)
        text_lower = text.lower()

        # Bonus za rzekę
        river_bonus = 0
        for river in self.KNOWN_RIVERS:
            if river in text_lower:
                river_bonus = 3
                break

        scores = defaultdict(float)

        if river_bonus > 0:
            scores['hydro'] += river_bonus

        for word in lemmas:
            for intent, keywords in self.KEYWORDS.items():
                if word in keywords:
                    scores[intent] += keywords[word]

        for i in range(len(lemmas) - 1):
            bigram = (lemmas[i], lemmas[i + 1])
            for intent, bigram_list in self.BIGRAM_BONUSES.items():
                if bigram in bigram_list:
                    scores[intent] += 3.0

        print(f"🔍 NLP: '{text}' → {dict(scores)}")

        if not scores:
            return None

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        if max_score < 2.0:
            return None

        # Rozstrzyganie remisów
        if abs(scores.get('hydro', 0) - scores.get('pogoda', 0)) < 1.0:
            if any(word in lemmas for word in ['woda', 'rzeka', 'poziom', 'wodowskaz']):
                return 'hydro'
            if river_bonus > 0:
                return 'hydro'

        return best_intent

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """Wyciąga nazwy geograficzne z tekstu."""
        locations = {'placeName': [], 'geogName': []}
        text_lower = text.lower()

        # Szukaj znanych rzek
        for river in self.KNOWN_RIVERS:
            if river in text_lower:
                base = self._get_river_base_form(river)
                if base and base not in locations['geogName']:
                    locations['geogName'].append(base)

        # spaCy NER
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                name = ent.lemma_ if ent.lemma_ else ent.text
                name = name.strip()

                if name.lower() in [r.lower() for r in locations['geogName']]:
                    continue

                if ent.label_ == 'placeName':
                    if name not in locations['placeName']:
                        locations['placeName'].append(name)
                elif ent.label_ == 'geogName':
                    if name not in locations['geogName']:
                        locations['geogName'].append(name)

        return locations

    def _get_river_base_form(self, river: str) -> str:
        RIVER_LEMMAS = {
            'wiśle': 'wisła', 'wisle': 'wisła', 'wisły': 'wisła',
            'wisly': 'wisła', 'wisla': 'wisła',
            'sanie': 'san', 'sanu': 'san',
            'odrze': 'odra', 'odry': 'odra',
            'warcie': 'warta', 'warty': 'warta',
            'narwi': 'narew', 'narwią': 'narew',
            'bugu': 'bug', 'bugiem': 'bug',
            'noteci': 'noteć', 'notec': 'noteć',
            'pilicy': 'pilica', 'dunajcu': 'dunajec',
            'nysie': 'nysa', 'nysy': 'nysa',
            'bobrze': 'bóbr', 'bobr': 'bóbr',
            'wieprza': 'wieprz', 'brdzie': 'brda',
            'gwdzie': 'gwda', 'biebrzy': 'biebrza',
            'nerze': 'ner',
        }
        return RIVER_LEMMAS.get(river.lower(), river.lower())