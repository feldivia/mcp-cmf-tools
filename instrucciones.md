# RegulBot Demo — MCP Server + Chat Frontend

> **Scope**: Demo funcional mínima en **3-4 horas** con Claude Code.
> Un solo servicio Python con MCP server embebido + chat endpoint + frontend React.
> Deploy en Railway como un único servicio.

---

## Decisión de Arquitectura: Lo Más Simple que Funciona

```
┌─────────────────────────────────────────────────────────────────┐
│                     UN SOLO SERVICIO                            │
│                                                                 │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────────┐ │
│  │  React Chat   │───▶│  FastAPI       │───▶│  Anthropic API   │ │
│  │  (static)     │◀──│  /api/chat     │◀──│  Claude Sonnet    │ │
│  │               │ SSE│  (proxy)       │    │  con tool_use     │ │
│  └──────────────┘    └───────┬───────┘    └──────────────────┘ │
│                              │                                  │
│                     ┌────────▼────────┐                         │
│                     │  MCP Server     │                         │
│                     │  FastMCP        │                         │
│                     │  (embebido)     │                         │
│                     │                 │                         │
│                     │  Tools:         │                         │
│                     │  • verificar    │──▶ API CMF (REST)       │
│                     │  • indicadores  │──▶ mindicador.cl        │
│                     │  • alertas      │──▶ XLSX local           │
│                     │  • consultar_ley│──▶ BCN XML              │
│                     └─────────────────┘                         │
│                                                                 │
│  Puerto: 8080  │  Railway: 1 servicio  │  Costo: ~$5/mes       │
└─────────────────────────────────────────────────────────────────┘
```

**¿Por qué NO LangGraph para la demo?** Claude ya tiene tool_use nativo. Le pasas las tools del MCP server como function definitions, Claude decide cuáles llamar, tú ejecutas y devuelves. Menos código, menos bugs, misma demo. LangGraph es para producción con flujos complejos — para una demo de 3 minutos, es overengineering.

**¿Por qué embeber el MCP server?** FastMCP puede generar un `app` ASGI que montas dentro de FastAPI. Un solo proceso, un solo puerto, un solo deploy. El MCP server sigue siendo accesible externamente en `/mcp` para Claude Desktop o Claude Code.

---

## Estructura del Proyecto

```
regulbot/
├── pyproject.toml
├── Dockerfile
├── .env.example
│
├── server.py                    # ← ENTRY POINT: FastAPI + MCP embebido
│
├── mcp_tools/                   # ← MCP TOOLS
│   ├── __init__.py
│   ├── cmf.py                   # verificar_institucion + indicadores + alertas
│   ├── mindicador.py            # indicadores_economicos
│   └── bcn.py                   # consultar_ley
│
├── chat/                        # ← CHAT ENDPOINT
│   ├── __init__.py
│   ├── endpoint.py              # POST /api/chat con SSE
│   └── claude_bridge.py         # Puente: MCP tools → Claude tool_use
│
├── data/                        # ← DATOS ESTÁTICOS
│   ├── alertas_fraude.json      # Alertas CMF pre-procesadas
│   ├── glosario_financiero.json # Glosario CMF Educa
│   └── context.md               # System prompt + contexto regulatorio
│
├── frontend/                    # ← REACT CHAT UI
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── components/
│       │   ├── ChatWindow.jsx
│       │   ├── Message.jsx
│       │   ├── ToolBadge.jsx    # Muestra qué tool se usó
│       │   └── Welcome.jsx
│       └── hooks/
│           └── useChat.js
│
└── scripts/
    ├── prepare_alerts.py        # Convierte XLSX CMF → JSON
    └── test_tools.py            # Testea tools del MCP
```

**Total: ~15 archivos.** Eso es todo.

---

## Paso 1: MCP Server con Tools (60 min)

### `mcp_tools/cmf.py`

```python
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
```

### `mcp_tools/mindicador.py`

```python
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
```

### `mcp_tools/bcn.py`

```python
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
```

