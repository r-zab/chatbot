# scripts/get_station_coords.py
import json
import httpx
from geopy.geocoders import Nominatim
from pathlib import Path
import time

# Ustawiamy User-Agent (wymagane przez Nominatim)
geolocator = Nominatim(user_agent="pogodowy_stroz_app")

DATA_DIR = Path(__file__).parent.parent / "app" / "data"


def main():
    print("1. Pobieranie listy stacji z IMGW...")
    try:
        resp = httpx.get("https://danepubliczne.imgw.pl/api/data/synop", timeout=10)
        stations = resp.json()
    except Exception as e:
        print(f"Błąd IMGW: {e}")
        return

    station_coords = {}

    print(f"2. Geokodowanie {len(stations)} stacji (może to chwilę potrwać)...")

    for stacja in stations:
        name = stacja['stacja']
        stacja_id = stacja['id_stacji']

        # Próbujemy znaleźć współrzędne miasta
        try:
            location = geolocator.geocode(f"{name}, Polska")
            if location:
                station_coords[stacja_id] = {
                    "name": name,
                    "lat": location.latitude,
                    "lon": location.longitude
                }
                print(f"✅ {name}: {location.latitude}, {location.longitude}")
            else:
                print(f"❌ Nie znaleziono: {name}")
        except Exception as e:
            print(f"⚠️ Błąd dla {name}: {e}")

        # Ważne: opóźnienie, żeby nie zablokowali nam API Nominatim
        time.sleep(1.0)

        # Zapis do pliku
    save_path = DATA_DIR / "station_coords.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(station_coords, f, indent=2)

    print(f"\nGotowe! Zapisano współrzędne w {save_path}")


if __name__ == "__main__":
    main()