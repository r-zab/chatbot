# app/api/imgw_client.py
import httpx
from fastapi import HTTPException


class ImgwApiClient:
    def __init__(self):
        self.base_url = "https://danepubliczne.imgw.pl/api/data"
        self.async_client = httpx.AsyncClient(timeout=20.0)

    async def get_synop_data(self, station_id: str):
        """Pobiera dane pogodowe (SYNOP) dla stacji."""
        url = f"{self.base_url}/synop/id/{station_id}"
        return await self._get(url, "API Pogodowe")

    async def get_hydro_data(self, station_id: str):
        """Pobiera dane hydrologiczne dla stacji."""
        url = f"{self.base_url}/hydro/id/{station_id}"
        return await self._get(url, "API Hydrologiczne")

    async def get_all_hydro_data(self):
        """Pobiera WSZYSTKIE dane hydrologiczne - do wyszukiwania."""
        url = f"{self.base_url}/hydro"
        return await self._get(url, "API Hydrologiczne (wszystkie)")

    async def get_hydro_by_river(self, river_name: str) -> list:
        """
        Pobiera wszystkie stacje dla danej rzeki.
        Przeszukuje wszystkie dane hydro i filtruje po nazwie rzeki.
        """
        all_data = await self.get_all_hydro_data()
        if not isinstance(all_data, list):
            return []

        river_lower = river_name.lower().strip()

        # Normalizacja - usunięcie polskich znaków do porównania
        def normalize(text):
            if not text:
                return ""
            replacements = {
                'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
                'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
            }
            text = text.lower()
            for pl, en in replacements.items():
                text = text.replace(pl, en)
            return text

        river_norm = normalize(river_lower)

        matching = []
        for station in all_data:
            station_river = station.get('rzeka', '')
            if normalize(station_river) == river_norm or river_norm in normalize(station_river):
                matching.append(station)

        return matching

    async def get_meteo_warnings(self):
        """Pobiera listę ostrzeżeń meteorologicznych."""
        url = "https://danepubliczne.imgw.pl/api/data/warningsmeteo"
        return await self._get(url, "API Ostrzeżeń")

    async def _get(self, url: str, service_name: str):
        try:
            response = await self.async_client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Brak danych dla {service_name}.")
            raise HTTPException(status_code=e.response.status_code, detail=f"Błąd {service_name}: {e.response.text}")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail=f"Timeout - {service_name} nie odpowiada.")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"Nie można połączyć z {service_name}.")
        except Exception as e:
            print(f"CRITICAL ERROR connecting to {url}: {e}")
            raise HTTPException(status_code=503, detail=f"Serwis {service_name} niedostępny.")