---

## Paso 2: Server Principal — FastAPI + MCP Embebido (45 min)

### `server.py`

```python
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
    print("🚀 RegulBot server starting...")
    print(f"   MCP endpoint: /mcp")
    print(f"   Chat endpoint: /api/chat")
    print(f"   CMF API key: {'✅ configured' if CMF_API_KEY else '❌ missing'}")
    yield
    print("👋 RegulBot server stopping...")


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
```

---

## Paso 3: Chat Endpoint — Puente MCP → Claude (60 min)

### `chat/claude_bridge.py`

```python
"""
Puente entre MCP tools y Claude API con tool_use.
Convierte las tools del MCP server a function definitions de Claude,
ejecuta las tool calls, y devuelve la respuesta completa.
"""
import json
import os
from pathlib import Path
from anthropic import AsyncAnthropic
from mcp_tools.cmf import verificar_institucion, indicadores_cmf, alertas_fraude
from mcp_tools.mindicador import indicadores_economicos
from mcp_tools.bcn import consultar_ley

client = AsyncAnthropic()
CMF_API_KEY = os.getenv("CMF_API_KEY", "")

# System prompt
SYSTEM_PROMPT = (Path(__file__).parent.parent / "data" / "context.md").read_text(
    encoding="utf-8"
) if (Path(__file__).parent.parent / "data" / "context.md").exists() else """
Eres RegulBot, asistente de regulación financiera chilena.
Traduces normativas complejas a lenguaje ciudadano.

REGLAS:
1. Cita siempre la fuente legal (ley, artículo, circular)
2. No inventes datos — si no sabes, dilo
3. Incluye acciones concretas que el ciudadano pueda tomar
4. Usa emojis como indicadores visuales (✅ ⚠️ ❌ 👉)
5. Máximo 300 palabras por respuesta
6. Agrega disclaimer: no eres asesor legal ni financiero

Tienes acceso a herramientas para consultar datos en tiempo real de la CMF,
indicadores económicos, alertas de fraude y leyes chilenas.
"""

# Tools como definiciones para Claude API
TOOLS = [
    {
        "name": "cmf_verificar_institucion",
        "description": (
            "Verifica si una institución financiera (banco, fintech, cooperativa) "
            "está regulada por la CMF en Chile. Retorna datos del registro oficial."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {
                    "type": "string",
                    "description": "Nombre de la institución (ej: 'Tenpo', 'Banco Falabella')",
                }
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "cmf_indicadores",
        "description": "Obtiene UF, dólar, euro y UTM actuales desde la API CMF.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "cmf_alertas",
        "description": (
            "Busca en alertas de fraude de la CMF. Verifica si un nombre o URL "
            "aparece como entidad no autorizada o denunciada por estafa."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "busqueda": {
                    "type": "string",
                    "description": "Nombre, URL o app a verificar",
                }
            },
            "required": ["busqueda"],
        },
    },
    {
        "name": "chile_indicadores_economicos",
        "description": (
            "Obtiene indicadores económicos actuales de Chile: "
            "UF, dólar, euro, UTM, IPC, IMACEC, TPM. Fuente: mindicador.cl."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "chile_consultar_ley",
        "description": (
            "Consulta una ley chilena. IDs: 1187323 (Ley Fintech), "
            "1040348 (SERNAC Financiero), 141599 (Consumidor), 141763 (Datos Personales)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id_norma": {
                    "type": "string",
                    "description": "ID de la norma en leychile.cl",
                }
            },
            "required": ["id_norma"],
        },
    },
]

# Dispatcher: ejecuta la tool correspondiente
TOOL_DISPATCH = {
    "cmf_verificar_institucion": lambda args: verificar_institucion(args["nombre"], CMF_API_KEY),
    "cmf_indicadores": lambda args: indicadores_cmf(CMF_API_KEY),
    "cmf_alertas": lambda args: alertas_fraude(args["busqueda"]),
    "chile_indicadores_economicos": lambda args: indicadores_economicos(),
    "chile_consultar_ley": lambda args: consultar_ley(args["id_norma"]),
}


async def chat_with_tools(user_message: str, history: list[dict] | None = None):
    """
    Envía mensaje a Claude con tools, ejecuta tool calls, retorna respuesta.
    Genera eventos SSE para streaming al frontend.
    """
    messages = []

    # Agregar historial
    if history:
        for msg in history[-10:]:  # Últimos 10 mensajes
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    # Llamada inicial a Claude
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )

    # Loop de tool use (máximo 3 iteraciones)
    tools_used = []
    for _ in range(3):
        if response.stop_reason != "tool_use":
            break

        # Encontrar tool_use blocks
        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_blocks:
            break

        # Ejecutar cada tool
        tool_results = []
        for block in tool_blocks:
            tool_name = block.name
            tool_input = block.input

            # Yield evento de tool en uso
            tools_used.append({"name": tool_name, "input": tool_input})

            # Ejecutar la tool
            if tool_name in TOOL_DISPATCH:
                try:
                    result = await TOOL_DISPATCH[tool_name](tool_input)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"Tool '{tool_name}' no encontrada"}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        # Enviar resultados a Claude para que genere respuesta final
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

    # Extraer texto final
    final_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_text += block.text

    return {
        "response": final_text,
        "tools_used": tools_used,
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
```

