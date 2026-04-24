"""Tool para consultar leyes en la BCN."""
import httpx


# IDs de normas financieras clave
NORMAS = {
    "ley_fintech": "1187323",      # Ley 21.521
    "sernac_financiero": "1040348", # Ley 20.555
    "consumidor": "141599",         # Ley 19.496
    "datos_personales": "141763",   # Ley 19.628
}


async def consultar_ley(id_norma: str) -> dict:
    """Consulta una ley chilena en leychile.cl."""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            # Intentar obtener HTML de la ley (más simple que XML)
            url = f"https://www.leychile.cl/navegar?idNorma={id_norma}"
            r = await client.get(url, follow_redirects=True)

            if r.status_code == 200:
                return {
                    "id_norma": id_norma,
                    "url": url,
                    "disponible": True,
                    "fuente": "Biblioteca del Congreso Nacional (leychile.cl)",
                    "nota": "Texto completo disponible en la URL indicada.",
                }
        except httpx.RequestError as e:
            return {"error": str(e)}

    return {"id_norma": id_norma, "disponible": False}
