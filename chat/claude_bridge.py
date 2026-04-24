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
