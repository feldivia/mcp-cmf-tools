"""
RegulBot Server
FastAPI + MCP Server embebido + Chat endpoint
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

from mcp_tools.cmf import verificar_institucion, indicadores_cmf, alertas_fraude
from mcp_tools.mindicador import indicadores_economicos
from mcp_tools.bcn import consultar_ley, NORMAS
from chat.endpoint import router as chat_router

# ════════════════════════════════════════════
#  MCP SERVER
# ════════════════════════════════════════════

CMF_API_KEY = os.getenv("CMF_API_KEY", "")

mcp = FastMCP(
    "mcp-chile-finanzas",
    version="0.1.0",
    description="Regulación financiera chilena: CMF, SII, BCN, mindicador",
)


@mcp.tool()
async def cmf_verificar_institucion(nombre: str) -> dict:
    """Verifica si una institución financiera está regulada por la CMF.
    Busca en el registro oficial de bancos e instituciones financieras.
    Ejemplo: cmf_verificar_institucion("Banco Falabella")
    """
    return await verificar_institucion(nombre, CMF_API_KEY)


@mcp.tool()
async def cmf_indicadores() -> dict:
    """Obtiene indicadores financieros oficiales: UF, dólar, euro, UTM.
    Datos de la API CMF actualizados diariamente.
    """
    return await indicadores_cmf(CMF_API_KEY)


@mcp.tool()
async def cmf_alertas(busqueda: str) -> dict:
    """Busca en las alertas de fraude publicadas por la CMF.
    Verifica si un nombre, URL o app aparece como entidad no autorizada.
    Ejemplo: cmf_alertas("inversión garantizada")
    """
    return await alertas_fraude(busqueda)


@mcp.tool()
async def chile_indicadores_economicos() -> dict:
    """Obtiene indicadores económicos actuales de Chile.
    UF, dólar, euro, UTM, IPC, IMACEC, TPM, bitcoin.
    Fuente: mindicador.cl, actualizado cada hora, sin autenticación.
    """
    return await indicadores_economicos()


@mcp.tool()
async def chile_consultar_ley(id_norma: str) -> dict:
    """Consulta una ley chilena en la Biblioteca del Congreso Nacional.
    IDs útiles: 1187323 (Ley Fintech), 1040348 (SERNAC Financiero),
    141599 (Consumidor), 141763 (Datos Personales).
    """
    return await consultar_ley(id_norma)


# ════════════════════════════════════════════
#  FASTAPI APP
# ════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown."""
    print("RegulBot server starting...")
    print(f"   MCP endpoint: /mcp")
    print(f"   Chat endpoint: /api/chat")
    print(f"   CMF API key: {'configured' if CMF_API_KEY else 'missing'}")
    yield
    print("RegulBot server stopping...")


app = FastAPI(
    title="RegulBot",
    description="Traductor regulatorio ciudadano + MCP Server",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar MCP server en /mcp
mcp_app = mcp.streamable_http_app()
app.mount("/mcp", mcp_app)

# Chat endpoint
app.include_router(chat_router)


# Health check
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "regulbot",
        "mcp_endpoint": "/mcp",
        "tools": [
            "cmf_verificar_institucion",
            "cmf_indicadores",
            "cmf_alertas",
            "chile_indicadores_economicos",
            "chile_consultar_ley",
        ],
    }


# Servir frontend en producción
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
