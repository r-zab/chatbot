# app/logic/nlp.py
import spacy


class NLPService:
    def __init__(self):
        # Słowa kluczowe do punktacji
        self.KEYWORDS = {
            'ostrzeżenia': [
                'ostrzeż', 'alert', 'zagroż', 'uwaga', 'burz', 'upał', 'wiatr', 'grad', 'mróz', 'wichur',
                'ulew', 'śnieg', 'gołoledź', 'meteo', 'worn'
            ],
            'hydro': [
                'wod', 'rzek', 'stan', 'poziom', 'wylew', 'zalew', 'hydro', 'cm', 'głębokość', 'wodowskaz',
                'fala', 'powódź', 'wisła', 'odra', 'warta'
            ],
            'pogoda': [
                'pogod', 'temperatu', 'ciepł', 'zimn', 'stopni', 'ciśnieni', 'synop', 'celcjusz', 'prognoz',
                'deszcz', 'słońc', 'chmur', 'jaka'
            ]
        }

        # Ładowanie modelu spaCy
        try:
            self.nlp = spacy.load("pl_core_news_sm")
        except OSError:
            print("OSTRZEŻENIE: Brak modelu spaCy. Uruchom: python -m spacy download pl_core_news_sm")
            self.nlp = None

    def recognize_intent(self, text: str) -> str:
        """Rozpoznaje intencję metodą punktacji."""
        text_lower = text.lower()
        scores = {'ostrzeżenia': 0, 'hydro': 0, 'pogoda': 0}

        for intent, stems in self.KEYWORDS.items():
            for stem in stems:
                if stem in text_lower:
                    scores[intent] += 1

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        # Debug
        print(f"NLP Score: {scores} -> {best_intent}")

        # Jeśli wynik jest > 0, zwracamy intencję.
        # Jeśli 0, ale tekst jest krótki (np. nazwa miasta), zakładamy pogodę.
        if max_score > 0:
            return best_intent

        # Fallback: Domyślnie pogoda
        return 'pogoda'

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        """Wyciąga encje geograficzne."""
        locations = {'placeName': [], 'geogName': []}
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ == 'placeName':
                    locations['placeName'].append(ent.text)
                elif ent.label_ == 'geogName':
                    locations['geogName'].append(ent.text)
        return locations