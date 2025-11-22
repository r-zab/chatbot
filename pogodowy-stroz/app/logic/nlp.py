import spacy

INTENT_KEYWORDS = {
    'pogoda': ['pogoda', 'temperatura', 'jak ciepło', 'stopni', 'ciśnienie', 'wiatr', 'synoptyczne'],
    'ostrzeżenia': ['ostrzeżenie', 'alert', 'zagrożenie', 'uwaga', 'burza', 'upał', 'niebezpiecznie'],
    'hydro': ['woda', 'rzeka', 'stan wody', 'poziom rzeki', 'hydrologiczne', 'wyleje'],
}

try:
    nlp = spacy.load("pl_core_news_sm")
except OSError:
    print("BŁĄD: Model spaCy 'pl_core_news_sm' nie znaleziony. Uruchom: python -m spacy download pl_core_news_sm")
    nlp = None

def recognize_intent(text: str) -> str | None:
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return intent
    return None

def extract_entities(text: str) -> dict[str, list[str]]:
    if not nlp:
        return {'placeName': [], 'geogName': []}

    doc = nlp(text)
    locations = {'placeName': [], 'geogName': []}

    for ent in doc.ents:
        if ent.label_ == 'placeName':
            locations['placeName'].append(ent.text)
        elif ent.label_ == 'geogName':
            locations['geogName'].append(ent.text)

    return locations
