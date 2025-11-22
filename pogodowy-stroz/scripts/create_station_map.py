# scripts/create_station_map.py
import httpx
import json
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"


def normalize_text(text: str) -> str:
    if not isinstance(text, str): return ""
    text = text.lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return text.strip().replace("-", " ")  # Zamieniamy myślniki na spacje dla łatwiejszego porównania


def main():
    print("--- Rozpoczynanie INTELIGENTNEGO mapowania stacji IMGW ---")

    # 1. Pobierz stacje
    url = "https://danepubliczne.imgw.pl/api/data/synop"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        stations = response.json()
    except Exception as e:
        print(f"Błąd pobierania: {e}")
        return

    # 2. Wczytaj słownik SIMC
    simc_path = DATA_DIR / "simc_dict.json"
    if not simc_path.exists():
        print("Brak simc_dict.json! Uruchom najpierw prepare_teryt.py")
        return

    with open(simc_path, "r", encoding="utf-8") as f:
        simc_dict = json.load(f)

    # Odwracamy słownik SIMC, żeby szukać kodu po nazwie (nazwa -> id)
    # simc_dict jest teraz: { "warszawa": "0918123", ... }

    map_simc_to_synop = {}
    matched_count = 0

    print(f"Przetwarzanie {len(stations)} stacji...")

    for station in stations:
        original_name = station['stacja']
        station_id = station['id_stacji']
        norm_station = normalize_text(original_name)  # np. "poznan lawica"

        # STRATEGIA 1: Dokładne dopasowanie
        # Sprawdzamy czy "poznan lawica" jest kluczem w SIMC (mało prawdopodobne)
        found_simc_id = simc_dict.get(norm_station)

        # STRATEGIA 2: Szukanie podciągów (Dla "Poznań-Ławica", "Wrocław-Strachowice")
        if not found_simc_id:
            # Dzielimy nazwę stacji na słowa: ["poznan", "lawica"]
            parts = norm_station.split()
            for part in parts:
                # Jeśli człon nazwy (np. "poznan") jest w słowniku miast, bierzemy to!
                # Warunek len(part) > 2 eliminuje krótkie śmieci
                if part in simc_dict and len(part) > 2:
                    found_simc_id = simc_dict[part]
                    print(f"   Dopasowano (fuzzy): {original_name} -> {part}")
                    break

        if found_simc_id:
            map_simc_to_synop[found_simc_id] = station_id
            matched_count += 1
        else:
            print(f"❌ Brak dopasowania dla stacji: {original_name}")

    # Zapisz wynik
    out_path = DATA_DIR / "map_simc_to_imgw_synop.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(map_simc_to_synop, f, indent=2)

    print(f"\nSUKCES: Zmapowano {matched_count} z {len(stations)} stacji.")
    print("PAMIĘTAJ: Zrestartuj serwer, aby załadować nowe mapowania!")


if __name__ == "__main__":
    main()