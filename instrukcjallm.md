# 🌦️ Pogodowy Stróż

Inteligentny chatbot pogodowy wykorzystujący dane z IMGW-PIB i lokalny model językowy Bielik.

## 📋 Wymagania systemowe

| Komponent | Minimum | Zalecane |
|-----------|---------|----------|
| RAM | 8 GB | 16 GB |
| Dysk | 15 GB wolnego | 20 GB |
| System | Windows 10/11, Linux, macOS | - |
| Python | 3.10+ | 3.11+ |

## 🚀 Instalacja

### Krok 1: Sklonuj repozytorium

```bash
git clone https://github.com/TWOJ_USERNAME/pogodowy-stroz.git
cd pogodowy-stroz
```

### Krok 2: Utwórz środowisko wirtualne

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Krok 3: Zainstaluj zależności

```bash
pip install -r requirements.txt
```

Zainstaluj model spaCy dla języka polskiego:
```bash
python -m spacy download pl_core_news_sm
```

### Krok 4: Zainstaluj Ollama i model Bielik

#### 4.1 Zainstaluj Ollama

**Windows:**
1. Pobierz instalator: https://ollama.com/download/windows
2. Uruchom `OllamaSetup.exe`
3. Kliknij "Install"
4. Po instalacji Ollama działa w tle (ikona w zasobniku)

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

#### 4.2 Sprawdź czy Ollama działa

```bash
ollama --version
```

Powinno pokazać wersję, np. `ollama version 0.1.xx`

#### 4.3 Pobierz model Bielik (polski LLM)

```bash
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

⏳ **Uwaga:** Pobieranie może zająć 10-30 minut (6.7 GB)

#### 4.4 Sprawdź czy model się pobrał

```bash
ollama list
```

Powinieneś zobaczyć:
```
NAME                                              SIZE
SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M        6.7 GB
```

#### 4.5 Przetestuj model (opcjonalnie)

```bash
ollama run SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M "Cześć! Odpowiedz po polsku."
```

## ▶️ Uruchomienie

### Windows (PowerShell)

```powershell
$env:USE_LLM="true"
$env:LLM_PROVIDER="ollama"
$env:LLM_MODEL="SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M"

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Windows (CMD)

```cmd
set USE_LLM=true
set LLM_PROVIDER=ollama
set LLM_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Linux/macOS

```bash
USE_LLM=true LLM_PROVIDER=ollama LLM_MODEL="SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M" \
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🌐 Dostęp do aplikacji

- **Backend API:** http://localhost:8000
- **Frontend (interfejs czatu):** http://localhost:8000/static/index.html

Możesz też otworzyć plik `static/index.html` bezpośrednio w przeglądarce.

## ✅ Weryfikacja instalacji

Po uruchomieniu powinieneś zobaczyć w terminalu:

```
✅ DataService: 🏙️ 12345 miast, 🗺️ 380 powiatów, 🌊 1200 stacji hydro
✅ LLM Service zainicjalizowany (provider: ollama)
🤖 LLM status: ✅ dostępny
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🧪 Testowanie

### Test API (PowerShell)

```powershell
$body = @{
    message = "Jaka pogoda w Warszawie?"
    session_id = "test123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method POST -ContentType "application/json" -Body $body
```

### Test API (curl - Linux/macOS)

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Jaka pogoda w Warszawie?", "session_id": "test123"}'
```

## ⚠️ Rozwiązywanie problemów

### Problem: "Nie można połączyć z Ollama"

```bash
# Sprawdź czy Ollama działa
ollama list

# Jeśli nie działa, uruchom ręcznie
ollama serve
```

### Problem: "Model zbyt wolny"

Użyj mniejszego modelu:

```bash
ollama pull llama3.2:3b
```

I zmień zmienną:

```bash
LLM_MODEL=llama3.2:3b
```

### Problem: "Brak modelu spaCy"

```bash
python -m spacy download pl_core_news_sm
```

### Problem: "Port 8000 zajęty"

Użyj innego portu:

```bash
python -m uvicorn app.main:app --reload --port 8080
```

## 🔧 Uruchomienie bez LLM

Jeśli nie chcesz instalować Ollama, chatbot będzie działać z wykrywaniem intencji opartym na regułach:

```bash
USE_LLM=false python -m uvicorn app.main:app --reload
```

## 📁 Struktura projektu

```
pogodowy-stroz/
├── app/
│   ├── api/
│   │   └── imgw_client.py      # Klient API IMGW
│   ├── data/
│   │   ├── simc_dict.json      # Słownik miast
│   │   ├── terc_dict.json      # Słownik powiatów
│   │   └── map_hydro.json      # Mapowanie stacji hydro
│   ├── logic/
│   │   ├── conversation.py     # Logika konwersacji (FSM)
│   │   └── nlp.py              # Przetwarzanie języka
│   ├── services/
│   │   ├── data_service.py     # Serwis danych
│   │   └── llm_service.py      # Integracja z LLM
│   └── main.py                 # Główny plik FastAPI
├── static/
│   ├── index.html              # Frontend
│   ├── script.js
│   └── style.css
├── requirements.txt
└── README.md
```

## 📝 Licencja

[Dodaj informacje o licencji]

## 🤝 Wkład

[Dodaj informacje o kontrybucji]

## 📧 Kontakt

[Dodaj informacje kontaktowe]