### `chat/endpoint.py`

```python
"""SSE endpoint para el chat."""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from chat.claude_bridge import chat_with_tools

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """Chat con RegulBot. Retorna SSE con progreso y respuesta."""

    async def stream():
        yield f"data: {json.dumps({'type': 'status', 'message': 'Procesando...'})}\n\n"

        try:
            result = await chat_with_tools(req.message, req.history)

            # Enviar tools usadas
            for tool in result.get("tools_used", []):
                yield f"data: {json.dumps({'type': 'tool', 'name': tool['name'], 'input': tool['input']})}\n\n"

            # Enviar respuesta
            yield f"data: {json.dumps({'type': 'response', 'content': result['response'], 'tools_used': result['tools_used'], 'usage': result['usage']})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
```

---

## Paso 4: Frontend React (60 min)

### `frontend/src/App.jsx`

```jsx
import { useState } from "react";
import ChatWindow from "./components/ChatWindow";
import Welcome from "./components/Welcome";

export default function App() {
  const [started, setStarted] = useState(false);
  const [initialQ, setInitialQ] = useState("");

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {!started ? (
        <Welcome onSelect={(q) => { setInitialQ(q); setStarted(true); }} />
      ) : (
        <ChatWindow initialQuestion={initialQ} />
      )}
    </div>
  );
}
```

### `frontend/src/components/Welcome.jsx`

```jsx
const suggestions = [
  { emoji: "🏦", text: "¿Tenpo está regulada?" },
  { emoji: "💰", text: "¿Cuánto vale la UF hoy?" },
  { emoji: "⚠️", text: "Me llegó un SMS sospechoso de mi banco" },
  { emoji: "📋", text: "¿Qué derechos tengo con mi tarjeta de crédito?" },
];

export default function Welcome({ onSelect }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">RegulBot</h1>
        <p className="text-gray-500 text-sm max-w-md">
          Traductor de regulación financiera chilena.
          Conectado en tiempo real con la CMF, SII y BCN.
        </p>
        <div className="flex gap-2 justify-center mt-3">
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
            MCP Server activo
          </span>
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
            5 tools disponibles
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s.text)}
            className="text-left p-4 bg-white border border-gray-200 rounded-xl
                       hover:border-blue-300 hover:shadow-sm transition-all text-sm"
          >
            <span className="text-lg mr-2">{s.emoji}</span>
            {s.text}
          </button>
        ))}
      </div>
    </div>
  );
}
```

### `frontend/src/components/ChatWindow.jsx`

