# app/logic/nlp.py
import spacy

class NLPService:
    def __init__(self):
        # --- BARDZO SZCZEGÓŁOWE SŁOWA KLUCZOWE ---
        # Używamy form podstawowych (mianownik lp), bo kod poniżej zamieni
        # tekst użytkownika na lemmaty (np. "ostrzeżeń" -> "ostrzeżenie")
        self.KEYWORDS = {
            'ostrzeżenia': [
                # Główne
                'ostrzeżenie', 'alert', 'zagrożenie', 'uwaga', 'niebezpieczeństwo', 'ryzyko',
                # Zjawiska
                'burza', 'nawałnica', 'wichura', 'szkwał', 'trąba', 'wiatr', 'porywy',
                'grad', 'opad', 'ulewa', 'śnieg', 'zawieja', 'zamieć',
                'mróz', 'przymrozek', 'gołoledź', 'szklanka', 'lodowica',
                'upał', 'gorąco', 'spiekota',
                'mgła', 'smog', 'jakość', 'powietrze',
                # Techniczne
                'meteo', 'rcb', 'imgw', 'stopień', 'kod', 'czerwony', 'pomarańczowy', 'żółty'
            ],
            'hydro': [
                # Woda i rzeki
                'woda', 'rzeka', 'potok', 'strumień', 'rzeczny', 'jezioro', 'zalew',
                'stan', 'poziom', 'głębokość', 'wodowskaz',
                # Zjawiska hydro
                'powódź', 'podtopienie', 'zalanie', 'wylewać', 'wystąpić', 'brzeg',
                'fala', 'wezbranie', 'kulminacja', 'alarmowy', 'ostrzegawczy',
                # Konkretne rzeki (dla pewności, choć DataService też to robi)
                'wisła', 'odra', 'warta', 'bug', 'narew', 'san', 'noteć'
            ],
            'pogoda': [
                # Ogólne
                'pogoda', 'prognoza', 'aura', 'atmosfera', 'klimat', 'czas',
                # Parametry
                'temperatura', 'stopień', 'celsjusz', 'ciepło', 'zimno',
                'ciśnienie', 'hpa', 'barometr',
                'wilgotność', 'punkt', 'rosy',
                # Zjawiska pogodowe (lekkie/ogólne)
                'słońce', 'chmura', 'zachmurzenie', 'przejaśnienie',
                'deszcz', 'mżawka', 'padać', 'mokro', 'sucho',
                'wiosna', 'lato', 'jesień', 'zima', 'weekend', 'jutro', 'dziś',
                'jaka', 'czy', 'będzie'
            ]
        }

        # Ładowanie modelu językowego
        try:
            # Model 'pl_core_news_sm' posiada wbudowany lematyzator dla języka polskiego
            self.nlp = spacy.load("pl_core_news_sm")
        except OSError:
            print("OSTRZEŻENIE: Brak modelu spaCy. Uruchom w terminalu: python -m spacy download pl_core_news_sm")
            self.nlp = None

    def _lemmatize_text(self, text: str) -> list[str]:
        """
        Pomocnicza funkcja: zamienia zdanie na listę form podstawowych.
        Np. "Jaka jest pogoda w Skrzynicach?" -> ['jaki', 'być', 'pogoda', 'w', 'skrzynice']
        """
        if not self.nlp:
            return text.lower().split()

        doc = self.nlp(text)
        # Zwracamy listę lemmatów (małymi literami), ignorując interpunkcję
        return [token.lemma_.lower() for token in doc if not token.is_punct]

    def recognize_intent(self, text: str) -> str | None:
        """
        Rozpoznaje intencję metodą punktacji na LEMMATACH.
        To sprawia, że 'ostrzeżeń' (dopełniacz) trafi w słowo kluczowe 'ostrzeżenie' (mianownik).
        """
        lemmas = self._lemmatize_text(text)

        # Słownik punktacji
        scores = {'ostrzeżenia': 0, 'hydro': 0, 'pogoda': 0}

        # Iterujemy po każdym słowie z zapytania (w formie podstawowej)
        for word in lemmas:
            for intent, keywords in self.KEYWORDS.items():
                if word in keywords:
                    scores[intent] += 1

        # Znajdź najlepszy wynik
        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        print(f"DEBUG NLP: Tekst='{text}' -> Lemmaty={lemmas} -> Wynik={scores}")

        # Logika priorytetów:
        # Jeśli jest remis, a padło słowo "woda/rzeka", preferuj hydro.
        if scores['hydro'] > 0 and scores['hydro'] == scores['pogoda']:
            return 'hydro'

        # ZMIANA: Jeśli wynik > 0, zwracamy intencję.
        # Jeśli 0 (brak słów kluczowych), zwracamy None.
        if max_score > 0:
            return best_intent

        return None

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """
        Wyciąga nazwy geograficzne, próbując przywrócić ich formę podstawową.
        To klucz do "w Skrzynicach" -> "Skrzynice".
        """
        locations = {'placeName': [], 'geogName': []}

        if self.nlp:
            doc = self.nlp(text)

            for ent in doc.ents:
                # ent.text = "Skrzynicach" (to co wpisał user)
                # ent.lemma_ = "Skrzynice" (forma podstawowa - TEGO CHCEMY!)

                # Czasem lemma_ jest błędna w małych modelach, więc bierzemy lemma,
                # a jeśli puste/dziwne, to original text.
                location_name = ent.lemma_ if ent.lemma_ else ent.text

                # Dodatkowe czyszczenie (np. usunięcie "w " z początku jeśli spaCy to złapało)
                location_name = location_name.replace("w ", "").strip()

                if ent.label_ == 'placeName':  # Miasta, wsie
                    locations['placeName'].append(location_name)
                elif ent.label_ == 'geogName':  # Rzeki, góry
                    locations['geogName'].append(location_name)

        return locations