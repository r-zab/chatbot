# app/services/llm_service.py

import httpx
import json
import os
from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMProvider(ABC):
    """Bazowa klasa dla providerów LLM."""

    @abstractmethod
    async def classify_intent(self, text: str) -> dict:
        """Klasyfikuje intencję użytkownika."""
        pass


class OllamaProvider(BaseLLMProvider):
    """
    Provider dla Ollama (lokalne LLM).
    Obsługuje Bielik, Llama, Mistral itp.
    Instalacja Ollama: https://ollama.ai
    Pobranie Bielika: ollama pull SpeakLeash/bielik-7b-instruct-v0.1-gguf
    """

    def __init__(
        self,
        model_name: str = "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M",
        base_url: str = "http://localhost:11434",
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def classify_intent(self, text: str) -> dict:
        prompt = self._build_prompt(text)
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Niska temperatura dla spójności
                        "num_predict": 100,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            raw = result.get("response", "") or ""
            return self._parse_response(raw)
        except Exception as e:
            print(f"❌ Ollama error: {e}")
            return {"intent": None, "confidence": 0.0, "error": str(e), "entities": {}}

    def _build_prompt(self, text: str) -> str:
        # Bardziej restrykcyjny prompt z przykładami (few-shot)
        return f"""
INST
Jesteś polskim klasyfikatorem intencji dla bota pogodowego.
Masz zwrócić TYLKO jeden obiekt JSON, bez żadnego dodatkowego tekstu przed ani po.

Dostępne intencje:
- "pogoda" – pytania o pogodę, temperaturę, opady, wiatr, zachmurzenie itp.
- "ostrzeżenia" – ostrzeżenia i alerty meteorologiczne, np. burze, wichury, upały, mróz.
- "hydro" – stan wód, rzeki, poziom wody, wodowskazy, powodzie.
- null – wszystko inne (small talk, pytania spoza pogody).

Pole "entities.location" powinno zawierać krótką nazwę miejsca/rzeki/regionu, jeśli da się ją wyciągnąć, np.:
- "Warszawa"
- "Lublin"
- "Wisła"
- "województwo lubelskie"
Jeśli nie ma miejsca w zdaniu, ustaw "location" na null lub pomiń to pole.

Przykłady:

Użytkownik: "Pogoda w Warszawie jutro"
Odpowiedź:
{{"intent": "pogoda", "confidence": 0.95, "entities": {{"location": "Warszawa"}}}}

Użytkownik: "Czy są jakieś ostrzeżenia dla Lubelszczyzny?"
Odpowiedź:
{{"intent": "ostrzeżenia", "confidence": 0.92, "entities": {{"location": "województwo lubelskie"}}}}

Użytkownik: "Stan wody Wisła w Fordonie"
Odpowiedź:
{{"intent": "hydro", "confidence": 0.96, "entities": {{"location": "Wisła Fordon"}}}}

Użytkownik: "Cześć, jak działasz?"
Odpowiedź:
{{"intent": null, "confidence": 0.9, "entities": {{}}}}

Teraz sklasyfikuj:

Użytkownik: "{text}"
Odpowiedź:
INST JSON
""".strip()

    def _parse_response(self, response: str) -> dict:
        """Parsuje odpowiedź LLM do struktury danych."""
        try:
            if not response:
                return {"intent": None, "confidence": 0.0, "entities": {}}

            response = response.strip()
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx == -1 or end_idx <= start_idx:
                print(f"⚠️ Brak JSON w odpowiedzi LLM: {response[:200]}")
                return {"intent": None, "confidence": 0.0, "entities": {}}

            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)

            # Prosta walidacja struktury
            if "intent" not in result:
                print(f"⚠️ Brak pola 'intent' w JSON: {json_str}")
                return {"intent": None, "confidence": 0.0, "entities": {}}

            intent = result.get("intent")
            if intent is not None:
                intent = str(intent).lower().strip()

            # Mapowanie wariantów
            intent_map = {
                "ostrzezenia": "ostrzeżenia",
                "ostrzezenie": "ostrzeżenia",
                "alert": "ostrzeżenia",
                "alerty": "ostrzeżenia",
                "weather": "pogoda",
                "pogoda": "pogoda",
                "hydrology": "hydro",
                "hydro": "hydro",
                "woda": "hydro",
                "rzeka": "hydro",
            }
            intent = intent_map.get(intent, intent)

            # Normalizacja entities
            entities = result.get("entities") or {}
            if not isinstance(entities, dict):
                entities = {}

            # Upewnij się, że location jest stringiem lub None
            loc = entities.get("location")
            if loc is not None:
                entities["location"] = str(loc).strip() or None

            confidence_raw = result.get("confidence", 0.8)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.8

            return {
                "intent": intent,
                "confidence": confidence,
                "entities": entities,
            }

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}, response: {response[:200]}")
            return {"intent": None, "confidence": 0.0, "entities": {}}
        except Exception as e:
            print(f"⚠️ Parse error: {e}, response: {response[:200]}")
            return {"intent": None, "confidence": 0.0, "entities": {}}


