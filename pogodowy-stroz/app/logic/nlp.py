import spacy

class NLPService:
    def __init__(self):
        try:
            self.nlp = spacy.load("pl_core_news_sm")
        except OSError:
            print("Warning: Model spaCy 'pl_core_news_sm' not found. NLP features might be limited.")
            self.nlp = None

    def recognize_intent(self, text: str) -> str:
        text = text.lower()
        scores = {
            'pogoda': 0,
            'ostrzeżenia': 0,
            'hydro': 0
        }

        # Scenariusz 1: Pogoda
        keywords_weather = ['pogoda', 'temperatura', 'słońce', 'wieje', 'zimno', 'ciepło', 'deszcz', 'śnieg', 'prognoza', 'stopni']
        for w in keywords_weather:
            if w in text: scores['pogoda'] += 1

        # Scenariusz 2: Ostrzeżenia
        keywords_alerts = ['alert', 'ostrzeżenie', 'burza', 'grad', 'wiatr', 'meteo', 'zagrożenie', 'uwaga']
        for w in keywords_alerts:
            if w in text: scores['ostrzeżenia'] += 1

        # Scenariusz 3: Hydro
        keywords_hydro = ['rzeka', 'woda', 'stan', 'wylewa', 'powódź', 'wisła', 'odra', 'warta', 'poziom', 'wodowskaz']
        for w in keywords_hydro:
            if w in text: scores['hydro'] += 1

        # Wybór najlepszej intencji
        best_intent = max(scores, key=scores.get)

        if scores[best_intent] > 0:
            return best_intent

        return 'greeting' # Scenariusz 4: Greeting/Inne

    def extract_entities(self, text: str) -> dict:
        if not self.nlp:
            return {'placeName': []}

        doc = self.nlp(text)
        entities = {'placeName': []}

        for ent in doc.ents:
            # spaCy dla polskiego różnie rozpoznaje lokalizacje (placeName, geogName, location itp.)
            if ent.label_ in ['placeName', 'geogName', 'LOC', 'GPE']:
                entities['placeName'].append(ent.text)

        return entities
