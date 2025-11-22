from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.logic.conversation import ChatbotLogic
import asyncio

app = FastAPI(title="Pogodowy Stróż API")

# 1. CORS Configuration (Integracja z Lovable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji warto zmienić na konkretne domeny
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prosty magazyn sesji w pamięci (w produkcji użyj Redis/DB)
sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id

    # Pobierz lub stwórz instancję logiki dla sesji
    if session_id not in sessions:
        sessions[session_id] = ChatbotLogic(session_id)

    bot = sessions[session_id]

    # Przetwórz wiadomość
    response_text = await bot.handle_message(request.message)

    return ChatResponse(response=response_text, session_id=session_id)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Pogodowy Stróż Backend is running"}
