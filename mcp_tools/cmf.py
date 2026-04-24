"""Tools para la API CMF Bancos."""
import httpx
from cachetools import TTLCache

_cache = TTLCache(maxsize=200, ttl=86400)  # 24h
CMF_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"


async def verificar_institucion(nombre: str, cmf_api_key: str) -> dict:
    """Verifica si una institución financiera está regulada por la CMF."""
    key = f"inst:{nombre.lower()}"
    if key in _cache:
        return _cache[key]

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(
                f"{CMF_BASE}/instituciones",
                params={"apikey": cmf_api_key, "formato": "json"},
            )
            if r.status_code == 200:
                for inst in r.json().get("Instituciones", []):
                    if nombre.lower() in inst.get("NombreInstitucion", "").lower():
                        result = {
                            "encontrada": True,
                            "nombre": inst["NombreInstitucion"],
                            "tipo": "Institución Bancaria Regulada",
                            "regulador": "CMF",
                            "rut": inst.get("Rut", ""),
                            "sucursales": inst.get("CantidadSucursales", ""),
                            "sitio_web": inst.get("SitioWeb", ""),
                            "fuente": "API CMF Bancos (api.cmfchile.cl)",
                        }
                        _cache[key] = result
                        return result
        except httpx.RequestError as e:
            return {"error": f"Error conectando con CMF: {e}"}

    result = {
        "encontrada": False,
        "nombre": nombre,
        "mensaje": (
            "No encontrada en el registro de instituciones bancarias de la CMF. "
            "Esto puede significar que: (a) no es un banco, "
            "(b) opera bajo otro nombre, o (c) no está regulada. "
            "Verifica en cmfchile.cl o llama al (56-2) 2887-9200."
        ),
        "fuente": "API CMF Bancos",
    }
    _cache[key] = result
    return result


async def indicadores_cmf(cmf_api_key: str) -> dict:
    """Obtiene UF, dólar, euro, UTM desde la API CMF."""
    if "ind" in _cache:
        return _cache["ind"]

    result = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name, ep in [("uf", "uf"), ("dolar", "dolar"), ("euro", "euro"), ("utm", "utm")]:
            try:
                r = await client.get(
                    f"{CMF_BASE}/{ep}",
                    params={"apikey": cmf_api_key, "formato": "json"},
                )
                if r.status_code == 200:
                    vals = list(r.json().values())[0]
                    if isinstance(vals, list) and vals:
                        result[name] = {"valor": vals[0].get("Valor"), "fecha": vals[0].get("Fecha")}
            except httpx.RequestError:
                result[name] = {"error": "no disponible"}

    result["fuente"] = "API CMF Bancos"
    _cache["ind"] = result
    return result


async def alertas_fraude(busqueda: str) -> dict:
    """Busca en alertas de fraude CMF."""
    import json
    from pathlib import Path

    alerts_path = Path(__file__).parent.parent / "data" / "alertas_fraude.json"
    if not alerts_path.exists():
        return {"encontrada": False, "error": "Base de alertas no cargada"}

    alertas = json.loads(alerts_path.read_text())
    matches = [
        a for a in alertas
        if busqueda.lower() in a.get("nombre", "").lower()
        or busqueda.lower() in a.get("url", "").lower()
    ]
    return {
        "encontrada": len(matches) > 0,
        "coincidencias": matches[:5],
        "nivel_riesgo": "ALTO — posible fraude" if matches else "sin alertas",
        "total_alertas_cmf": len(alertas),
        "fuente": "CMF — Alertas al Público",
    }
