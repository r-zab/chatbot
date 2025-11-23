# app/logic/conversation.py
from transitions.extensions.asyncio import AsyncMachine
from app.services.data_service import DataService
from app.logic.nlp import NLPService


class ChatbotLogic:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data_service = DataService()
        self.nlp_service = NLPService()

        self.current_intent = None
        self.current_location_id = None
        self.response = ""

        states = ['initial', 'awaiting_location', 'processing']
        self.machine = AsyncMachine(model=self, states=states, initial='initial')

        # Przejścia
        self.machine.add_transition(trigger='process_input', source='initial', dest='processing',
                                    conditions='_has_valid_location_and_intent', after='_fetch_data_action')
        self.machine.add_transition(trigger='process_input', source='initial', dest='awaiting_location',
                                    conditions='_has_intent_but_no_location', after='_ask_for_location_text')

        # ZMIANA: Przejście dla nieznanej intencji
        self.machine.add_transition(trigger='process_input', source='initial', dest='initial',
                                    unless=['_has_valid_location_and_intent', '_has_intent_but_no_location'],
                                    after='_handle_unknown')

        self.machine.add_transition(trigger='process_input', source='awaiting_location', dest='processing',
                                    conditions='_check_location_in_input', after='_fetch_data_action')
        self.machine.add_transition(trigger='process_input', source='awaiting_location', dest='awaiting_location',
                                    unless='_check_location_in_input', after='_ask_for_location_again')
        self.machine.add_transition(trigger='reset', source='processing', dest='initial', after='_finalize_response')

    async def handle_message(self, text: str) -> str:
        if self.state == 'initial':
            self.current_intent = self.nlp_service.recognize_intent(text)
            # Jeśli intencja rozpoznana, szukamy lokalizacji
            if self.current_intent:
                entities = self.nlp_service.extract_entities(text)
                self.current_location_id = self.data_service.validate_and_get_id(entities, self.current_intent,
                                                                                 original_text=text)
            else:
                self.current_location_id = None

        await self.process_input(text)

        if self.state == 'processing':
            await self.reset()

        return self.response

    # Warunki
    def _has_valid_location_and_intent(self, text):
        return self.current_intent is not None and self.current_location_id is not None

    def _has_intent_but_no_location(self, text):
        return self.current_intent is not None and self.current_location_id is None

    def _check_location_in_input(self, text):
        entities = self.nlp_service.extract_entities(text)
        # Tu używamy zapamiętanej intencji
        found = self.data_service.validate_and_get_id(entities, self.current_intent, original_text=text)
        if found:
            self.current_location_id = found
            return True
        return False

    # Akcje
    async def _fetch_data_action(self, text):
        self.response = await self.data_service.fetch_data(self.current_intent, self.current_location_id)
        self.current_location_id = None
        self.current_intent = None

    def _ask_for_location_text(self, text):
        if self.current_intent == 'pogoda':
            self.response = "Gdzie mam sprawdzić pogodę? Podaj miasto."
        elif self.current_intent == 'ostrzeżenia':
            self.response = "Podaj powiat lub miasto dla ostrzeżeń."
        elif self.current_intent == 'hydro':
            self.response = "O jaką rzekę chodzi?"

    def _ask_for_location_again(self, text):
        self.response = "Nie zrozumiałem lokalizacji. Spróbuj podać pełną nazwę (np. Wrocław, Wisła)."

    def _handle_unknown(self, text):
        # ZMIANA: Reakcja na kanapkę
        self.response = "Nie rozumiem. Zapytaj o pogodę, stan rzek lub ostrzeżenia."

    def _finalize_response(self):
        pass