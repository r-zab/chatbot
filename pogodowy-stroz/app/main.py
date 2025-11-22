# app/main.py
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
    """Główny endpoint obsługi czatu."""
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
