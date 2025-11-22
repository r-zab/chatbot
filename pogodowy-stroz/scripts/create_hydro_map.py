import httpx
import json
import unicodedata
from pathlib import Path

# Ścieżka do zapisu
SAVE_PATH = Path(__file__).parent.parent / "app" / "data" / "map_hydro.json"

def normalize(text):
    if not text: return ""
    text = text.lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return text.strip()

def main():
    print("Pobieranie stacji hydrologicznych z IMGW...")
    try:
        # Pobieramy wszystkie dane hydro
        resp = httpx.get("https://danepubliczne.imgw.pl/api/data/hydro/", timeout=20)
        data = resp.json()
    except Exception as e:
        print(f"Błąd pobierania: {e}")
        return

    hydro_map = {}

    print(f"Przetwarzanie {len(data)} stacji...")

    for station in data:
        # station wygląda tak: {"id_stacji": "150190060", "stacja": "Annopol", "rzeka": "Wisła", ...}
        stacja_id = station['id_stacji']
        nazwa_stacji = normalize(station['stacja']) # np. annopol
        nazwa_rzeki = normalize(station['rzeka'])   # np. wisla

        # Mapujemy RZEKĘ na ID stacji (uwaga: rzeka ma wiele stacji, nadpisujemy - to uproszczenie)
        # Lepsza metoda: zapamiętać listę stacji dla rzeki, ale tutaj robimy prosto:
        if nazwa_rzeki not in hydro_map:
            hydro_map[nazwa_rzeki] = stacja_id

        # Mapujemy NAZWĘ STACJI na ID (np. "Annopol")
        hydro_map[nazwa_stacji] = stacja_id

        # Mapujemy "Rzeka Stacja" (np. "Wisła Annopol")
        hydro_map[f"{nazwa_rzeki} {nazwa_stacji}"] = stacja_id

    # Zapis
    SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(hydro_map, f, indent=2)

    print(f"Gotowe! Zapisano {len(hydro_map)} kluczy mapowania w {SAVE_PATH}")

if __name__ == "__main__":
    main()
