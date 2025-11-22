from transitions.extensions.asyncio import AsyncMachine
from app.logic.nlp import NLPService
from app.services.data_service import DataService

class ChatbotLogic:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data_service = DataService()
        self.nlp_service = NLPService()

        self.current_intent = None
        self.current_location_id = None
        self.response = ""

        # Zmienne tymczasowe na wynik
        self.processing_result = None

        # Definicja stanów
        states = ['initial', 'awaiting_location', 'processing']

        self.machine = AsyncMachine(model=self, states=states, initial='initial')

        # --- Przejścia (Transitions) ---

        # 1. Ze stanu initial, wykryto intencję
        self.machine.add_transition(
            trigger='process_input',
            source='initial',
            dest='processing',
            conditions='_has_valid_location_and_intent', # Mamy intencję i lokalizację -> od razu procesujemy
            after='_fetch_data_action'
        )

        self.machine.add_transition(
            trigger='process_input',
            source='initial',
            dest='awaiting_location',
            conditions='_has_intent_but_no_location', # Mamy intencję (np. Pogoda), ale brak miasta
            after='_ask_for_location_text'
        )

        self.machine.add_transition(
            trigger='process_input',
            source='initial',
            dest='initial',
            unless=['_has_valid_location_and_intent', '_has_intent_but_no_location'], # Greeting / Inne
            after='_handle_greeting_or_unknown'
        )

        # 2. Ze stanu awaiting_location (dosłanie miasta)
        self.machine.add_transition(
            trigger='process_input',
            source='awaiting_location',
            dest='processing',
            conditions='_check_location_in_input', # Sprawdzamy czy teraz podano miasto
            after='_fetch_data_action'
        )

        self.machine.add_transition(
            trigger='process_input',
            source='awaiting_location',
            dest='awaiting_location',
            unless='_check_location_in_input', # Nadal nie podano miasta
            after='_ask_for_location_again'
        )

        # 3. Powrót po przetworzeniu
        self.machine.add_transition(
            trigger='reset',
            source='processing',
            dest='initial',
            after='_finalize_response'
        )

    async def handle_message(self, text: str) -> str:
        """Główna pętla obsługi wiadomości."""

        # Jeśli jesteśmy w initial, rozpoznajemy intencję od zera
        if self.state == 'initial':
            self.current_intent = self.nlp_service.recognize_intent(text)
            # Próbujemy wyciągnąć ID lokalizacji od razu
            self.current_location_id = self.data_service.validate_and_get_id(text, self.current_intent)

        await self.process_input(text) # Trigger maszyny stanów

        # Jeśli weszliśmy w stan 'processing', musimy wrócić do 'initial' żeby wypluć wynik
        if self.state == 'processing':
            await self.reset()

        return self.response

    # --- WARUNKI (CONDITIONS) ---

    def _has_valid_location_and_intent(self, text):
        return self.current_intent in ['pogoda', 'ostrzeżenia', 'hydro'] and self.current_location_id is not None

    def _has_intent_but_no_location(self, text):
        return self.current_intent in ['pogoda', 'ostrzeżenia', 'hydro'] and self.current_location_id is None

    def _check_location_in_input(self, text):
        # Jesteśmy w trybie oczekiwania, więc intencja jest już znana (self.current_intent)
        # Próbujemy znaleźć lokalizację w NOWYM tekście
        found_id = self.data_service.validate_and_get_id(text, self.current_intent)
        if found_id:
            self.current_location_id = found_id
            return True
        return False

    # --- AKCJE (AFTER) ---

    async def _fetch_data_action(self, text):
        # Pobieramy dane z DataService
        self.response = await self.data_service.fetch_data(self.current_intent, self.current_location_id)
        # Czyścimy kontekst (opcjonalnie, zależy czy chcemy pamiętać)
        self.current_location_id = None
        self.current_intent = None

    def _ask_for_location_text(self, text):
        if self.current_intent == 'pogoda':
            self.response = "Gdzie mam sprawdzić pogodę? Podaj miasto."
        elif self.current_intent == 'ostrzeżenia':
            self.response = "Dla jakiego powiatu (lub miasta) chcesz sprawdzić ostrzeżenia?"
        elif self.current_intent == 'hydro':
            self.response = "O jaką rzekę lub stację hydrologiczną chodzi?"

    def _ask_for_location_again(self, text):
        self.response = "Nadal nie rozumiem lokalizacji. Spróbuj podać pełną nazwę (np. Wrocław, Wisła)."

    def _handle_greeting_or_unknown(self, text):
        if self.current_intent == 'greeting':
            self.response = "Cześć! 👋 Sprawdzam pogodę, rzeki i ostrzeżenia. Co Cię interesuje?"
        else:
            self.response = "Nie jestem pewien. Zapytaj o pogodę, ostrzeżenia lub stan rzek."

    def _finalize_response(self):
        # Tu nic nie musimy robić, response jest już ustawiony w _fetch_data_action
        pass
