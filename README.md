# Pogodowy Stróż - Asystent Meteo

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)
![Tailwind CSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-%2309A3D5.svg?style=for-the-badge&logo=spacy&logoColor=white)

Zaawansowany system konwersacyjny (chatbot) służący do sprawdzania pogody, ostrzeżeń meteorologicznych oraz stanów hydrologicznych w Polsce. Projekt łączy potężny backend oparty na Pythonie i sztucznej inteligencji z nowoczesnym frontendem wygenerowanym przez Lovable.

---

## Kluczowe Funkcjonalności

Aplikacja została zaprojektowana jako dwuczłonowy system (Klient-Serwer), oferujący:

* **Zaawansowane Przetwarzanie Języka (NLP):**
    * **Analiza Intencji:** System wykorzystuje bibliotekę **spaCy** oraz autorskie algorytmy punktacji słów kluczowych, aby rozróżnić pytania o pogodę, ostrzeżenia czy stany rzek.
    * **Ekstrakcja Encji:** Automatyczne wyciąganie nazw miast, powiatów i rzek z naturalnych zapytań użytkownika.

* **Integracja z Danymi Publicznymi (IMGW):**
    * **Dane Synoptyczne:** Pobieranie aktualnej temperatury, ciśnienia i wiatru ze stacji pomiarowych.
    * **Hydro:** Sprawdzanie stanów wód w rzekach.
    * **System Ostrzeżeń:** Filtrowanie oficjalnych alertów meteo dla konkretnych powiatów na podstawie kodów TERYT.

* **Inteligentna Geolokalizacja:**
    * **Algorytm "Najbliższego Sąsiada":** Jeśli użytkownik zapyta o małą wieś, system geokoduje ją i automatycznie znajduje najbliższą stację pomiarową IMGW, podając odległość.
    * **Fuzzy Matching:** Obsługa literówek i polskiej odmiany (np. rozpoznawanie "w *Lublinie*" jako "Lublin").

* **Nowoczesny Interfejs Użytkownika:**
    * Responsywny frontend zbudowany w **React** i **Tailwind CSS**.
    * Estetyczny design typu "chat" zapewniający płynną komunikację z botem.

---

## Stos Technologiczny

### Backend (API & Logika)
* **Język:** Python 3.10+
* **Framework API:** FastAPI + Uvicorn
* **NLP:** spaCy (model `pl_core_news_sm`)
* **Przetwarzanie Danych:** Pandas, Geopy (Geocoding), HTTPX (Asynchroniczne zapytania)
* **Logika Konwersacji:** Biblioteka `transitions` (Async State Machine)

### Frontend (Interfejs)
* **Framework:** React (Vite)
* **Styling:** Tailwind CSS
* **Runtime:** Node.js

---

## Uruchomienie Projektu

Projekt składa się z dwóch niezależnych części, które muszą działać jednocześnie. Zaleca się uruchomienie najpierw Backendu.

### 🛠️ Część 1: Backend (Python)

Mózg operacji. Wymaga połączenia z internetem do pobierania danych IMGW.

#### 1. Przygotowanie Środowiska
Otwórz terminal w folderze `pogodowy-stroz`.

**Dla Windows (PowerShell):**
```bash
  python -m venv venv
  .\venv\Scripts\Activate.ps1
```
*(Jeśli wystąpi błąd o uprawnieniach, wpisz: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` i spróbuj ponownie)*

**Dla Mac/Linux:**
```bash
  python3 -m venv venv
  source venv/bin/activate
```

Po aktywacji powinieneś widzieć (venv) na początku linii w terminalu.

### Krok 3: Zainstaluj biblioteki
```bash
  pip install -r requirements.txt
```
Jeśli nie masz pliku `requirements.txt`, zainstaluj ręcznie:

```bash
  pip install fastapi uvicorn httpx spacy transitions geopy pandas
```
### Krok 4: Generacja Mapy Współrzędnych (Geokodowanie Stacji) 🌍

Ponieważ bot musi wiedzieć, gdzie leży każda z 60 stacji IMGW, musisz wygenerować plik z koordynatami.

**Upewnij się, że masz już zainstalowaną bibliotekę `geopy` (Krok 2).**

```bash
# Uruchom ten skrypt, aby stworzyć station_coords.json
python scripts/get_station_coords.py
```
### Krok 5: Pobierz model językowy (AI)

Backend potrzebuje polskiego modelu do zrozumienia, czym jest "miasto" w zdaniu.

```bash
  python -m spacy download pl_core_news_sm
```

### Krok 6: Weryfikacja Danych (KRYTYCZNE!) ⚠️

Sprawdź, czy w folderze `app/data/` znajdują się pliki `.json`. Bez nich bot nie zadziała.

W folderze `app/data/` powinny być:

- `terc_dict.json`
- `simc_dict.json`
- `map_simc_to_imgw_synop.json`
- `map_hydro.json`
- `station_coords.json`

**Uwaga:** Jeśli folder jest pusty, musisz skopiować te pliki od autora projektu lub wygenerować je skryptami z folderu `scripts/` (wymaga to posiadania surowych plików CSV z GUS).

### Krok 7: Uruchom serwer

Będąc w głównym folderze projektu, wpisz:

```bash
  uvicorn app.main:app --reload
```

Serwer powinien wystartować na porcie 8000.  
Sprawdź, czy działa, wchodząc w przeglądarce na: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---
## Autorzy

Backend: Rafał Zaborek & Jakub Zatorski & Jakub Różycki.