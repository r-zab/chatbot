# app/logic/conversation.py
from transitions.extensions.asyncio import AsyncMachine
from app.services.data_service import DataService
from app.logic.nlp import NLPService
import random


class ChatbotLogic:
    def __init__(self, session_id):
        self.session_id = session_id
        self.data_service = DataService()
        self.nlp_service = NLPService()

        self.current_intent = None
        self.current_location_id = None
        self.response = ""
        self.last_intent = None
        self.last_location_name = None

        states = ['initial', 'awaiting_location', 'processing']
        self.machine = AsyncMachine(model=self, states=states, initial='initial')

        # PRZEJŚCIA Z 'initial'
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

        # PRZEJŚCIA Z 'awaiting_location'
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

        # PRZEJŚCIE Z 'processing'
        self.machine.add_transition(
            trigger='reset',
            source='processing',
            dest='initial',
            after='_finalize_response'
        )

    async def handle_message(self, text: str) -> str:
        """Główna funkcja przetwarzająca wiadomość."""
        print(f"\n{'=' * 60}")
        print(f"📩 WIADOMOŚĆ: '{text}'")
        print(f"🔄 Stan: {self.state}, intent={self.current_intent}")

        # 🔥 1. Sprawdź small talk
        is_small_talk, talk_type = self.nlp_service.is_small_talk(text)
        if is_small_talk:
            return self._handle_small_talk(talk_type)

        # 🔥 2. Sprawdź czy to prośba o coś czego nie umiemy
        if self.nlp_service.is_cant_do_request(text):
            return self._handle_cant_do()

        # 3. Rozpoznaj intencję
        detected_intent = self.nlp_service.recognize_intent(text)
        print(f"🎯 Wykryta intencja: {detected_intent}")

        # STAN 'initial'
        if self.state == 'initial':
            if not detected_intent and self.last_intent:
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
            else:
                self.current_location_id = None

        # STAN 'awaiting_location'
        elif self.state == 'awaiting_location':
            if detected_intent:
                self._temp_detected_intent = detected_intent
                entities = self.nlp_service.extract_entities(text)
                self._temp_location_id = self.data_service.validate_and_get_id(
                    entities,
                    detected_intent,
                    original_text=text
                )

        await self.process_input(text)

        if self.state == 'processing':
            await self.reset()

        print(f"📤 ODPOWIEDŹ: {self.response}")
        return self.response

    def _handle_small_talk(self, talk_type: str) -> str:
        """Obsługa small talk."""
        print(f"💬 Small talk: {talk_type}")

        # Reset stanu jeśli był w awaiting
        if self.state == 'awaiting_location':
            self.state = 'initial'
            self.current_intent = None

        if talk_type == 'greeting':
            responses = [
                "Cześć! 👋 W czym mogę pomóc?",
                "Hej! 👋 Zapytaj mnie o pogodę, ostrzeżenia lub stan rzek.",
                "Siema! 🌤️ Czego szukasz? Pogoda, ostrzeżenia, czy stany wód?",
                "Witaj! ☀️ Jestem Pogodowym Stróżem. Jak mogę pomóc?"
            ]
            return random.choice(responses)

        elif talk_type == 'goodbye' or talk_type == 'thanks':
            responses = [
                "Do usług! 👋 Wróć gdy będziesz potrzebować info o pogodzie.",
                "Nie ma sprawy! 😊 Trzymaj się!",
                "Spoko! 👍 Zapraszam ponownie.",
                "Na zdrowie! ☀️ Do następnego razu!"
            ]
            self.last_intent = None  # Reset kontekstu
            return random.choice(responses)

        elif talk_type == 'help':
            return (
                "🤖 Jestem Pogodowym Stróżem. Umiem:\n\n"
                "🌤️ Pogoda → np. \"Pogoda w Warszawie\"\n"
                "⚠️ Ostrzeżenia → np. \"Ostrzeżenia dla Krakowa\"\n"
                "💧 Stany wód → np. \"Stan wody w Wiśle\"\n\n"
                "Możesz też pytać kontekstowo:\n"
                "\"A w Krakowie?\" - użyję poprzedniego tematu."
            )

        elif talk_type == 'nonsense':
            responses = [
                "🤔 Hmm, nie rozumiem. Zapytaj o pogodę, ostrzeżenia lub stan rzek.",
                "😅 Chyba się nie rozumiemy. Spróbuj: \"Pogoda Warszawa\"",
                "🧐 Nie łapię. Jestem botem pogodowym - zapytaj o pogodę!"
            ]
            return random.choice(responses)

        return "Nie rozumiem. Zapytaj o pogodę, stan rzek lub ostrzeżenia."

    def _handle_cant_do(self) -> str:
        """🔥 NOWE: Obsługa próśb których bot nie umie zrealizować."""
        responses = [
            "😅 Niestety, tego nie umiem. Jestem tylko botem pogodowym!\n\n"
            "Mogę sprawdzić:\n"
            "🌤️ Pogodę\n"
            "⚠️ Ostrzeżenia\n"
            "💧 Stany wód",

            "🤖 Hej, jestem Pogodowym Stróżem, nie czarodziejem! 😄\n"
            "Zapytaj mnie o pogodę, ostrzeżenia lub poziom wody w rzekach.",

            "😊 Chciałbym pomóc, ale umiem tylko sprawy pogodowe!\n"
            "Spróbuj: \"Pogoda Warszawa\" lub \"Stan wody Wisła\"",
        ]
        return random.choice(responses)

    # ==================== WARUNKI ====================

    def _has_valid_location_and_intent(self, text):
        return self.current_intent is not None and self.current_location_id is not None

    def _has_intent_but_no_location(self, text):
        return self.current_intent is not None and self.current_location_id is None

    def _detected_new_intent_with_location(self, text):
        if not hasattr(self, '_temp_detected_intent'):
            return False
        return self._temp_detected_intent is not None and self._temp_location_id is not None

    def _detected_new_intent_without_location(self, text):
        if not hasattr(self, '_temp_detected_intent'):
            return False
        return self._temp_detected_intent is not None and self._temp_location_id is None

    def _check_location_in_input(self, text):
        if hasattr(self, '_temp_detected_intent') and self._temp_detected_intent:
            return False

        entities = self.nlp_service.extract_entities(text)
        found = self.data_service.validate_and_get_id(
            entities,
            self.current_intent,
            original_text=text
        )

        if found:
            self.current_location_id = found
            return True
        return False

    # ==================== AKCJE ====================

    def _prepare_new_query(self, text):
        self.current_intent = self._temp_detected_intent
        self.current_location_id = self._temp_location_id
        self.last_intent = self.current_intent
        self._temp_detected_intent = None
        self._temp_location_id = None

    async def _fetch_data_action(self, text):
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
            self.response = "🌍 Dla jakiego miasta sprawdzić pogodę?"
        elif self.current_intent == 'ostrzeżenia':
            self.response = "🗺️ Dla jakiego powiatu/miasta sprawdzić ostrzeżenia?"
        elif self.current_intent == 'hydro':
            self.response = "🏞️ Dla jakiej rzeki sprawdzić stan wody?\n(np. Wisła, Odra, Warta, San)"
        else:
            self.response = "📍 Podaj lokalizację."

    def _ask_for_location_again(self, text):
        if self.current_intent == 'hydro':
            self.response = "🤔 Nie rozpoznałem rzeki. Podaj np. Wisła, Odra, Warta, Bug, Narew."
        else:
            self.response = "🤔 Nie rozpoznałem lokalizacji. Podaj pełną nazwę miasta."

    def _handle_unknown(self, text):
        responses = [
            "🤔 Nie rozumiem. Zapytaj o pogodę, stan rzek lub ostrzeżenia.",
            "😕 Nie łapię. Spróbuj: \"Pogoda Warszawa\" lub \"Stan wody Wisła\"",
            "🧐 Hmm? Jestem botem pogodowym. Zapytaj o pogodę!"
        ]
        self.response = random.choice(responses)

    def _finalize_response(self):
        if hasattr(self, '_temp_detected_intent'):
            self._temp_detected_intent = None
            self._temp_location_id = None