from transitions.extensions.asyncio import AsyncMachine
from app.logic.nlp import recognize_intent, extract_entities
from app.services.data_service import DataService


class ChatbotLogic:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data_service = DataService()
        self.current_intent = None
        self.current_location_id = None
        self.response = "Cześć! Jestem Pogodowym Stróżem. Zapytaj mnie o pogodę (np. w Poznaniu) lub ostrzeżenia."
        self.processing_result = None
        self.processing_error = None

        states = ['initial', 'awaiting_location', 'awaiting_clarification', 'processing']
        self.machine = AsyncMachine(model=self, states=states, initial='initial')

        # Konfiguracja przejść (bez zmian logicznych, tylko kosmetyka)
        self.machine.add_transition(trigger='intent_recognized', source='initial', dest='processing',
                                    conditions='_has_valid_location', after='_trigger_data_processing')
        self.machine.add_transition(trigger='intent_recognized', source='initial', dest='awaiting_location',
                                    conditions='_is_location_missing', after='_ask_for_location')
        self.machine.add_transition(trigger='intent_recognized', source='initial', dest='awaiting_clarification',
                                    conditions='_is_location_invalid', after='_ask_for_correction')
        self.machine.add_transition(trigger='other_question', source='initial', dest='initial',
                                    after='_handle_other_question')

        # Obsługa dosłania lokalizacji w kolejnej wiadomości
        self.machine.add_transition(trigger='location_provided', source=['awaiting_location', 'awaiting_clarification'],
                                    dest='processing', conditions='_has_valid_location',
                                    after='_trigger_data_processing')
        self.machine.add_transition(trigger='location_provided', source=['awaiting_location', 'awaiting_clarification'],
                                    dest='awaiting_clarification', conditions='_is_location_missing',
                                    after='_ask_for_correction')

        self.machine.add_transition('data_processed', 'processing', 'initial', after='_format_response')
        self.machine.add_transition('error_occurred', 'processing', 'initial', after='_format_error')

    async def process_message(self, text: str) -> str:
        # Logika stanu początkowego
        if self.state == 'initial':
            self.current_intent = recognize_intent(text)
            if not self.current_intent:
                await self.trigger('other_question')
                return self.response

            entities = extract_entities(text)
            # PRZEKAZUJEMY 'text' DO FALLBACKU
            self.current_location_id = self.data_service.validate_and_get_id(entities, self.current_intent,
                                                                             original_text=text)

            await self.trigger('intent_recognized')
            return self.response

        # Logika gdy czekamy na lokalizację (np. użytkownik napisał wcześniej samą "pogoda")
        elif self.state in ['awaiting_location', 'awaiting_clarification']:
            entities = extract_entities(text)
            # Tutaj też przekazujemy 'text', bo użytkownik mógł wpisać po prostu "Poznań"
            self.current_location_id = self.data_service.validate_and_get_id(entities, self.current_intent,
                                                                             original_text=text)

            await self.trigger('location_provided')  # FSM sprawdzi warunki czy ID zostało znalezione
            return self.response

        return self.response

    # --- Warunki ---
    def _has_valid_location(self):
        return self.current_location_id is not None

    def _is_location_missing(self):
        return self.current_location_id is None

    def _is_location_invalid(self):
        return False  # Uproszczenie

    # --- ZMIENIONE TEKSTY ODPOWIEDZI ---
    def _ask_for_location(self):
        # Zamiast "Rozumiem...", proste pytanie
        if self.current_intent == 'pogoda':
            self.response = "Gdzie mam sprawdzić pogodę? Podaj nazwę miejscowości."
        elif self.current_intent == 'ostrzeżenia':
            self.response = "Dla jakiego powiatu chcesz sprawdzić ostrzeżenia?"
        else:
            self.response = "Podaj proszę lokalizację."

    def _ask_for_correction(self):
        self.response = "Nie znalazłem takiej stacji pomiarowej. Sprawdź literówki lub podaj większe miasto w pobliżu."

    def _handle_other_question(self):
        self.response = "Na razie znam się tylko na pogodzie i ostrzeżeniach. Zapytaj np. 'Jaka pogoda w Warszawie?'"

    def _format_response(self):
        self.response = self.processing_result
        self._reset_context()

    def _format_error(self):
        self.response = f"Ups, coś poszło nie tak przy pobieraniu danych: {self.processing_error}"
        self._reset_context()

    def _reset_context(self):
        self.current_intent = None
        self.current_location_id = None

    async def _trigger_data_processing(self):
        try:
            self.response = "Sprawdzam..."  # Krótki komunikat oczekiwania
            result = await self.data_service.fetch_data(self.current_intent, self.current_location_id)
            self.processing_result = result
            await self.trigger('data_processed')
        except Exception as e:
            self.processing_error = str(e)
            await self.trigger('error_occurred')