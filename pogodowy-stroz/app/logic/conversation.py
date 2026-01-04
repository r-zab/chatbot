# app/logic/conversation.py
from transitions.extensions.asyncio import AsyncMachine
from app.services.data_service import DataService
from app.logic.nlp import NLPService


class ChatbotLogic:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data_service = DataService()
        self.nlp_service = NLPService()

        # Stan konwersacji
        self.current_intent = None
        self.current_location_id = None
        self.response = ""

        # Pamięć kontekstu
        self.last_intent = None
        self.last_location_name = None

        # Definicja stanów
        states = ['initial', 'awaiting_location', 'processing']
        self.machine = AsyncMachine(model=self, states=states, initial='initial')

        # ==================== PRZEJŚCIA Z 'initial' ====================
        self.machine.add_transition(
            trigger='process_input',
            source='initial',
            dest='processing',
            conditions='_has_valid_location_and_intent',
            after='_fetch_data_action'
        )
        self.machine.add_transition(
            trigger='process_input',
            source='initial',
            dest='awaiting_location',
            conditions='_has_intent_but_no_location',
            after='_ask_for_location_text'
        )
        self.machine.add_transition(
            trigger='process_input',
            source='initial',
            dest='initial',
            unless=['_has_valid_location_and_intent', '_has_intent_but_no_location'],
            after='_handle_unknown'
        )

        # ==================== PRZEJŚCIA Z 'awaiting_location' ====================
        self.machine.add_transition(
            trigger='process_input',
            source='awaiting_location',
            dest='processing',
            conditions='_detected_new_intent_with_location',
            before='_prepare_new_query',
            after='_fetch_data_action'
        )
        self.machine.add_transition(
            trigger='process_input',
            source='awaiting_location',
            dest='awaiting_location',
            conditions='_detected_new_intent_without_location',
            before='_prepare_new_query',
            after='_ask_for_location_text'
        )
        self.machine.add_transition(
            trigger='process_input',
            source='awaiting_location',
            dest='processing',
            conditions='_check_location_in_input',
            after='_fetch_data_action'
        )
        self.machine.add_transition(
            trigger='process_input',
            source='awaiting_location',
            dest='awaiting_location',
            unless=['_detected_new_intent_with_location',
                    '_detected_new_intent_without_location',
                    '_check_location_in_input'],
            after='_ask_for_location_again'
        )

        # ==================== PRZEJŚCIE Z 'processing' ====================
        self.machine.add_transition(
            trigger='reset',
            source='processing',
            dest='initial',
            after='_finalize_response'
        )

    async def handle_message(self, text: str) -> str:
        """Główna funkcja przetwarzająca wiadomość użytkownika."""
        print(f"\n{'=' * 70}")
        print(f"📩 WIADOMOŚĆ: '{text}'")
        print(f"🔄 Stan: {self.state}, intent={self.current_intent}")

        # 🔥 NOWE: Obsługa small talk PRZED wszystkim innym
        is_small_talk, talk_type = self.nlp_service.is_small_talk(text)
        if is_small_talk:
            return self._handle_small_talk(talk_type)

        # Rozpoznaj intencję
        detected_intent = self.nlp_service.recognize_intent(text)
        print(f"🎯 Wykryta intencja: {detected_intent}")

        # ==================== STAN 'initial' ====================
        if self.state == 'initial':
            # Użyj kontekstu jeśli brak intencji
            if not detected_intent and self.last_intent:
                print(f"🔄 Użycie last_intent: {self.last_intent}")
                detected_intent = self.last_intent

            self.current_intent = detected_intent

            if self.current_intent:
                entities = self.nlp_service.extract_entities(text)
                self.current_location_id = self.data_service.validate_and_get_id(
                    entities,
                    self.current_intent,
                    original_text=text
                )
                self.last_intent = self.current_intent
                print(f"✅ Rozpoznano: intent={self.current_intent}, location={self.current_location_id}")
            else:
                self.current_location_id = None

        # ==================== STAN 'awaiting_location' ====================
        elif self.state == 'awaiting_location':
            if detected_intent:
                # Nowe zapytanie - przerwij czekanie
                print(f"🆕 NOWE ZAPYTANIE wykryte!")
                self._temp_detected_intent = detected_intent
                entities = self.nlp_service.extract_entities(text)
                self._temp_location_id = self.data_service.validate_and_get_id(
                    entities,
                    detected_intent,
                    original_text=text
                )
            else:
                # Odpowiedź na pytanie o lokalizację
                print(f"📝 Odpowiedź na pytanie o lokalizację")

        # Uruchom maszynę stanów
        await self.process_input(text)

        if self.state == 'processing':
            await self.reset()

        print(f"📤 ODPOWIEDŹ: {self.response}")
        print(f"{'=' * 70}\n")

        return self.response

    def _handle_small_talk(self, talk_type: str) -> str:
        """🔥 NOWE: Obsługa small talk."""
        print(f"💬 Small talk: {talk_type}")

        # Resetuj stan czekania (jeśli był)
        if self.state == 'awaiting_location':
            self.state = 'initial'
            self.current_intent = None

        if talk_type == 'greeting':
            return "Cześć! 👋 W czym mogę pomóc? Mogę sprawdzić pogodę, ostrzeżenia lub stan rzek."

        elif talk_type == 'goodbye':
            # Resetuj kontekst przy pożegnaniu
            self.last_intent = None
            return "Do usług! 👋 Wróć gdy będziesz potrzebować informacji o pogodzie."

        elif talk_type == 'confused':
            return ("Mogę Ci pomóc z:\n"
                    "🌤️ **Pogodą** - np. 'Pogoda w Warszawie'\n"
                    "⚠️ **Ostrzeżeniami** - np. 'Ostrzeżenia Kraków'\n"
                    "💧 **Stanami rzek** - np. 'Stan wody w Wiśle'")

        return "Nie rozumiem. Zapytaj o pogodę, ostrzeżenia lub stan rzek."

    # ==================== WARUNKI ====================

    def _has_valid_location_and_intent(self, text):
        result = self.current_intent is not None and self.current_location_id is not None
        print(f"   🔹 _has_valid_location_and_intent: {result}")
        return result

    def _has_intent_but_no_location(self, text):
        result = self.current_intent is not None and self.current_location_id is None
        print(f"   🔹 _has_intent_but_no_location: {result}")
        return result

    def _detected_new_intent_with_location(self, text):
        if not hasattr(self, '_temp_detected_intent'):
            return False
        result = (self._temp_detected_intent is not None and
                  self._temp_location_id is not None)
        print(f"   🔹 _detected_new_intent_with_location: {result}")
        return result

    def _detected_new_intent_without_location(self, text):
        if not hasattr(self, '_temp_detected_intent'):
            return False
        result = (self._temp_detected_intent is not None and
                  self._temp_location_id is None)
        print(f"   🔹 _detected_new_intent_without_location: {result}")
        return result

    def _check_location_in_input(self, text):
        if hasattr(self, '_temp_detected_intent') and self._temp_detected_intent:
            return False

        print(f"   🔍 Szukam lokalizacji dla: {self.current_intent}")
        entities = self.nlp_service.extract_entities(text)
        found = self.data_service.validate_and_get_id(
            entities,
            self.current_intent,
            original_text=text
        )

        if found:
            self.current_location_id = found
            print(f"   ✅ Znaleziono: {found}")
            return True
        return False

    # ==================== AKCJE ====================

    def _prepare_new_query(self, text):
        print(f"   🔄 Przygotowanie nowego zapytania")
        self.current_intent = self._temp_detected_intent
        self.current_location_id = self._temp_location_id
        self.last_intent = self.current_intent
        self._temp_detected_intent = None
        self._temp_location_id = None

    async def _fetch_data_action(self, text):
        print(f"   📡 Pobieranie danych...")
        self.response = await self.data_service.fetch_data(
            self.current_intent,
            self.current_location_id
        )
        if self.current_location_id and isinstance(self.current_location_id, dict):
            self.last_location_name = self.current_location_id.get('name')
        self.current_location_id = None
        self.current_intent = None

    def _ask_for_location_text(self, text):
        if self.current_intent == 'pogoda':
            self.response = "Gdzie mam sprawdzić pogodę? Podaj miasto."
        elif self.current_intent == 'ostrzeżenia':
            self.response = "Dla jakiego powiatu/miasta sprawdzić ostrzeżenia?"
        elif self.current_intent == 'hydro':
            self.response = "Dla jakiej rzeki sprawdzić stan wody? (np. Wisła, Odra, San)"
        else:
            self.response = "Podaj lokalizację."

    def _ask_for_location_again(self, text):
        if self.current_intent == 'hydro':
            self.response = "Nie rozpoznałem nazwy rzeki. Podaj np. Wisła, Odra, Warta, San."
        else:
            self.response = "Nie rozpoznałem lokalizacji. Podaj pełną nazwę miasta."

    def _handle_unknown(self, text):
        self.response = "Nie rozumiem. Zapytaj o pogodę, stan rzek lub ostrzeżenia."

    def _finalize_response(self):
        if hasattr(self, '_temp_detected_intent'):
            self._temp_detected_intent = None
            self._temp_location_id = None