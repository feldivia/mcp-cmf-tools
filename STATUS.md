# RegulBot — Estado del Proyecto

> Ultima actualizacion: 2026-04-26

---

## Resumen

RegulBot es un MCP Server standalone de regulacion financiera chilena. Expone 5 tools y 3 prompts conectados a APIs reales (CMF, mindicador.cl, BCN). Se ejecuta via streamable-http o stdio.

---

## Arquitectura

```
python mcp_server.py              --> streamable-http en :8080
python mcp_server.py stdio        --> stdio (MCP Inspector / Claude Desktop)
Docker (Dockerfile.mcp)           --> Railway deploy
```

---

## Componentes

### MCP Server

| Archivo | Estado | Descripcion |
|---|---|---|
| `mcp_server.py` | OK | Entry point: FastMCP con 5 tools + 3 prompts |
| `mcp_tools/cmf.py` | OK | 3 funciones: verificar_institucion, indicadores_cmf, alertas_fraude |
| `mcp_tools/mindicador.py` | OK | 1 funcion: indicadores_economicos (mindicador.cl, sin auth) |
| `mcp_tools/bcn.py` | OK | 1 funcion: consultar_ley (leychile.cl) + dict NORMAS |

### Datos y Configuracion

| Archivo | Estado | Descripcion |
|---|---|---|
| `data/alertas_fraude.json` | OK | Alertas CMF (ejemplo) |
| `data/context.md` | OK | System prompt regulatorio |
| `pyproject.toml` | OK | Dependencias Python |
| `Dockerfile` | OK | Deploy standalone del MCP server |
| `.env.example` | OK | Template de variables de entorno |

### Scripts

| Archivo | Estado | Descripcion |
|---|---|---|
| `scripts/prepare_alerts.py` | OK | Genera alertas CMF en JSON |
| `scripts/test_tools.py` | OK | Test directo de cada tool async |

---

## Tools MCP (5)

1. **cmf_verificar_institucion(nombre)** — Verifica si una entidad esta regulada por la CMF
2. **cmf_indicadores()** — UF, dolar, euro, UTM desde API CMF
3. **cmf_alertas(busqueda)** — Busca en alertas de fraude CMF
4. **chile_indicadores_economicos()** — Indicadores desde mindicador.cl
5. **chile_consultar_ley(id_norma)** — Consulta leyes en leychile.cl/BCN

## Prompts MCP (3)

1. **verificar_empresa(nombre)** — Verifica legitimidad combinando CMF + alertas
2. **resumen_economico()** — Panorama economico completo de Chile
3. **explicar_ley(id_norma)** — Explica una ley en lenguaje ciudadano

---

## Como Ejecutar

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 2. Activar entorno
source .venv/Scripts/activate

# 3. Ejecutar MCP server
python mcp_server.py                    # streamable-http en :8080
python mcp_server.py stdio              # modo stdio

# 4. Testear con MCP Inspector
npx @modelcontextprotocol/inspector python mcp_server.py stdio
```

---