```jsx
import { useState, useEffect, useRef } from "react";
import Message from "./Message";
import ToolBadge from "./ToolBadge";

export default function ChatWindow({ initialQuestion }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTools, setActiveTools] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (initialQuestion) sendMessage(initialQuestion);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeTools]);

  async function sendMessage(text) {
    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setActiveTools([]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: messages.slice(-10),
        }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === "tool") {
              setActiveTools((prev) => [...prev, data]);
            }

            if (data.type === "response") {
              setMessages((prev) => [
                ...prev,
                {
                  role: "assistant",
                  content: data.content,
                  tools: data.tools_used || [],
                  usage: data.usage,
                },
              ]);
              setActiveTools([]);
            }

            if (data.type === "error") {
              setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `Error: ${data.message}`, error: true },
              ]);
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error de conexión.", error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col max-w-2xl mx-auto w-full">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-white flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
          R
        </div>
        <div>
          <div className="font-semibold text-sm">RegulBot</div>
          <div className="text-xs text-gray-400">
            MCP: CMF · mindicador · BCN
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {/* Tool activity */}
        {activeTools.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {activeTools.map((t, i) => (
              <ToolBadge key={i} name={t.name} input={t.input} />
            ))}
          </div>
        )}

        {loading && activeTools.length === 0 && (
          <div className="text-gray-400 text-sm animate-pulse">
            Pensando...
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && input.trim() && sendMessage(input.trim())}
            placeholder="Pregunta sobre regulación financiera..."
            className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                       focus:outline-none focus:border-blue-400"
            disabled={loading}
          />
          <button
            onClick={() => input.trim() && sendMessage(input.trim())}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium
                       disabled:opacity-40 hover:bg-blue-700 transition-colors"
          >
            Enviar
          </button>
        </div>
      </div>
    </div>
  );
}
```

### `frontend/src/components/Message.jsx`

```jsx
import ToolBadge from "./ToolBadge";

export default function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white"
            : msg.error
              ? "bg-red-50 text-red-800 border border-red-200"
              : "bg-white border border-gray-200 text-gray-800"
        }`}
      >
        {/* Render markdown-like content */}
        <div className="whitespace-pre-wrap">{msg.content}</div>

        {/* Tools used */}
        {msg.tools && msg.tools.length > 0 && (
          <div className="mt-3 pt-2 border-t border-gray-100 flex flex-wrap gap-1.5">
            {msg.tools.map((t, i) => (
              <ToolBadge key={i} name={t.name} compact />
            ))}
          </div>
        )}

        {/* Token usage */}
        {msg.usage && (
          <div className="mt-1 text-xs text-gray-400">
            {msg.usage.input_tokens + msg.usage.output_tokens} tokens
          </div>
        )}
      </div>
    </div>
  );
}
```

### `frontend/src/components/ToolBadge.jsx`

```jsx
const TOOL_LABELS = {
  cmf_verificar_institucion: { icon: "🏦", label: "Verificando en CMF" },
  cmf_indicadores: { icon: "📊", label: "Indicadores CMF" },
  cmf_alertas: { icon: "🚨", label: "Alertas de fraude" },
  chile_indicadores_economicos: { icon: "💹", label: "Indicadores Chile" },
  chile_consultar_ley: { icon: "📜", label: "Consultando ley" },
};

