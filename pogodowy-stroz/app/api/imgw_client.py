# app/api/imgw_client.py
import httpx
from fastapi import HTTPException

class ImgwApiClient:
    def __init__(self):
        self.base_url = "https://danepubliczne.imgw.pl/api/data"
        # Timeout zwiększony dla bezpieczeństwa
        self.async_client = httpx.AsyncClient(timeout=20.0)

    async def get_synop_data(self, station_id: str):
        """Pobiera dane pogodowe (SYNOP) dla stacji."""
        url = f"{self.base_url}/synop/id/{station_id}"
        return await self._get(url, "API Pogodowe")

    async def get_hydro_data(self, station_id: str):
        """Pobiera dane hydrologiczne dla stacji."""
        url = f"{self.base_url}/hydro/id/{station_id}"
        return await self._get(url, "API Hydrologiczne")

    async def get_meteo_warnings(self):
        """
        Pobiera surową listę ostrzeżeń z https://danepubliczne.imgw.pl/api/data/meteo/worn.
        Filtrowanie odbywa się po stronie DataService.
        """
        url = "https://danepubliczne.imgw.pl/api/data/meteo/worn" # Pełny URL dla pewności
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
        except Exception as e:
            # Logujemy błąd wewnętrznie
            print(f"CRITICAL ERROR connecting to {url}: {e}")
            raise HTTPException(status_code=503, detail=f"Serwis {service_name} niedostępny lub błąd sieci.")
