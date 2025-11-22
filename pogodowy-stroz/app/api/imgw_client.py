# app/api/imgw_client.py
import httpx
from fastapi import HTTPException

class ImgwApiClient:
    def __init__(self):
        # Base URL kończy się na /api/data, więc endpointy doklejamy po slashu
        self.base_url = "https://danepubliczne.imgw.pl/api/data"
        self.async_client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)

    async def get_synop_data(self, station_id: str):
        """Pobiera dane pogodowe (SYNOP)."""
        # Adres: https://danepubliczne.imgw.pl/api/data/synop/id/{id}
        return await self._get(f"/synop/id/{station_id}", "API Pogodowe")

    async def get_hydro_data(self, station_id: str):
        """Pobiera dane hydrologiczne."""
        # Adres: https://danepubliczne.imgw.pl/api/data/hydro/id/{id}
        return await self._get(f"/hydro/id/{station_id}", "API Hydrologiczne")

    async def get_meteo_warnings(self):
        """Pobiera ostrzeżenia z endpointu wskazanego w dokumentacji."""
        # POPRAWKA: Używamy dokładnie tego adresu ze zrzutu ekranu
        # Pełny adres wyjdzie: https://danepubliczne.imgw.pl/api/data/meteo/worn
        return await self._get("/meteo/worn", "API Ostrzeżeń")

    async def _get(self, endpoint: str, service_name: str):
        try:
            response = await self.async_client.get(endpoint)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Czasem IMGW zwraca 404 jak nie ma danych dla stacji
                raise HTTPException(status_code=404, detail=f"Brak danych dla tego zapytania.")
            raise HTTPException(status_code=e.response.status_code, detail=f"Błąd {service_name}: {e.response.text}")
        except Exception as e:
            print(f"Błąd połączenia z {service_name}: {e}")
            raise HTTPException(status_code=503, detail=f"Serwis {service_name} jest niedostępny.")