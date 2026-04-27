# MCP CMF Tools — Estado del Proyecto

> Ultima actualizacion: 2026-04-27

---

## Resumen

MCP Server standalone de regulacion financiera chilena. Expone 4 tools y 3 prompts. Fuentes: API CMF (indicadores), mindicador.cl (indicadores), CMF web (alertas de fraude), leychile.cl (leyes). Se ejecuta via streamable-http o stdio.

---

## Arquitectura

```
python mcp_server.py              --> streamable-http en :8080
python mcp_server.py stdio        --> stdio (MCP Inspector / Claude Desktop)
Docker (Dockerfile)               --> Deploy en contenedor
```

---

## Componentes

### MCP Server

| Archivo | Estado | Descripcion |
|---|---|---|
| `mcp_server.py` | OK | Entry point: FastMCP con 4 tools + 3 prompts |
| `mcp_tools/cmf.py` | OK | 2 funciones: indicadores_cmf, alertas_fraude |
| `mcp_tools/mindicador.py` | OK | 1 funcion: indicadores_economicos (mindicador.cl, sin auth) |
| `mcp_tools/bcn.py` | OK | 1 funcion: consultar_ley (leychile.cl) + dict NORMAS |

### Configuracion

| Archivo | Estado | Descripcion |
|---|---|---|
| `pyproject.toml` | OK | Dependencias: mcp, httpx, cachetools |
| `Dockerfile` | OK | Deploy standalone del MCP server |
| `.env.example` | OK | Template de variables de entorno |

### Scripts

| Archivo | Estado | Descripcion |
|---|---|---|
| `scripts/test_tools.py` | OK | Test directo de cada tool async |

---

## Tools MCP (4)

1. **cmf_indicadores()** — UF, dolar, euro, UTM desde API CMF (requiere API key)
2. **cmf_alertas(busqueda)** — Busca en alertas de fraude CMF (scraping web)
3. **chile_indicadores_economicos()** — Indicadores desde mindicador.cl (sin auth)
4. **chile_consultar_ley(id_norma)** — Consulta leyes en leychile.cl (sin auth)

## Prompts MCP (3)

1. **verificar_empresa(nombre)** — Busca en alertas de fraude CMF
2. **resumen_economico()** — Panorama economico completo de Chile
3. **explicar_ley(id_norma)** — Explica una ley en lenguaje ciudadano

---

## Como Ejecutar

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu CMF_API_KEY

# 2. Activar entorno
source .venv/Scripts/activate

# 3. Ejecutar MCP server
python mcp_server.py                    # streamable-http en :8080
python mcp_server.py stdio              # modo stdio

# 4. Testear con MCP Inspector
npx @modelcontextprotocol/inspector python mcp_server.py stdio
```