class OpenAIProvider(BaseLLMProvider):
    """
    Provider dla OpenAI API.
    Wymaga klucza API w zmiennej środowiskowej OPENAI_API_KEY.
    """

    def __init__(self, model: str = "gpt-3.5-turbo", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def classify_intent(self, text: str) -> dict:
        if not self.api_key:
            return {"intent": None, "confidence": 0.0, "error": "Brak klucza API", "entities": {}}
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": """Jesteś klasyfikatorem intencji dla polskiego bota pogodowego.
Zwracaj TYLKO JSON bez żadnego dodatkowego tekstu.
Dostępne intencje:
- "pogoda" - pytania o pogodę, temperaturę, warunki atmosferyczne
- "ostrzeżenia" - ostrzeżenia meteorologiczne, alerty, zagrożenia pogodowe
- "hydro" - stan wód, rzeki, poziom wody, wodowskazy, powodzie
Format odpowiedzi:
{"intent": "nazwa_lub_null", "confidence": 0.0-1.0, "entities": {"location": "nazwa_lub_null"}}""",
                        },
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100,
                },
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return self._parse_response(content)
        except Exception as e:
            print(f"❌ OpenAI error: {e}")
            return {"intent": None, "confidence": 0.0, "error": str(e), "entities": {}}

    def _parse_response(self, response: str) -> dict:
        try:
            response = (response or "").strip()
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx == -1 or end_idx <= start_idx:
                return {"intent": None, "confidence": 0.0, "entities": {}}
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)
            return {
                "intent": result.get("intent"),
                "confidence": float(result.get("confidence", 0.8)),
                "entities": result.get("entities", {}) or {},
            }
        except Exception as e:
            print(f"⚠️ Parse error: {e}")
            return {"intent": None, "confidence": 0.0, "entities": {}}


class HuggingFaceProvider(BaseLLMProvider):
    """
    Provider dla HuggingFace Inference API.
    Możesz użyć Bielika hostowanego na HF.
    """

    def __init__(self, model_id: str = "speakleash/Bielik-7B-Instruct-v0.1", api_key: Optional[str] = None):
        self.model_id = model_id
        self.api_key = api_key or os.getenv("HF_API_KEY")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def classify_intent(self, text: str) -> dict:
        if not self.api_key:
            return {"intent": None, "confidence": 0.0, "error": "Brak klucza HF API", "entities": {}}

        prompt = f"""[INST] Jesteś klasyfikatorem intencji. Klasyfikuj tekst do jednej z kategorii:
- pogoda (pytania o pogodę)
- ostrzeżenia (alerty meteorologiczne)
- hydro (stany wód, rzeki)
- null (inne)
Zwróć TYLKO JSON: {{"intent": "...", "confidence": 0.9, "entities": {{"location": "..."}}}}
Tekst: {text} [/INST]"""

        try:
            response = await self.client.post(
                f"https://api-inference.huggingface.co/models/{self.model_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 100,
                        "temperature": 0.1,
                        "return_full_text": False,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated = result[0].get("generated_text", "") or ""
                return self._parse_response(generated)
            return {"intent": None, "confidence": 0.0, "entities": {}}
        except Exception as e:
            print(f"❌ HuggingFace error: {e}")
            return {"intent": None, "confidence": 0.0, "error": str(e), "entities": {}}

        # parse_response jak w Ollama/OpenAI, ale prostsze

    def _parse_response(self, response: str) -> dict:
        try:
            response = (response or "").strip()
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx == -1 or end_idx <= start_idx:
                return {"intent": None, "confidence": 0.0, "entities": {}}
            json_str = response[start_idx:end_idx]
            result = json.loads(json_str)
            entities = result.get("entities", {}) or {}
            return {
                "intent": result.get("intent"),
                "confidence": float(result.get("confidence", 0.8)),
                "entities": entities,
            }
        except Exception:
            return {"intent": None, "confidence": 0.0, "entities": {}}


class LLMService:
    """
    Główny serwis LLM z fallbackiem.
    Próbuje używać LLM, a jeśli się nie uda - wraca do reguł.
    """

    def __init__(self, provider: str = "ollama", **kwargs):
        self.provider = self._create_provider(provider, **kwargs)
        self.fallback_enabled = True

    def _create_provider(self, provider: str, **kwargs) -> BaseLLMProvider:
        providers = {
            "ollama": OllamaProvider,
            "openai": OpenAIProvider,
            "huggingface": HuggingFaceProvider,
        }
        if provider not in providers:
            print(f"⚠️ Nieznany provider '{provider}', używam Ollama")
            provider = "ollama"
        return providers[provider](**kwargs)

    async def classify_intent(self, text: str) -> dict:
        """
        Klasyfikuje intencję używając LLM.
        Zwraca dict z kluczami: intent, confidence, entities
        """
        result = await self.provider.classify_intent(text)

        # Walidacja wyniku
        valid_intents = {"pogoda", "ostrzeżenia", "hydro", None}
        if result.get("intent") not in valid_intents:
            result["intent"] = None
            result["confidence"] = 0.0

        # Upewnij się, że entities istnieje
        if "entities" not in result or not isinstance(result["entities"], dict):
            result["entities"] = {}

        return result

    async def is_available(self) -> bool:
        """Sprawdza czy LLM jest dostępny."""
        try:
            result = await self.classify_intent("test pogoda warszawa")
            return "error" not in result
        except Exception:
            return False
