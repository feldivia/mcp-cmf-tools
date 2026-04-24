"""Tool para mindicador.cl — sin autenticación."""
import httpx
from cachetools import TTLCache

_cache = TTLCache(maxsize=1, ttl=3600)  # 1h


async def indicadores_economicos() -> dict:
    """Obtiene indicadores económicos de Chile en tiempo real."""
    if "data" in _cache:
        return _cache["data"]

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get("https://mindicador.cl/api")
            if r.status_code == 200:
                raw = r.json()
                result = {}
                for key in ["uf", "dolar", "euro", "utm", "ipc", "imacec", "tpm", "bitcoin"]:
                    if key in raw:
                        result[key] = {
                            "nombre": raw[key].get("nombre", key),
                            "valor": raw[key].get("valor"),
                            "unidad": raw[key].get("unidad_medida", ""),
                        }
                result["fuente"] = "mindicador.cl (API abierta)"
                _cache["data"] = result
                return result
        except httpx.RequestError as e:
            return {"error": str(e)}

    return {"error": "No se pudo conectar"}
