import json
import httpx
import time
from geopy.geocoders import Nominatim
from pathlib import Path

# Ustawienia
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
SAVE_PATH = DATA_DIR / "station_coords.json"

# Inicjalizacja geokodera (wymaga unikalnego user-agent)
geolocator = Nominatim(user_agent="pogodowy_stroz_script_generator")


def main():
    print("--- Generowanie współrzędnych stacji IMGW ---")

    # 1. Pobierz listę stacji z IMGW
    url = "https://danepubliczne.imgw.pl/api/data/synop"
    try:
        print(f"Pobieranie listy stacji z: {url}")
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        stations = response.json()
    except Exception as e:
        print(f"BŁĄD: Nie udało się pobrać danych z IMGW: {e}")
        return

    station_coords = {}
    print(f"Znaleziono {len(stations)} stacji. Rozpoczynam geokodowanie...")

    # 2. Dla każdej stacji znajdź współrzędne GPS
    for i, station in enumerate(stations):
        name = station['stacja']
        station_id = station['id_stacji']

        # Zapytanie do OpenStreetMap (Nominatim)
        query = f"{name}, Polska"

        try:
            location = geolocator.geocode(query)

            if location:
                station_coords[station_id] = {
                    "name": name,
                    "lat": location.latitude,
                    "lon": location.longitude
                }
                print(f"[{i + 1}/{len(stations)}] ✅ {name}: {location.latitude}, {location.longitude}")
            else:
                print(f"[{i + 1}/{len(stations)}] ❌ Nie znaleziono współrzędnych dla: {name}")

        except Exception as e:
            print(f"⚠️ Błąd geokodowania dla {name}: {e}")

        # Ważne: opóźnienie, żeby nie zablokowali nam dostępu do API map
        time.sleep(1.0)

    # 3. Zapisz wynik do pliku
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(station_coords, f, indent=2)
        print(f"\nSUKCES! Zapisano mapę współrzędnych w: {SAVE_PATH}")
    except Exception as e:
        print(f"Błąd zapisu pliku: {e}")


if __name__ == "__main__":
    main()