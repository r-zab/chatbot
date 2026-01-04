# 🌤️ Pogodowy Stróż - Asystent Meteo

![Python](https://img.shields.io/badge/python-3.12+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![spaCy](https://img.shields.io/badge/spaCy-%2309A3D5.svg?style=for-the-badge&logo=spacy&logoColor=white)

Zaawansowany chatbot pogodowy wykorzystujący NLP i maszynę stanów do kontekstowych rozmów o pogodzie, ostrzeżeniach meteorologicznych i stanach wód w Polsce (API IMGW).

## 🎯 Demo

```
👤 Pogoda w Warszawie
🤖 🌡️ -3.5°C, 💨 2 m/s, 🌧️ 1.1 mm

👤 A w Krakowie?
🤖 🌡️ -3.6°C, 💨 4 m/s, 🌧️ 0.01 mm

👤 Stan wody w Wiśle
🤖 💧 Rzeka: Wisła, Stacja: Wisła, Stan: 95 cm
```

## ✨ Funkcje

- **NLP z spaCy** - rozpoznawanie intencji, ekstrakcja encji, obsługa odmiany ("w Wiśle" → "Wisła")
- **Pamięć kontekstu** - "Pogoda Warszawa" → "A w Krakowie?" działa poprawnie
- **Fuzzy matching** - tolerancja na literówki (85-95% podobieństwa)
- **Geolokalizacja** - algorytm najbliższej stacji dla miast bez pomiarów
- **Integracja IMGW** - 60+ stacji synoptycznych, 600+ stacji hydrologicznych, alerty meteo

## 🏗️ Architektura

```
Frontend (HTML/CSS/JS) ←→ FastAPI Backend
                           ├── NLP (spaCy + logic/nlp.py)
                           ├── FSM (transitions + logic/conversation.py)
                           ├── Data Service (walidacja, fuzzy matching)
                           └── IMGW API Client (httpx)
```

## 🛠️ Technologie

**Backend:** Python 3.12+, FastAPI, spaCy, transitions, httpx, geopy  
**Frontend:** HTML5, CSS3, Vanilla JavaScript  
**Dane:** JSON (TERYT, SIMC, mapy stacji IMGW)

## 🚀 Instalacja

```bash
# Sklonuj i stwórz środowisko
git clone https://github.com/twoj-user/pogodowy-stroz.git
cd pogodowy-stroz
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1

# Zainstaluj zależności
pip install -r requirements.txt
python -m spacy download pl_core_news_sm

# Uruchom serwer
uvicorn app.main:app --reload
```

**Aplikacja:** http://127.0.0.1:8000  
**API Docs:** http://127.0.0.1:8000/docs

## 📁 Struktura

```
app/
├── api/imgw_client.py          # Klient API IMGW
├── logic/
│   ├── nlp.py                  # Przetwarzanie języka
│   └── conversation.py         # Maszyna stanów
├── services/data_service.py    # Walidacja i geolokalizacja
├── data/*.json                 # Mapy TERYT i stacji
└── main.py                     # FastAPI endpointy
static/                         # Frontend (HTML/CSS/JS)
scripts/                        # Skrypty pomocnicze
```

## 🧪 Przykłady

```
Pogoda w Warszawie
Ostrzeżenia dla Krakowa
Stan wody w Wiśle
A w Sanie?                # Kontekst
Woda w Warcie             # Odmiana
```

## ❗ Troubleshooting

**Brak modelu spaCy:**  
```bash
python -m spacy download pl_core_news_sm
```

**PowerShell - błąd uprawnień:**  
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 👥 Autorzy

Rafał Zaborek, Jakub Zatorski, Jakub Różycki

## 📄 Licencja

MIT License

