# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.logic.conversation import ChatbotLogic
import os

app = FastAPI(title="Pogodowy Stróż API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfiguracja LLM
USE_LLM = os.getenv("USE_LLM", "true").lower() == "true"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama, openai, huggingface

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

    if session_id not in sessions:
        sessions[session_id] = ChatbotLogic(
            session_id,
            use_llm=USE_LLM,
            llm_provider=LLM_PROVIDER
        )

    bot = sessions[session_id]
    response_text = await bot.handle_message(request.message)

    return ChatResponse(response=response_text, session_id=session_id)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Pogodowy Stróż Backend is running",
        "llm_enabled": USE_LLM,
        "llm_provider": LLM_PROVIDER
    }

@app.get("/health")
async def health():
    """Endpoint do sprawdzenia stanu serwisu."""
    return {"status": "healthy", "llm": USE_LLM}