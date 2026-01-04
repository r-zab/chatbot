# app/logic/nlp.py
import spacy
from collections import defaultdict


class NLPService:
    def __init__(self):
        # 🔥 NOWE: Obsługa small talk
        self.GREETINGS = {
            'cześć', 'czesc', 'czesd', 'hej', 'siema', 'elo', 'yo',
            'witaj', 'witam', 'dzień dobry', 'dzien dobry', 'dobry wieczór',
            'hello', 'hi', 'halo'
        }

        self.GOODBYES = {
            'dzięki', 'dzieki', 'dziekuje', 'dziękuję', 'dziekuję',
            'thanks', 'thx', 'ok', 'okej', 'okay',
            'pa', 'papa', 'do widzenia', 'nara', 'na razie',
            'do zobaczenia', 'trzymaj się', 'trzymaj sie'
        }

        self.CONFUSED = {
            'co', 'co?', 'słucham', 'slucham', 'nie rozumiem',
            'help', 'pomoc', '?', '??', '???'
        }

        # 🔥 Lista znanych polskich rzek (do lepszego rozpoznawania)
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
            'prosna', 'prośnie',
            'bzura', 'bzurze',
            'brda', 'brdzie',
            'wieprz', 'wieprza',
            'raba', 'rabie',
            'poprad', 'popradzie',
            'soła', 'sole',
            'skawa', 'skawie',
            'drwęca', 'drweca',
            'bóbr', 'bobr', 'bobrze',
            'gwda', 'gwdzie',
            'ner', 'nerze',
            'barycz', 'baryczy',
            'widawka', 'widawce',
            'kamienna', 'kamiennej',
            'tanew', 'tanwi',
        }

        # SŁOWA KLUCZOWE Z WAGAMI
        self.KEYWORDS = {
            'ostrzeżenia': {
                # SILNE (waga 3)
                'ostrzeżenie': 3, 'ostrzezenie': 3,  # 🔥 bez polskich znaków
                'alert': 3, 'alerty': 3, 'alertów': 3,  # 🔥 DODANE!
                'zagrożenie': 3, 'zagrozenie': 3,
                'niebezpieczeństwo': 3, 'niebezpieczenstwo': 3,
                'uwaga': 2, 'ryzyko': 2,
                # Zjawiska
                'burza': 2, 'nawałnica': 3, 'nawalnica': 3,
                'wichura': 3, 'szkwał': 2, 'trąba': 3, 'traba': 3,
                'grad': 2, 'ulewa': 2, 'zawieja': 2, 'zamieć': 2, 'zamiec': 2,
                'mróz': 1, 'mroz': 1, 'przymrozek': 1,
                'gołoledź': 2, 'gololedz': 2,
                'upał': 2, 'upal': 2, 'spiekota': 2,
                # Techniczne
                'meteo': 2, 'rcb': 3, 'imgw': 2,
                'kod': 1, 'czerwony': 2, 'pomarańczowy': 2, 'pomaranczowy': 2, 'żółty': 1, 'zolty': 1,
                # Wiatr jako słaby sygnał ostrzeżeń
                'porywy': 2, 'silny': 1, 'mocny': 1
            },
            'hydro': {
                # SILNE (waga 3)
                'woda': 3, 'wody': 3,  # 🔥 DODANE odmiany
                'rzeka': 3, 'rzeki': 3, 'rzeką': 3,
                'stan': 2, 'stanu': 2,  # 🔥 Zmniejszona waga (konflikt z "stan pogody")
                'poziom': 3, 'poziomu': 3,
                'wodowskaz': 3, 'wodowskazu': 3,
                'powódź': 3, 'powodz': 3,
                'podtopienie': 3, 'zalanie': 3, 'wezbranie': 3,
                'hydro': 3, 'hydrologia': 3, 'hydrologiczny': 3,
                # Średnie (waga 2)
                'potok': 2, 'strumień': 2, 'strumien': 2,
                'rzeczny': 2, 'jezioro': 2,
                'kulminacja': 2, 'alarmowy': 2, 'ostrzegawczy': 2,
                'głębokość': 2, 'glebokosc': 2,
                # Nazwy głównych rzek (waga 2)
                'wisła': 2, 'wisla': 2, 'odra': 2, 'warta': 2,
                'bug': 2, 'narew': 2, 'san': 2, 'noteć': 2, 'notec': 2,
                'pilica': 2, 'dunajec': 2,
            },
            'pogoda': {
                # SILNE (waga 3)
                'pogoda': 3, 'pogody': 3, 'pogodę': 3, 'pogode': 3,
                'prognoza': 3, 'prognozy': 3,
                'temperatura': 3, 'temperatury': 3, 'temperaturę': 3, 'temperature': 3,
                'stopni': 3, 'stopień': 3, 'stopien': 3,
                # Parametry (waga 2-3)
                'ciepło': 2, 'cieplo': 2, 'zimno': 2,
                'ciśnienie': 2, 'cisnienie': 2, 'hpa': 2,
                'wilgotność': 2, 'wilgotnosc': 2,
                'celsjusz': 2, 'celsjusza': 2,
                # Zjawiska łagodne (waga 2)
                'słońce': 2, 'slonce': 2, 'słonecznie': 2, 'slonecznie': 2,
                'chmura': 2, 'chmury': 2, 'zachmurzenie': 2,
                'deszcz': 2, 'deszczu': 2, 'pada': 2, 'padać': 2, 'padac': 2,
                'mżawka': 2, 'mzawka': 2,
                'śnieg': 1, 'snieg': 1, 'opad': 1, 'opady': 1,
                # Czasowe (waga 2)
                'jutro': 2, 'dziś': 2, 'dzis': 2, 'dzisiaj': 2, 'teraz': 2,
                'weekend': 2, 'tydzień': 1, 'tydzien': 1,
                # Pytania
                'jaka': 2, 'jaki': 2, 'jakie': 2, 'ile': 2,
                'będzie': 1, 'bedzie': 1, 'jest': 1,
                # Wiatr jako parametr pogody (waga 2-3)
                'wiatr': 2, 'wiatru': 2, 'wieje': 2,
                'prędkość': 3, 'predkosc': 3, 'kierunek': 2,
                'metr': 2, 'sekunda': 2, 'm/s': 3,
            }
        }

        # Bigramy - bonus za kombinacje słów
        self.BIGRAM_BONUSES = {
            'pogoda': [
                ('prędkość', 'wiatr'), ('predkosc', 'wiatr'),
                ('kierunek', 'wiatr'),
                ('jaka', 'pogoda'), ('jaki', 'wiatr'),
                ('będzie', 'pogoda'), ('bedzie', 'pogoda'),
                ('ile', 'stopni'),
            ],
            'ostrzeżenia': [
                ('silny', 'wiatr'), ('mocny', 'wiatr'),
                ('ostrzeżenie', 'meteorologiczny'),
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

    def is_small_talk(self, text: str) -> tuple[bool, str | None]:
        """
        🔥 NOWE: Sprawdza czy tekst to small talk (powitanie, pożegnanie, etc.)
        Zwraca (True, typ) lub (False, None)
        """
        text_lower = text.lower().strip()
        text_normalized = self._normalize_for_check(text_lower)

        # Sprawdź dokładne dopasowanie
        if text_normalized in self.GREETINGS or text_lower in self.GREETINGS:
            return (True, 'greeting')

        if text_normalized in self.GOODBYES or text_lower in self.GOODBYES:
            return (True, 'goodbye')

        if text_normalized in self.CONFUSED or text_lower in self.CONFUSED:
            return (True, 'confused')

        # Sprawdź czy to pojedyncze słowo które jest powitaniem/pożegnaniem
        if len(text_lower.split()) == 1:
            if text_normalized in self.GREETINGS:
                return (True, 'greeting')
            if text_normalized in self.GOODBYES:
                return (True, 'goodbye')

        return (False, None)

    def _normalize_for_check(self, text: str) -> str:
        """Normalizuje tekst do porównań (bez polskich znaków)."""
        import unicodedata
        text = text.lower().strip()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        return text.replace("?", "").replace("!", "").replace(".", "").strip()

    def _lemmatize_text(self, text: str) -> list[str]:
        """Zamienia tekst na listę lemmatów."""
        if not self.nlp:
            return text.lower().split()

        doc = self.nlp(text)
        return [token.lemma_.lower() for token in doc if not token.is_punct]

    def recognize_intent(self, text: str) -> str | None:
        """
        Rozpoznaje intencję metodą WAŻONEJ punktacji.
        """
        # 🔥 NOWE: Sprawdź czy to small talk
        is_st, st_type = self.is_small_talk(text)
        if is_st:
            print(f"🔍 NLP: Small talk wykryty ({st_type})")
            return None  # Brak intencji dla small talk

        lemmas = self._lemmatize_text(text)
        text_lower = text.lower()

        # 🔥 NOWE: Bonus za wykrycie nazwy rzeki w tekście
        river_bonus = 0
        for river in self.KNOWN_RIVERS:
            if river in text_lower:
                river_bonus = 3
                print(f"   🏞️ Wykryto rzekę: {river}")
                break

        scores = defaultdict(float)

        # Dodaj bonus za rzekę do hydro
        if river_bonus > 0:
            scores['hydro'] += river_bonus

        # Punktacja za pojedyncze słowa
        for word in lemmas:
            for intent, keywords in self.KEYWORDS.items():
                if word in keywords:
                    scores[intent] += keywords[word]

        # Bonus za bigramy
        for i in range(len(lemmas) - 1):
            bigram = (lemmas[i], lemmas[i + 1])
            for intent, bigram_list in self.BIGRAM_BONUSES.items():
                if bigram in bigram_list:
                    scores[intent] += 3.0

        print(f"🔍 NLP: '{text}'")
        print(f"   Lemmaty: {lemmas}")
        print(f"   Wyniki: {dict(scores)}")

        if not scores:
            return None

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        if max_score < 2.0:
            print(f"   ⚠️ Wynik za niski ({max_score})")
            return None

        # Rozstrzyganie remisów
        if abs(scores.get('hydro', 0) - scores.get('pogoda', 0)) < 1.0:
            if any(word in lemmas for word in ['woda', 'rzeka', 'poziom', 'wodowskaz']):
                print(f"   🎯 Remis → HYDRO")
                return 'hydro'
            if river_bonus > 0:
                print(f"   🎯 Remis + rzeka → HYDRO")
                return 'hydro'

        print(f"   ✅ Intencja: {best_intent} ({max_score} pkt)")
        return best_intent

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """
        Wyciąga nazwy geograficzne z tekstu.
        🔥 ULEPSZONE: Wykrywa też rzeki które spaCy może przeoczyć.
        """
        locations = {'placeName': [], 'geogName': []}
        text_lower = text.lower()

        # 1. Najpierw szukaj znanych rzek
        for river in self.KNOWN_RIVERS:
            if river in text_lower:
                # Normalizuj do formy podstawowej
                base = self._get_river_base_form(river)
                if base and base not in locations['geogName']:
                    locations['geogName'].append(base)
                    print(f"   🏞️ Znaleziono rzekę: {river} → {base}")

        # 2. spaCy NER
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                name = ent.lemma_ if ent.lemma_ else ent.text
                name = name.strip()

                # Pomiń jeśli to już jest dodana rzeka
                if name.lower() in [r.lower() for r in locations['geogName']]:
                    continue

                if ent.label_ == 'placeName':
                    if name not in locations['placeName']:
                        locations['placeName'].append(name)
                elif ent.label_ == 'geogName':
                    if name not in locations['geogName']:
                        locations['geogName'].append(name)

        print(f"   📍 Encje: {locations}")
        return locations

    def _get_river_base_form(self, river: str) -> str:
        """Mapuje odmianę rzeki na formę podstawową."""
        RIVER_LEMMAS = {
            # Wisła
            'wiśle': 'wisła', 'wisle': 'wisła', 'wisły': 'wisła',
            'wisly': 'wisła', 'wisla': 'wisła',
            # San
            'sanie': 'san', 'sanu': 'san',
            # Odra
            'odrze': 'odra', 'odry': 'odra',
            # Warta
            'warcie': 'warta', 'warty': 'warta',
            # Narew
            'narwi': 'narew', 'narwią': 'narew',
            # Bug
            'bugu': 'bug', 'bugiem': 'bug',
            # Noteć
            'noteci': 'noteć', 'notec': 'noteć',
            # Inne
            'pilicy': 'pilica', 'dunajcu': 'dunajec',
            'nysie': 'nysa', 'nysy': 'nysa',
            'prośnie': 'prosna', 'bzurze': 'bzura',
            'brdzie': 'brda', 'gwdzie': 'gwda',
            'wieprza': 'wieprz', 'rabie': 'raba',
            'popradzie': 'poprad', 'sole': 'soła',
            'skawie': 'skawa', 'drwęcy': 'drwęca',
            'bobrze': 'bóbr', 'bobr': 'bóbr',
        }
        return RIVER_LEMMAS.get(river.lower(), river.lower())