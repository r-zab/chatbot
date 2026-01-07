# app/logic/conversation.py

from transitions.extensions.asyncio import AsyncMachine
from app.services.data_service import DataService
from app.logic.nlp import NLPService
import random
import difflib


class ChatbotLogic:
    def __init__(self, session_id, use_llm: bool = True, llm_provider: str = "ollama"):
        self.session_id = session_id
        self.data_service = DataService()
        self.nlp_service = NLPService(use_llm=use_llm, llm_provider=llm_provider)

        self.current_intent = None
        self.current_location_id = None
        self.response = ""
        self.last_intent = None
        self.last_location_name = None
        self.last_water_body = None
        self.llm_checked = False

        # 🔥 Zapamiętywanie ostatnich ostrzeżeń
        self.last_warnings_data: list = []
        self.last_warnings_location: str = ""
        self.last_warnings_type: str = ""

        self._temp_detected_intent = None
        self._temp_location_id = None

        states = ["initial", "awaiting_location", "processing"]
        self.machine = AsyncMachine(model=self, states=states, initial="initial")

        # PRZEJŚCIA Z 'initial'
        self.machine.add_transition(
            trigger="process_input",
            source="initial",
            dest="processing",
            conditions="_has_valid_location_and_intent",
            after="_fetch_data_action",
        )
        self.machine.add_transition(
            trigger="process_input",
            source="initial",
            dest="awaiting_location",
            conditions="_has_intent_but_no_location",
            after="_ask_for_location_text",
        )
        self.machine.add_transition(
            trigger="process_input",
            source="initial",
            dest="initial",
            unless=["_has_valid_location_and_intent", "_has_intent_but_no_location"],
            after="_handle_unknown",
        )

        # PRZEJŚCIA Z 'awaiting_location'
        self.machine.add_transition(
            trigger="process_input",
            source="awaiting_location",
            dest="processing",
            conditions="_detected_new_intent_with_location",
            before="_prepare_new_query",
            after="_fetch_data_action",
        )
        self.machine.add_transition(
            trigger="process_input",
            source="awaiting_location",
            dest="awaiting_location",
            conditions="_detected_new_intent_without_location",
            before="_prepare_new_query",
            after="_ask_for_location_text",
        )
        self.machine.add_transition(
            trigger="process_input",
            source="awaiting_location",
            dest="processing",
            conditions="_check_location_in_input",
            after="_fetch_data_action",
        )
        self.machine.add_transition(
            trigger="process_input",
            source="awaiting_location",
            dest="awaiting_location",
            unless=[
                "_detected_new_intent_with_location",
                "_detected_new_intent_without_location",
                "_check_location_in_input",
            ],
            after="_ask_for_location_again",
        )

        # PRZEJŚCIE Z 'processing'
        self.machine.add_transition(
            trigger="reset",
            source="processing",
            dest="initial",
            after="_finalize_response",
        )

    def _force_reset_to_initial(self):
        """Wymusza reset stanu do initial."""
        self.state = "initial"
        self.current_intent = None
        self.current_location_id = None
        self._temp_detected_intent = None
        self._temp_location_id = None

    async def handle_message(self, text: str) -> str:
        """Główna funkcja przetwarzająca wiadomość."""
        print(f"\n{'=' * 60}")
        print(f"📩 WIADOMOŚĆ: '{text}'")
        print(f"🔄 Stan: {self.state}, intent={self.current_intent}")

        # 🔥 Sprawdź dostępność LLM (tylko raz na sesję)
        if not self.llm_checked and self.nlp_service.use_llm:
            await self.nlp_service.check_llm_availability()
            self.llm_checked = True

        # 1. Sprawdź small talk
        is_small_talk, talk_type = self.nlp_service.is_small_talk(text)
        if is_small_talk:
            return self._handle_small_talk(talk_type)

        # 2. Sprawdź czy to prośba o coś czego nie umiemy
        if self.nlp_service.is_cant_do_request(text):
            return self._handle_cant_do()

        # =====================================================
        # 🔥 3. NOWE: Sprawdź czy użytkownik pyta o wiele rzeczy
        # =====================================================
        if self.nlp_service.has_multiple_intents(text):
            return (
                "🤔 Mogę sprawdzić tylko jedną rzecz naraz.\n\n"
                "Zapytaj najpierw o jedno, np.:\n"
                "• \"Pogoda Warszawa\"\n"
                "• \"Ostrzeżenia mazowieckie\"\n"
                "• \"Stan wody Wisła\""
            )

        # 3. Rozpoznaj intencję
        detected_intent, metadata = await self.nlp_service.recognize_intent_async(text)
        print(f"🎯 Wykryta intencja: {detected_intent} (source: {metadata.get('source', '?')})")

        # 4. Obsłuż specjalne intencje
        if detected_intent == "forecast_unavailable":
            self._force_reset_to_initial()
            return self._handle_forecast_unavailable()

        if detected_intent == "hydro_lista":
            return await self._handle_station_list(text)

        # 5. Obsłuż pytanie o powiaty
        if detected_intent == "warnings_powiaty":
            return self._handle_county_list_request()

        # LLM entities.location
        llm_location = None
        entities_meta = metadata.get("entities") or {}
        if isinstance(entities_meta, dict):
            llm_location = entities_meta.get("location")

        # STAN 'initial'
        if self.state == "initial":
            if not detected_intent and self.last_intent:
                detected_intent = self.last_intent

            self.current_intent = detected_intent

            if self.current_intent:
                if llm_location:
                    print(f"🧭 LLM entities.location: {llm_location}")
                    self.current_location_id = self.data_service.validate_and_get_id(
                        {"placeName": [llm_location], "geogName": [llm_location]},
                        self.current_intent,
                        original_text=text,
                    )

                if not self.current_location_id:
                    extracted = self.nlp_service.extract_entities(text)
                    self.current_location_id = self.data_service.validate_and_get_id(
                        extracted,
                        self.current_intent,
                        original_text=text,
                    )

                self.last_intent = self.current_intent
            else:
                self.current_location_id = None

            await self.process_input(text)

            if self.state == "processing":
                await self.reset()

            print(f"📤 ODPOWIEDŹ: {self.response}")
            return self.response

        # STAN 'awaiting_location'
        elif self.state == "awaiting_location":
            # 🔥 NOWE: Sprawdź czy to wygląda na nieistniejącą lokalizację (bait)
            if self._looks_like_fake_location(text):
                self.response = self._ask_for_real_location()
                print(f"⚠️ Wykryto prawdopodobnie fałszywą lokalizację")
                print(f"📤 ODPOWIEDŹ: {self.response}")
                return self.response

            self._temp_detected_intent = detected_intent

            if llm_location:
                cand_entities = {"placeName": [llm_location], "geogName": [llm_location]}
            else:
                cand_entities = self.nlp_service.extract_entities(text)

            self._temp_location_id = self.data_service.validate_and_get_id(
                cand_entities,
                detected_intent or self.current_intent or self.last_intent,
                original_text=text,
            )

            await self.process_input(text)

            if self.state == "processing":
                await self.reset()

            print(f"📤 ODPOWIEDŹ: {self.response}")
            return self.response

        # STAN 'processing' – awaryjnie
        elif self.state == "processing":
            await self.reset()
            self._handle_unknown(text)
            print(f"📤 ODPOWIEDŹ: {self.response}")
            return self.response

        # Fallback
        self._handle_unknown(text)
        print(f"📤 ODPOWIEDŹ: {self.response}")
        return self.response

    # ==================== 🔥 NOWA WALIDACJA LOKALIZACJI ====================

    def _looks_like_fake_location(self, text: str) -> bool:
        """Sprawdza czy tekst wygląda na fałszywą/wymyśloną lokalizację."""
        text_lower = text.lower().strip()
        normalized = self.data_service._normalize(text_lower)

        # 🔥 NOWE: Sprawdź czy to znane zagraniczne miasto
        if normalized in self.data_service.FOREIGN_CITIES:
            print(f"   🌍 Wykryto zagraniczne miasto w input: {normalized}")
            return False  # Nie "fake", ale zagraniczne - pozwól validate_and_get_id to obsłużyć

        # Bardzo krótkie (poniżej 2 znaków) lub bardzo długie
        if len(text_lower) < 2 or len(text_lower) > 40:
            return True

        # Usuń znaki interpunkcyjne
        cleaned = ''.join(c for c in text_lower if c.isalnum() or c.isspace())
        words = cleaned.split()

        # Jeśli to więcej niż 3 słowa, prawdopodobnie to nie lokalizacja
        if len(words) > 3:
            print(f"   ⚠️ Zbyt wiele słów ({len(words)}) - prawdopodobnie nie lokalizacja")
            return True

        # Dla pojedynczego słowa - szczególna walidacja
        if len(words) == 1:
            word = words[0]

            # Zbyt krótkie pojedyncze słowo
            if len(word) < 3:
                return True

            normalized = self.data_service._normalize(word)

            # Sprawdź czy to znana lokalizacja
            is_known = self._is_known_location(normalized)

            if not is_known:
                # Sprawdź fuzzy match z wysokim cutoff (90%)
                if not self._has_close_match(normalized, cutoff=0.90):
                    print(f"   ⚠️ Prawdopodobnie fałszywa lokalizacja: '{word}'")
                    return True

        # Dla dwóch słów - sprawdź czy to znany format (np. "powiat krakowski")
        elif len(words) == 2:
            combined = ' '.join(words)
            normalized = self.data_service._normalize(combined)

            # Sprawdź czy któreś słowo jest znane
            word1_known = self._is_known_location(self.data_service._normalize(words[0]))
            word2_known = self._is_known_location(self.data_service._normalize(words[1]))
            combined_known = self._is_known_location(normalized)

            if not (word1_known or word2_known or combined_known):
                # Żadna część nie jest znana - prawdopodobnie fake
                if not self._has_close_match(words[0], cutoff=0.85):
                    print(f"   ⚠️ Nieznana dwuczłonowa lokalizacja: '{combined}'")
                    return True

        return False

    def _is_known_location(self, normalized: str) -> bool:
        """Sprawdza czy znormalizowana nazwa jest znaną lokalizacją."""
        return (
                normalized in self.data_service.simc_dict or
                normalized in self.data_service.terc_dict or
                normalized in self.data_service.VOIVODESHIPS or
                normalized in self.data_service.REGION_ALIASES or
                normalized in self.data_service.MAIN_RIVERS or
                normalized in self.data_service.map_hydro or
                any(normalized in str(key).lower() for key in self.data_service.terc_dict.keys())
        )

    def _has_close_match(self, word: str, cutoff: float = 0.85) -> bool:
        """Sprawdza czy istnieje podobna znana lokalizacja (fuzzy match)."""
        # Zbierz wszystkie znane lokalizacje
        all_locations = set()
        all_locations.update(self.data_service.simc_dict.keys())
        all_locations.update(self.data_service.terc_dict.keys())
        all_locations.update(self.data_service.VOIVODESHIPS.keys())
        all_locations.update(self.data_service.REGION_ALIASES.keys())

        # Konwertuj na listę i znajdź podobieństwa
        locations_list = list(all_locations)
        matches = difflib.get_close_matches(word, locations_list, n=1, cutoff=cutoff)

        if matches:
            print(f"   ℹ️ Znaleziono podobną lokalizację: {matches[0]}")
            return True

        return False

    def _ask_for_real_location(self) -> str:
        """🔥 Prosi o podanie prawdziwej lokalizacji."""
        if self.current_intent == "pogoda":
            return (
                "🤔 Nie rozpoznaję tej lokalizacji.\n\n"
                "Podaj nazwę polskiego miasta, np.:\n"
                "• Warszawa, Kraków, Gdańsk\n"
                "• Lublin, Poznań, Wrocław\n"
                "• Zakopane, Sopot, Białystok"
            )
        elif self.current_intent == "ostrzeżenia":
            return (
                "🤔 Nie rozpoznaję tej lokalizacji.\n\n"
                "Podaj nazwę polskiego powiatu lub województwa, np.:\n"
                "• Mazowsze, Śląsk, Małopolska\n"
                "• województwo pomorskie\n"
                "• powiat krakowski, Lublin"
            )
        elif self.current_intent == "hydro":
            return (
                "🤔 Nie rozpoznaję tego akwenu.\n\n"
                "Podaj nazwę polskiej rzeki, jeziora lub wpisz \"Bałtyk\", np.:\n"
                "• Wisła, Odra, Bug, Narew\n"
                "• Mamry, Śniardwy\n"
                "• Bałtyk"
            )
        return "🤔 Nie rozpoznaję tej lokalizacji. Podaj poprawną nazwę."

    # ==================== POZOSTAŁE HANDLERY ====================

    def _handle_forecast_unavailable(self) -> str:
        """Obsługa pytań o prognozę."""
        return (
            "🔮 Niestety, nie mam dostępu do prognoz pogody.\n\n"
            "📡 Dane które udostępniam pochodzą z pomiarów IMGW i są aktualne "
            "(ostatni pomiar z ostatnich 1-2 godzin).\n\n"
            "Mogę sprawdzić:\n"
            "🌤️ Aktualną pogodę → \"Pogoda Warszawa\"\n"
            "⚠️ Aktywne ostrzeżenia → \"Ostrzeżenia Mazowsze\"\n"
            "💧 Aktualny stan wód → \"Stan wody Wisła\""
        )

    async def _handle_station_list(self, text: str) -> str:
        """Obsługa pytań o listę stacji."""
        entities = self.nlp_service.extract_entities(text)
        water_body = None

        for name in entities.get("geogName", []):
            normalized = self.data_service._normalize(name)
            if normalized in self.data_service.MAIN_RIVERS:
                water_body = normalized
                break
            if normalized in self.data_service.map_hydro:
                water_body = normalized
                break

        if not water_body:
            text_lower = text.lower()
            for river in self.nlp_service.KNOWN_RIVERS:
                if river in text_lower:
                    water_body = self.nlp_service._get_river_base_form(river)
                    break
            for lake in self.nlp_service.KNOWN_LAKES:
                if lake in text_lower:
                    water_body = lake
                    break
            for baltic in self.nlp_service.BALTIC_KEYWORDS:
                if baltic in text_lower:
                    water_body = "bałtyk"
                    break

        if not water_body and self.last_water_body:
            water_body = self.last_water_body

        if not water_body:
            return (
                "🏞️ Dla jakiego akwenu pokazać listę stacji?\n"
                "Podaj nazwę rzeki, jeziora lub wpisz \"Bałtyk\".\n\n"
                "Przykłady: \"lista stacji Wisła\", \"stacje na Odrze\""
            )

        return await self.data_service.get_station_list(water_body)

    def _handle_county_list_request(self) -> str:
        """🔥 Obsługa pytań o pełną listę powiatów z ostrzeżeń."""
        if not self.last_warnings_data:
            return (
                "❌ Nie mam zapisanych ostrzeżeń.\n\n"
                "Najpierw sprawdź ostrzeżenia dla wybranego regionu, np.:\n"
                "\"Ostrzeżenia dla Mazowsza\" lub \"Alerty Lubelszczyzna\""
            )

        # Zbierz wszystkie powiaty ze wszystkich ostrzeżeń
        all_counties_by_warning: dict[str, list[str]] = {}

        for warning in self.last_warnings_data:
            warning_name = warning.get("nazwa_zdarzenia", "Alert")
            warning_level = warning.get("stopien", "?")
            warning_key = f"{warning_name} (stopień {warning_level})"

            teryt_codes = warning.get("teryt", [])
            if isinstance(teryt_codes, str):
                teryt_codes = [teryt_codes]

            counties = []
            for code in teryt_codes:
                if code in self.data_service.terc_reverse:
                    county_name = self.data_service.terc_reverse[code]
                    counties.append(county_name)

            if counties:
                if warning_key not in all_counties_by_warning:
                    all_counties_by_warning[warning_key] = []
                all_counties_by_warning[warning_key].extend(counties)

        if not all_counties_by_warning:
            return "❌ Brak danych o powiatach w zapisanych ostrzeżeniach."

        # Formatuj odpowiedź
        response = f"📋 Pełna lista powiatów dla: {self.last_warnings_location}\n"
        response += "=" * 45 + "\n\n"

        for warning_key, counties in all_counties_by_warning.items():
            # Usuń duplikaty i posortuj
            unique_counties = sorted(set(counties))
            response += f"⚠️ {warning_key}\n"
            response += f"📍 Liczba powiatów: {len(unique_counties)}\n\n"

            # Wyświetl powiaty w kolumnach (po 2 w wierszu)
            for i in range(0, len(unique_counties), 2):
                if i + 1 < len(unique_counties):
                    response += f"   • {unique_counties[i]:<25} • {unique_counties[i + 1]}\n"
                else:
                    response += f"   • {unique_counties[i]}\n"

            response += "\n"

        return response

    def _handle_small_talk(self, talk_type: str) -> str:
        print(f"💬 Small talk: {talk_type}")
        if self.state == 'awaiting_location':
            self.state = 'initial'
            self.current_intent = None
        if talk_type == "greeting":
            responses = [
                "Cześć! 👋 W czym mogę pomóc?",
                "Hej! 👋 Zapytaj mnie o pogodę, ostrzeżenia lub stan wód.",
                "Siema! 🌤️ Czego szukasz? Pogoda, ostrzeżenia, czy stany wód?",
                "Witaj! ☀️ Jestem Pogodowym Stróżem. Jak mogę pomóc?",
            ]
            return random.choice(responses)

        elif talk_type in ("goodbye", "thanks"):
            responses = [
                "Do usług! 👋 Wróć gdy będziesz potrzebować info o pogodzie.",
                "Nie ma sprawy! 😊 Trzymaj się!",
                "Spoko! 👍 Zapraszam ponownie.",
                "Na zdrowie! ☀️ Do następnego razu!",
            ]
            self.last_intent = None
            self.last_water_body = None
            self.last_warnings_data = []
            return random.choice(responses)

        elif talk_type == "help":
            return (
                "🤖 Jestem Pogodowym Stróżem. Umiem:\n\n"
                "🌤️ Pogoda → np. \"Pogoda w Warszawie\"\n"
                "⚠️ Ostrzeżenia → np. \"Ostrzeżenia dla Mazowsza\"\n"
                "   → potem \"podaj powiaty\" dla pełnej listy\n"
                "💧 Stany wód → rzeki, jeziora, Bałtyk\n"
                "   np. \"Stan wody Wisła\", \"Bałtyk Hel\"\n\n"
                "📋 Lista stacji → \"jakie stacje na Wiśle?\"\n\n"
                "⚠️ Uwaga: Pokazuję dane aktualne (pomiary z ostatnich 1-2h), "
                "nie prognozy na przyszłość."
            )

        elif talk_type == "nonsense":
            responses = [
                "🤔 Hmm, nie rozumiem. Zapytaj o pogodę, ostrzeżenia lub stan wód.",
                "😅 Chyba się nie rozumiemy. Spróbuj: \"Pogoda Warszawa\"",
                "🧐 Nie łapię. Jestem botem pogodowym - zapytaj o pogodę!",
            ]
            return random.choice(responses)

        return "Nie rozumiem. Zapytaj o pogodę, stan wód lub ostrzeżenia."

    def _handle_cant_do(self) -> str:
        responses = [
            (
                "😅 Niestety, tego nie umiem. Jestem tylko botem pogodowym!\n\n"
                "Mogę sprawdzić:\n"
                "🌤️ Aktualną pogodę\n"
                "⚠️ Ostrzeżenia IMGW\n"
                "💧 Stany wód (rzeki, jeziora, Bałtyk)"
            ),
            (
                "🤖 Hej, jestem Pogodowym Stróżem, nie czarodziejem! 😄\n"
                "Zapytaj mnie o pogodę, ostrzeżenia lub poziom wody."
            ),
        ]
        return random.choice(responses)

    # ==================== WARUNKI (FSM) ====================

    def _has_valid_location_and_intent(self, text) -> bool:
        return self.current_intent is not None and self.current_location_id is not None

    def _has_intent_but_no_location(self, text) -> bool:
        return self.current_intent is not None and self.current_location_id is None

    def _detected_new_intent_with_location(self, text) -> bool:
        return (
                self._temp_detected_intent is not None
                and self._temp_location_id is not None
        )

    def _detected_new_intent_without_location(self, text) -> bool:
        return (
                self._temp_detected_intent is not None
                and self._temp_location_id is None
        )

    def _check_location_in_input(self, text) -> bool:
        if self._temp_detected_intent:
            return False

        entities = self.nlp_service.extract_entities(text)
        found = self.data_service.validate_and_get_id(
            entities,
            self.current_intent,
            original_text=text,
        )
        if found:
            self.current_location_id = found
            return True
        return False

    # ==================== AKCJE (FSM) ====================

    def _prepare_new_query(self, text):
        self.current_intent = self._temp_detected_intent
        self.current_location_id = self._temp_location_id
        self.last_intent = self.current_intent
        self._temp_detected_intent = None
        self._temp_location_id = None

    async def _fetch_data_action(self, text):
        # Pobierz dane i zapisz kontekst ostrzeżeń jeśli to ostrzeżenia
        if self.current_intent == "ostrzeżenia":
            response, warnings_data = await self.data_service.fetch_warnings_with_data(
                self.current_location_id
            )
            self.response = response

            # Zapisz dane ostrzeżeń do kontekstu
            if warnings_data:
                self.last_warnings_data = warnings_data
                self.last_warnings_location = self.current_location_id.get("name", "")
                self.last_warnings_type = self.current_location_id.get("type", "")
        else:
            self.response = await self.data_service.fetch_data(
                self.current_intent,
                self.current_location_id,
            )

        # Zapamiętaj akwen
        if self.current_intent == "hydro" and self.current_location_id:
            water_body_name = self.current_location_id.get("river_name") or self.current_location_id.get("name")
            if water_body_name:
                self.last_water_body = self.data_service._normalize(water_body_name)

        if self.current_location_id and isinstance(self.current_location_id, dict):
            self.last_location_name = self.current_location_id.get("name")

        self.current_location_id = None
        self.current_intent = None

    def _ask_for_location_text(self, text):
        if self.current_intent == "pogoda":
            self.response = "🌍 Dla jakiego miasta sprawdzić pogodę?"
        elif self.current_intent == "ostrzeżenia":
            self.response = (
                "🗺️ Dla jakiego powiatu/województwa sprawdzić ostrzeżenia?\n"
                "(np. Kraków, Mazowsze, województwo śląskie)"
            )
        elif self.current_intent == "hydro":
            self.response = (
                "🏞️ Dla jakiego akwenu sprawdzić stan wody?\n"
                "Podaj nazwę rzeki (np. Wisła, Odra), jeziora (np. Mamry) "
                "lub Bałtyk."
            )
        else:
            self.response = "📍 Podaj lokalizację."

    def _ask_for_location_again(self, text):
        if self.current_intent == "hydro":
            self.response = (
                "🤔 Nie rozpoznałem akwenu.\n"
                "Podaj nazwę rzeki (np. Wisła, Odra, Bug), "
                "jeziora (np. Mamry, Śniardwy) lub wpisz \"Bałtyk\"."
            )
        else:
            self.response = "🤔 Nie rozpoznałem lokalizacji. Podaj pełną nazwę miasta lub województwa."

    def _handle_unknown(self, text):
        responses = [
            "🤔 Nie rozumiem. Zapytaj o pogodę, stan wód lub ostrzeżenia.",
            "😕 Nie łapię. Spróbuj: \"Pogoda Warszawa\" lub \"Stan wody Wisła\"",
            "🧐 Hmm? Jestem botem pogodowym. Zapytaj o pogodę!",
        ]
        self.response = random.choice(responses)

    def _finalize_response(self):
        self._temp_detected_intent = None
        self._temp_location_id = None

