"""Tools para la API CMF."""
import httpx
from datetime import datetime
from cachetools import TTLCache

_cache = TTLCache(maxsize=200, ttl=86400)  # 24h
CMF_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"


async def indicadores_cmf(cmf_api_key: str) -> dict:
    """Obtiene UF, dolar, euro, UTM desde la API CMF."""
    if "ind" in _cache:
        return _cache["ind"]

    now = datetime.now()
    year, month = now.year, f"{now.month:02d}"

    endpoints = {
        "uf": "/uf",
        "dolar": f"/dolar/{year}/{month}",
        "euro": f"/euro/{year}/{month}",
        "utm": "/utm",
    }

    result = {}
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for name, ep in endpoints.items():
            try:
                r = await client.get(
                    f"{CMF_BASE}{ep}",
                    params={"apikey": cmf_api_key, "formato": "json"},
                )
                if r.status_code == 200 and "url_error" not in str(r.url):
                    vals = list(r.json().values())[0]
                    if isinstance(vals, list) and vals:
                        last = vals[-1]
                        result[name] = {"valor": last.get("Valor"), "fecha": last.get("Fecha")}
            except (httpx.RequestError, Exception):
                result[name] = {"error": "no disponible"}

    result["fuente"] = "API CMF (api.cmfchile.cl)"
    _cache["ind"] = result
    return result


async def alertas_fraude(busqueda: str) -> dict:
    """Busca en alertas de fraude publicadas por la CMF (consulta en vivo)."""
    key = f"alertas:{busqueda.lower()}"
    if key in _cache:
        return _cache[key]

    CMF_ALERTAS_URL = "https://www.cmfchile.cl/portal/principal/613/w3-propertyvalue-43333.html"

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            r = await client.get(CMF_ALERTAS_URL)
            if r.status_code != 200:
                return {
                    "error": f"CMF respondio con status {r.status_code}",
                    "url_consulta": CMF_ALERTAS_URL,
                }

            html = r.text.lower()
            termino = busqueda.lower()
            encontrada = termino in html

            result = {
                "busqueda": busqueda,
                "encontrada_en_pagina": encontrada,
                "nivel_riesgo": "ALTO — aparece en pagina de alertas CMF" if encontrada else "No encontrada en alertas CMF",
                "url_consulta": CMF_ALERTAS_URL,
                "nota": (
                    "Se busco el termino en la pagina oficial de alertas de la CMF. "
                    "Para verificacion completa, revisar directamente en el sitio."
                ),
                "fuente": "CMF — Alertas al Publico (cmfchile.cl)",
            }
            _cache[key] = result
            return result

        except httpx.RequestError as e:
            return {"error": f"Error conectando con CMF: {e}", "url_consulta": CMF_ALERTAS_URL}