export default function ToolBadge({ name, input, compact = false }) {
  const info = TOOL_LABELS[name] || { icon: "🔧", label: name };

  if (compact) {
    return (
      <span className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
        {info.icon} {info.label}
      </span>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 text-xs bg-amber-50 text-amber-700 border border-amber-200 px-3 py-1.5 rounded-lg animate-pulse">
      {info.icon} {info.label}
      {input && Object.keys(input).length > 0 && (
        <span className="text-amber-500">
          ({Object.values(input).join(", ")})
        </span>
      )}
    </div>
  );
}
```

---

## Paso 5: Deploy (30 min)

### `Dockerfile`

```dockerfile
# Build frontend
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Python backend + MCP
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY server.py ./
COPY mcp_tools/ ./mcp_tools/
COPY chat/ ./chat/
COPY data/ ./data/
COPY --from=frontend /app/frontend/dist ./frontend/dist

EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

### `pyproject.toml`

```toml
[project]
name = "regulbot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "anthropic>=0.40",
    "mcp[cli]>=1.27",
    "httpx>=0.27",
    "cachetools>=5.5",
    "pydantic>=2.0",
]
```

### `.env.example`

```bash
ANTHROPIC_API_KEY=sk-ant-...
CMF_API_KEY=...              # Solicitar gratis en api.cmfchile.cl
PORT=8080
```

### Deploy en Railway

```bash
# 1. Push a GitHub
git add . && git commit -m "RegulBot MVP" && git push

# 2. En Railway:
#    New Project → Deploy from GitHub repo
#    Add env vars: ANTHROPIC_API_KEY, CMF_API_KEY
#    Deploy automáticamente

# 3. Listo en: https://regulbot-xxx.up.railway.app
```

---

## Paso 6: Comandos Claude Code (Copy-Paste)

Abre Claude Code en la carpeta del proyecto y ejecuta estos prompts en orden:

```
PROMPT 1 (Scaffolding):
Crea un proyecto Python llamado regulbot con la siguiente estructura:
- server.py (FastAPI + MCP server embebido con FastMCP)
- mcp_tools/ (cmf.py, mindicador.py, bcn.py)
- chat/ (endpoint.py con SSE, claude_bridge.py)
- data/ (context.md con system prompt de regulación financiera)
- frontend/ (React + Vite + Tailwind: chat UI con Welcome, ChatWindow, Message, ToolBadge)
- Dockerfile multi-stage, pyproject.toml
Usa el código de referencia del archivo REGULBOT-MCP-DEMO.md que tengo abierto.

PROMPT 2 (Preparar datos):
Crea scripts/prepare_alerts.py que descargue los XLSX de alertas de fraude
de la CMF desde cmfchile.cl/portal/principal/613/w3-propertyvalue-43333.html
y los convierta a data/alertas_fraude.json con campos: nombre, url, tipo, fecha.
También crea data/context.md con el system prompt de RegulBot.

PROMPT 3 (Testear MCP):
Crea scripts/test_tools.py que pruebe cada tool del MCP server directamente
(sin MCP protocol, solo llamadas a las funciones async).
Prueba: verificar_institucion("Banco Falabella"), indicadores_economicos(),
consultar_ley("1187323"), alertas_fraude("inversión garantizada").

PROMPT 4 (Frontend):
Construye el frontend React con npm create vite, instala tailwindcss,
y crea los componentes: Welcome.jsx con 4 preguntas sugeridas,
ChatWindow.jsx con SSE streaming, Message.jsx con burbujas user/assistant,
ToolBadge.jsx que muestra qué MCP tool se está usando con animación pulse.

PROMPT 5 (Testear end-to-end):
Ejecuta el server con uvicorn server:app --reload --port 8080
y en otra terminal ejecuta el frontend con cd frontend && npm run dev.
Prueba las 4 preguntas de la Welcome screen y verifica que:
1. Las tools se ejecutan y muestran el ToolBadge
2. Claude genera respuestas con fuentes citadas
3. Los indicadores económicos son del día actual
```

---

## Checklist Final

```
[ ] CMF API key obtenida (gratis en api.cmfchile.cl)
[ ] ANTHROPIC_API_KEY configurada
[ ] server.py arranca sin errores en :8080
[ ] /mcp responde (testeable con MCP Inspector)
[ ] /api/health retorna las 5 tools
[ ] "¿Tenpo está regulada?" → ejecuta cmf_verificar_institucion
[ ] "¿Cuánto vale la UF?" → ejecuta chile_indicadores_economicos
[ ] "¿Es segura esta app de inversión?" → ejecuta cmf_alertas
[ ] Frontend muestra ToolBadge animado durante ejecución
[ ] Deploy en Railway funciona con HTTPS
[ ] Claude Desktop puede conectar al /mcp endpoint
```