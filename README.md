
# 🌦️ Pogodowy Stróż – Instrukcja Instalacji

Projekt składa się z dwóch części:
- **Backend (Python/FastAPI):** Mózg operacji, łączy się z IMGW i przetwarza język naturalny.
- **Frontend (Lovable/React):** Nowoczesny interfejs użytkownika.

---

## 🛠️ CZĘŚĆ 1: Backend (Python)

### Wymagania

- Python 3.10 lub nowszy
- Połączenie z internetem (do pobierania danych z IMGW i map)

### Instrukcja instalacji

#### Krok 1: Pobierz projekt i wejdź do folderu

Rozpakuj projekt i otwórz terminal (konsolę) w folderze `pogodowy-stroz`.

#### Krok 2: Stwórz i aktywuj wirtualne środowisko

To izoluje projekt od reszty systemu.

##### Dla Windows (PowerShell):


python -m venv venv
.\venv\Scripts\Activate.ps1


Jeśli wystąpi błąd o uprawnieniach:

```
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

i spróbuj ponownie aktywować środowisko.

##### Dla Mac/Linux:

```
python3 -m venv venv
source venv/bin/activate
```

Po aktywacji powinieneś widzieć `(venv)` na początku linii w terminalu.

#### Krok 3: Zainstaluj biblioteki

```
pip install -r requirements.txt
```

Jeśli nie masz pliku `requirements.txt`, zainstaluj ręcznie:

```
pip install fastapi uvicorn httpx spacy transitions geopy pandas
```

#### Krok 4: Pobierz model językowy (AI)

Backend potrzebuje polskiego modelu do analizy tekstu:

```
python -m spacy download pl_core_news_sm
```

#### Krok 5: Weryfikacja danych (KRYTYCZNE!) ⚠️

Sprawdź, czy w folderze `app/data/` znajdują się pliki `.json`. Powinny być tam:
- terc_dict.json
- simc_dict.json
- map_simc_to_imgw_synop.json
- map_hydro.json
- station_coords.json

Jeśli folder jest pusty: skopiuj pliki od autora projektu lub wygeneruj je skryptami z folderu `scripts/` (potrzebne surowe pliki CSV z GUS).

#### Krok 6: Uruchom serwer

Będąc w głównym folderze projektu, wpisz:

```
uvicorn app.main:app --reload
```

Serwer powinien wystartować na porcie 8000. Skontroluj działanie przez wejście w przeglądarce na: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🎨 CZĘŚĆ 2: Frontend (Lovable/React)

To nowoczesny interfejs graficzny wygenerowany przez Lovable.

### Wymagania

- Node.js (wersja 18 lub nowsza) – pobierz ze strony [nodejs.org](https://nodejs.org/)

### Instrukcja instalacji

#### Krok 1: Wejdź do folderu z frontendem

W terminalu przejdź do folderu z plikami Lovable (tam, gdzie jest plik `package.json`), np.:

```
cd frontend-lovable
```

#### Krok 2: Zainstaluj zależności

```
npm install
```

#### Krok 3: Uruchom stronę

```
npm run dev
```

#### Krok 4: Otwórz aplikację

Terminal pokaże adres lokalny, np.: [http://localhost:5173](http://localhost:5173)

---

## 🆘 Rozwiązywanie problemów

1. **Frontend nie łączy się z Backendem (Błąd sieci):**
   - Upewnij się, że Backend (uvicorn) działa w osobnym oknie terminala.
   - Sprawdź, czy w pliku `app/main.py` jest dodany CORSMiddleware z `allow_origins=["*"]`.

2. **Bot odpowiada "Nie znalazłem takiej lokalizacji" na wszystko:**
   - Brakuje plików w `app/data/`. Sprawdź Krok 5 w sekcji Backend.

3. **Błąd ModuleNotFoundError: No module named 'app':**
   - Uruchamiasz komendę uvicorn ze złego folderu. Musisz być w katalogu nadrzędnym, w którym bezpośrednio widać folder `app`.
