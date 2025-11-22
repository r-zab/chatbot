import os
from pathlib import Path

# Nazwa głównego katalogu projektu
PROJECT_NAME = "pogodowy-stroz"

# Struktura plików i ich zawartość (bazująca na dokumentacji)
project_structure = {
    f"{PROJECT_NAME}/requirements.txt": """fastapi
uvicorn
httpx
pydantic
spacy
transitions
pandas
jinja2
""",

    f"{PROJECT_NAME}/app/__init__.py": "",

    f"{PROJECT_NAME}/app/main.py": """# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.models import ChatRequest, ChatResponse
from app.services.state_manager import get_or_create_fsm
# from app.logic.conversation import ChatbotLogic # Typowanie

app = FastAPI(title="Pogodowy Stróż API")

# Serwowanie frontendu (SPA)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest):
    \"\"\"Główny endpoint obsługi czatu.\"\"\"
    # Pobranie lub stworzenie maszyny stanów dla danej sesji
    fsm = get_or_create_fsm(request.session_id)

    # Przekazanie wiadomości do logiki konwersacyjnej
    bot_response_text = await fsm.process_message(request.message)

    return ChatResponse(
        response=bot_response_text,
        session_id=request.session_id
    )

@app.get("/")
async def read_root():
    from fastapi.responses import FileResponse
    return FileResponse('static/index.html')
""",

    f"{PROJECT_NAME}/app/api/__init__.py": "",

    f"{PROJECT_NAME}/app/api/imgw_client.py": """import httpx
from fastapi import HTTPException
import asyncio

class ImgwApiClient:
    def __init__(self):
        self.base_url = "https://danepubliczne.imgw.pl/api/data"
        self.async_client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def get_synop_data(self, station_id: str):
        \"\"\"Pobiera dane synoptyczne dla konkretnej stacji.\"\"\"
        try:
            response = await self.async_client.get(f"/synop/id/{station_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Błąd API IMGW: {e.response.text}")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Błąd komunikacji z serwisem zewnętrznym IMGW.")

    async def get_hydro_data(self, station_id: str):
        \"\"\"Pobiera dane hydrologiczne dla konkretnej stacji.\"\"\"
        try:
            # Uwaga: weryfikacja endpointu hydro zgodnie z dokumentacją
            response = await self.async_client.get(f"/hydro/id/{station_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Błąd API Hydro IMGW: {e.response.text}")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Błąd komunikacji z serwisem Hydro IMGW.")

    async def get_meteo_warnings(self):
        \"\"\"Pobiera pełen plik ostrzeżeń meteorologicznych.\"\"\"
        try:
            response = await self.async_client.get("/warningsmeteo")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Błąd API Ostrzeżeń IMGW: {e.response.text}")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Błąd komunikacji z serwisem Ostrzeżeń IMGW.")
""",

    f"{PROJECT_NAME}/app/core/__init__.py": "",

    f"{PROJECT_NAME}/app/core/models.py": """from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
""",

    f"{PROJECT_NAME}/app/data/README.txt": "Tutaj trafią pliki JSON wygenerowane przez skrypty (terc_dict.json, simc_dict.json, itp.).",

    f"{PROJECT_NAME}/app/logic/__init__.py": "",

    f"{PROJECT_NAME}/app/logic/nlp.py": """import spacy

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
""",

    f"{PROJECT_NAME}/app/logic/conversation.py": """from transitions import Machine
from app.logic.nlp import recognize_intent, extract_entities
from app.services.data_service import DataService

class ChatbotLogic:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data_service = DataService()
        self.current_intent = None
        self.current_location_id = None
        self.response = "Cześć, w czym mogę pomóc?"
        self.processing_result = None
        self.processing_error = None

        states = ['initial', 'awaiting_location', 'awaiting_clarification', 'processing']

        self.machine = Machine(model=self, states=states, initial='initial')

        # Definicje przejść
        self.machine.add_transition(
            trigger='intent_recognized', source='initial', dest='processing',
            conditions='_has_valid_location', after='_trigger_data_processing'
        )
        self.machine.add_transition(
            trigger='intent_recognized', source='initial', dest='awaiting_location',
            conditions='_is_location_missing', after='_ask_for_location'
        )
        self.machine.add_transition(
            trigger='intent_recognized', source='initial', dest='awaiting_clarification',
            conditions='_is_location_invalid', after='_ask_for_correction'
        )
        self.machine.add_transition(
            trigger='other_question', source='initial', dest='initial',
            after='_handle_other_question'
        )
        self.machine.add_transition(
            trigger='location_provided', source=['awaiting_location', 'awaiting_clarification'], dest='processing',
            conditions='_has_valid_location', after='_trigger_data_processing'
        )
        self.machine.add_transition('data_processed', 'processing', 'initial', after='_format_response')
        self.machine.add_transition('error_occurred', 'processing', 'initial', after='_format_error')

    async def process_message(self, text: str) -> str:
        if self.state == 'initial':
            self.current_intent = recognize_intent(text)
            if not self.current_intent:
                self.trigger('other_question')
                return self.response

            entities = extract_entities(text)
            self.current_location_id = self.data_service.validate_and_get_id(entities, self.current_intent)
            self.trigger('intent_recognized')
            return self.response

        elif self.state in ['awaiting_location', 'awaiting_clarification']:
            entities = extract_entities(text)
            # Tu w pełnej wersji powinna być logika łącząca stare encje z nowymi
            self.current_location_id = self.data_service.validate_and_get_id(entities, self.current_intent)

            # Próba przejścia - maszyna sprawdzi warunki
            if self._has_valid_location():
                 self.trigger('location_provided')
            else:
                 # Jeśli nadal brak lokalizacji, można zostać w tym samym stanie lub poprosić o poprawkę
                 self._ask_for_correction()

            return self.response

        return self.response

    # Warunki
    def _has_valid_location(self):
        return self.current_location_id is not None

    def _is_location_missing(self):
        return self.current_location_id is None

    def _is_location_invalid(self):
        # Uproszczenie
        return False

    # Akcje
    def _ask_for_location(self):
        self.response = f"Rozumiem, że pytasz o {self.current_intent}. Podaj mi proszę lokalizację."

    def _ask_for_correction(self):
        self.response = "Niestety nie znalazłem takiej lokalizacji. Spróbuj podać inną nazwę."

    def _handle_other_question(self):
        self.response = "Przepraszam, potrafię tylko odpowiadać na pytania o pogodę, ostrzeżenia i stany wód."

    async def _trigger_data_processing(self):
        try:
            self.response = "Chwileczkę, sprawdzam dane w IMGW..."
            result = await self.data_service.fetch_data(self.current_intent, self.current_location_id)
            self.processing_result = result
            self.trigger('data_processed')
        except Exception as e:
            self.processing_error = str(e)
            self.trigger('error_occurred')

    def _format_response(self):
        self.response = self.processing_result
        self._reset_context()

    def _format_error(self):
        self.response = f"Wystąpił błąd: {self.processing_error}"
        self._reset_context()

    def _reset_context(self):
        self.current_intent = None
        self.current_location_id = None
""",

    f"{PROJECT_NAME}/app/services/__init__.py": "",

    f"{PROJECT_NAME}/app/services/data_service.py": """import json
import os
from app.api.imgw_client import ImgwApiClient

class DataService:
    def __init__(self):
        self.imgw_client = ImgwApiClient()
        # Ścieżki do plików danych
        base_path = "app/data"
        try:
            self.terc_dict = self._load_json(f"{base_path}/terc_dict.json")
            self.simc_dict = self._load_json(f"{base_path}/simc_dict.json")
            self.map_simc_to_synop = self._load_json(f"{base_path}/map_simc_to_imgw_synop.json")
        except FileNotFoundError:
            print("OSTRZEŻENIE: Brak plików słowników w app/data/. Uruchom skrypty przygotowawcze.")
            self.terc_dict = {}
            self.simc_dict = {}
            self.map_simc_to_synop = {}

    def _load_json(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _normalize(self, text: str) -> str:
        return text.lower().strip() # Tu należy dodać usuwanie diakrytyków

    def validate_and_get_id(self, entities: dict, intent: str) -> str | None:
        # Uproszczona logika walidacji
        if intent == 'ostrzeżenia':
            for place in entities.get('placeName', []):
                norm_place = self._normalize(place)
                if norm_place in self.terc_dict:
                    return self.terc_dict[norm_place]

        if intent == 'pogoda':
            for place in entities.get('placeName', []):
                norm_place = self._normalize(place)
                if norm_place in self.simc_dict:
                    simc_id = self.simc_dict[norm_place]
                    if simc_id in self.map_simc_to_synop:
                        return self.map_simc_to_synop[simc_id]
        return None

    async def fetch_data(self, intent: str, location_id: str) -> str:
        if intent == 'pogoda':
            data = await self.imgw_client.get_synop_data(location_id)
            return f"Pogoda dla stacji {data.get('stacja', 'Nieznana')}: {data.get('temperatura', '?')} C, ciśnienie: {data.get('cisnienie', '?')} hPa."

        if intent == 'ostrzeżenia':
            # Tu powinna być logika filtrowania pobranego pliku JSON po location_id (TERYT)
            _ = await self.imgw_client.get_meteo_warnings()
            return "Sprawdziłem ostrzeżenia (logika filtrowania do implementacji)."

        return "Nieobsługiwana intencja."
""",

    f"{PROJECT_NAME}/app/services/state_manager.py": """from app.logic.conversation import ChatbotLogic

# Magazyn sesji w pamięci
user_sessions: dict[str, ChatbotLogic] = {}

def get_or_create_fsm(session_id: str) -> ChatbotLogic:
    if session_id not in user_sessions:
        user_sessions[session_id] = ChatbotLogic(session_id)
    return user_sessions[session_id]
""",

    f"{PROJECT_NAME}/scripts/prepare_teryt.py": """# scripts/prepare_teryt.py
# Skrypt do przetwarzania plików TERYT (TERC.csv, SIMC.csv) na pliki JSON.
# Szczegóły implementacji w dokumentacji: Część 1.4
import pandas as pd
import json

def main():
    print("Tu zaimplementuj logikę parsowania TERC i SIMC...")
    # 1. Wczytaj CSV
    # 2. Znormalizuj nazwy
    # 3. Zapisz do app/data/terc_dict.json i simc_dict.json

if __name__ == "__main__":
    main()
""",

    f"{PROJECT_NAME}/scripts/create_station_map.py": """# scripts/create_station_map.py
# Skrypt do mapowania SIMC -> IMGW Station ID
# Szczegóły implementacji w dokumentacji: Część 1.4
import httpx
import json

def main():
    print("Tu zaimplementuj logikę mapowania stacji...")
    # 1. Pobierz listę stacji IMGW
    # 2. Wczytaj simc_dict.json
    # 3. Połącz po nazwach
    # 4. Zapisz app/data/map_simc_to_imgw_synop.json

if __name__ == "__main__":
    main()
""",

    f"{PROJECT_NAME}/static/index.html": """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pogodowy Stróż</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="chat-container">
        <div id="chat-window">
            <div class="message bot">Cześć, w czym mogę pomóc?</div>
        </div>
        <form id="chat-form">
            <input type="text" id="message-input" placeholder="Wpisz wiadomość..." autocomplete="off">
            <button type="submit">Wyślij</button>
        </form>
    </div>
    <script src="script.js"></script>
</body>
</html>
""",

    f"{PROJECT_NAME}/static/style.css": """body { font-family: sans-serif; background: #f0f2f5; display: flex; justify-content: center; height: 100vh; margin: 0; }
#chat-container { width: 100%; max-width: 600px; background: white; display: flex; flex-direction: column; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
#chat-window { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
.message { padding: 10px 15px; border-radius: 20px; max-width: 80%; word-wrap: break-word; }
.message.bot { background: #e4e6eb; color: black; align-self: flex-start; }
.message.user { background: #0084ff; color: white; align-self: flex-end; }
.message.bot-error { background: #ffcccc; color: darkred; align-self: flex-start; }
#chat-form { display: flex; border-top: 1px solid #ddd; padding: 10px; }
#message-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; }
button { margin-left: 10px; padding: 10px 20px; background: #0084ff; color: white; border: none; border-radius: 20px; cursor: pointer; }
""",

    f"{PROJECT_NAME}/static/script.js": """document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("message-input");
    const chatWindow = document.getElementById("chat-window");

    let sessionId = "session_" + Date.now();

    function renderMessage(message, senderClass) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${senderClass}`;
        messageDiv.textContent = message;
        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return messageDiv;
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        renderMessage(message, "user");
        input.value = "";

        const typingIndicator = renderMessage("...", "bot");

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: message, session_id: sessionId }),
            });

            chatWindow.removeChild(typingIndicator);

            if (!response.ok) throw new Error(`Błąd serwera: ${response.statusText}`);

            const data = await response.json();
            renderMessage(data.response, "bot");
            sessionId = data.session_id;

        } catch (error) {
            console.error("Błąd fetch:", error);
            if (typingIndicator.parentNode) chatWindow.removeChild(typingIndicator);
            renderMessage("Przepraszam, wystąpił błąd komunikacji.", "bot-error");
        }
    });
});
"""
}


def create_project():
    base_path = Path.cwd()
    print(f"Tworzenie struktury projektu w: {base_path / PROJECT_NAME}")

    for file_path, content in project_structure.items():
        path = base_path / file_path
        # Tworzenie folderów jeśli nie istnieją
        path.parent.mkdir(parents=True, exist_ok=True)

        # Zapisywanie pliku
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Utworzono: {file_path}")

    print("\n--- SUKCES ---")
    print(f"Projekt '{PROJECT_NAME}' został utworzony.")
    print("Następne kroki:")
    print(f"1. cd {PROJECT_NAME}")
    print("2. python -m venv venv")
    print("3. source venv/bin/activate (lub venv\\Scripts\\activate na Windows)")
    print("4. pip install -r requirements.txt")
    print("5. python -m spacy download pl_core_news_sm")
    print("6. Uzupełnij i uruchom skrypty w folderze scripts/ aby wygenerować dane JSON.")
    print("7. Uruchom serwer: uvicorn app.main:app --reload")


if __name__ == "__main__":
    create_project()