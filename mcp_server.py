"""
RegulBot MCP Server
Local:   python mcp_server.py          (streamable-http en puerto 8080)
Stdio:   python mcp_server.py stdio    (para MCP Inspector / mcp dev)
Deploy:  Railway con Dockerfile.mcp
"""
import os
import sys

from mcp.server.fastmcp import FastMCP

from mcp_tools.cmf import indicadores_cmf, alertas_fraude
from mcp_tools.mindicador import indicadores_economicos
from mcp_tools.bcn import consultar_ley

CMF_API_KEY = os.getenv("CMF_API_KEY", "")

mcp = FastMCP(
    "regulbot-mcp",
    instructions="Regulacion financiera chilena: CMF, BCN, mindicador",
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8080")),
    stateless_http=True,
    streamable_http_path="/",
)


# ════════════════════════════════════════════
#  TOOLS
# ════════════════════════════════════════════


@mcp.tool()
async def cmf_indicadores() -> dict:
    """Obtiene indicadores financieros oficiales: UF, dolar, euro, UTM.
    Datos de la API CMF actualizados diariamente.
    """
    return await indicadores_cmf(CMF_API_KEY)


@mcp.tool()
async def cmf_alertas(busqueda: str) -> dict:
    """Busca en las alertas de fraude publicadas por la CMF.
    Verifica si un nombre, URL o app aparece como entidad no autorizada.
    Ejemplo: cmf_alertas("inversion garantizada")
    """
    return await alertas_fraude(busqueda)


@mcp.tool()
async def chile_indicadores_economicos() -> dict:
    """Obtiene indicadores economicos actuales de Chile.
    UF, dolar, euro, UTM, IPC, IMACEC, TPM, bitcoin.
    Fuente: mindicador.cl, actualizado cada hora, sin autenticacion.
    """
    return await indicadores_economicos()


@mcp.tool()
async def chile_consultar_ley(id_norma: str) -> dict:
    """Consulta una ley chilena en la Biblioteca del Congreso Nacional.
    IDs utiles: 1187323 (Ley Fintech), 1040348 (SERNAC Financiero),
    141599 (Consumidor), 141763 (Datos Personales).
    """
    return await consultar_ley(id_norma)


# ════════════════════════════════════════════
#  PROMPTS
# ════════════════════════════════════════════


@mcp.prompt()
def verificar_empresa(nombre: str) -> str:
    """Verifica si una empresa financiera es legitima y segura."""
    return (
        f"Necesito verificar si '{nombre}' es una empresa financiera legitima en Chile. "
        f"Usa cmf_alertas para buscar si aparece en alertas de fraude. "
        f"Dame un resumen claro indicando si es segura o no."
    )


@mcp.prompt()
def resumen_economico() -> str:
    """Genera un resumen del panorama economico actual de Chile."""
    return (
        "Dame un resumen del panorama economico actual de Chile. "
        "Usa chile_indicadores_economicos para obtener UF, dolar, euro, IPC, TPM, etc. "
        "Tambien usa cmf_indicadores para los datos oficiales de la CMF. "
        "Presenta la informacion de forma clara y simple para un ciudadano comun."
    )


@mcp.prompt()
def explicar_ley(id_norma: str) -> str:
    """Explica una ley chilena en lenguaje simple y ciudadano."""
    return (
        f"Usa chile_consultar_ley con id_norma '{id_norma}' para obtener la referencia. "
        f"Luego explicame en lenguaje simple y ciudadano: "
        f"que regula esta ley, a quien protege, cuales son los derechos principales, "
        f"y que puede hacer un ciudadano si se vulneran sus derechos. "
        f"IDs utiles: 1187323 (Ley Fintech), 1040348 (SERNAC Financiero), "
        f"141599 (Consumidor), 141763 (Datos Personales)."
    )


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "streamable-http"
    mcp.run(transport=transport)
