from app.logic.conversation import ChatbotLogic

# Magazyn sesji w pamięci
user_sessions: dict[str, ChatbotLogic] = {}

def get_or_create_fsm(session_id: str) -> ChatbotLogic:
    if session_id not in user_sessions:
        user_sessions[session_id] = ChatbotLogic(session_id)
    return user_sessions[session_id]
