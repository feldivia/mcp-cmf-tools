# Instrucciones para Claude Code: MCP Server de Regulacion Financiera Chilena

> Este documento contiene las instrucciones completas para que Claude Code genere un MCP Server con tools de regulacion financiera chilena. Copia y pega cada seccion como prompt.

---

## Contexto del proyecto

Crear un MCP Server standalone usando FastMCP (Python) que exponga herramientas de consulta de regulacion financiera chilena. El servidor debe funcionar en modo stdio (para Claude Desktop, Claude Code, MCP Inspector) y en modo streamable-http (para deploy en servidor).

### Stack tecnologico

- Python 3.11+
- FastMCP (`mcp[cli]>=1.27`)
- httpx para requests HTTP async
- cachetools para cache en memoria con TTL

### Fuentes de datos reales

| Fuente | Base URL | Auth |
|---|---|---|
| API CMF v3 | `https://api.cmfchile.cl/api-sbifv3/recursos_api` | API Key gratis en api.cmfchile.cl |
| mindicador.cl | `https://mindicador.cl/api` | No requiere |
| Biblioteca del Congreso Nacional | `https://www.leychile.cl/navegar?idNorma={id}` | No requiere |
| CMF Alertas al Publico | `https://www.cmfchile.cl/portal/principal/613/w3-propertyvalue-43333.html` | No requiere |

### Restricciones de la API CMF

- Endpoint `/instituciones` no esta disponible (redirige a url_error)
- Endpoints de indicadores requieren fecha: `/dolar/{anio}/{mes}`, `/euro/{anio}/{mes}`
- `/uf` y `/utm` funcionan sin fecha
- Siempre usar `follow_redirects=True` y validar que la URL final no contenga `url_error`
- Formato: `params={"apikey": key, "formato": "json"}`

---

## Prompt 1: Estructura del proyecto

```
Crea un proyecto Python con esta estructura:

mcp-cmf-tools/
├── mcp_server.py          # Entry point FastMCP
├── mcp_tools/
│   ├── __init__.py
│   ├── cmf.py             # indicadores_cmf, alertas_fraude
│   ├── mindicador.py      # indicadores_economicos
│   └── bcn.py             # consultar_ley
├── scripts/
│   └── test_tools.py      # Test directo de cada tool
├── Dockerfile
├── pyproject.toml
├── .env.example
└── .gitignore

pyproject.toml debe tener:
- build-system con setuptools>=68.0
- [tool.setuptools.packages.find] con include = ["mcp_tools*"]
- dependencies: mcp[cli]>=1.27, httpx>=0.27, cachetools>=5.5
- requires-python >= 3.11

.env.example:
CMF_API_KEY=...
PORT=8080

.gitignore: __pycache__/, *.pyc, .env, *.egg-info/, .venv/, .claude/
```

---

## Prompt 2: mcp_tools/cmf.py

```
Crea mcp_tools/cmf.py con dos funciones async:

1. indicadores_cmf(cmf_api_key: str) -> dict
   - Consulta la API CMF v3 en https://api.cmfchile.cl/api-sbifv3/recursos_api
   - Obtiene UF (/uf), dolar (/dolar/{anio}/{mes}), euro (/euro/{anio}/{mes}), UTM (/utm)
   - IMPORTANTE: dolar y euro requieren anio y mes actuales en la URL
   - Usar httpx.AsyncClient con follow_redirects=True
   - Validar que la URL final NO contenga "url_error" (indica endpoint roto)
   - Params: {"apikey": cmf_api_key, "formato": "json"}
   - Tomar el ultimo valor de la lista retornada (vals[-1])
   - Retornar dict con valor y fecha por cada indicador
   - Cache con TTLCache de cachetools (24h)

2. alertas_fraude(busqueda: str) -> dict
   - Consulta en vivo la pagina de alertas CMF:
     https://www.cmfchile.cl/portal/principal/613/w3-propertyvalue-43333.html
   - Busca el termino en el HTML de la pagina (case insensitive)
   - Retorna si fue encontrada, nivel de riesgo, URL de consulta y fuente
   - Cache con TTLCache (24h)
   - No usa datos ficticios ni JSON locales
```

---

## Prompt 3: mcp_tools/mindicador.py

```
Crea mcp_tools/mindicador.py con una funcion async:

indicadores_economicos() -> dict
- GET a https://mindicador.cl/api (sin autenticacion)
- Extraer: uf, dolar, euro, utm, ipc, imacec, tpm, bitcoin
- De cada indicador tomar: nombre, valor, unidad_medida
- Cache con TTLCache (1 hora)
- Retornar dict con los indicadores y fuente "mindicador.cl (API abierta)"
```

---

## Prompt 4: mcp_tools/bcn.py

```
Crea mcp_tools/bcn.py con:

Un diccionario NORMAS con IDs de leyes financieras clave:
- ley_fintech: "1187323" (Ley 21.521)
- sernac_financiero: "1040348" (Ley 20.555)
- consumidor: "141599" (Ley 19.496)
- datos_personales: "141763" (Ley 19.628)

Una funcion async consultar_ley(id_norma: str) -> dict:
- Construye URL: https://www.leychile.cl/navegar?idNorma={id_norma}
- Hace GET con follow_redirects=True
- Si status 200, retorna: id_norma, url, disponible=True, fuente, nota
- Si falla, retorna error
- Sin cache (las leyes no cambian frecuentemente y la consulta es ligera)
```

---

## Prompt 5: mcp_server.py

```
Crea mcp_server.py como entry point del MCP server usando FastMCP:

from mcp.server.fastmcp import FastMCP

Configuracion de FastMCP:
- name: "regulbot-mcp"
- instructions: "Regulacion financiera chilena: CMF, BCN, mindicador"
- host: "0.0.0.0"
- port: int(os.getenv("PORT", "8080"))
- stateless_http: True
- streamable_http_path: "/"

CMF_API_KEY se lee de os.getenv("CMF_API_KEY", "")

Registrar 4 tools con @mcp.tool():

1. cmf_indicadores() -> dict
   Descripcion: "Obtiene indicadores financieros oficiales: UF, dolar, euro, UTM.
   Datos de la API CMF actualizados diariamente."

2. cmf_alertas(busqueda: str) -> dict
   Descripcion: "Busca en las alertas de fraude publicadas por la CMF.
   Verifica si un nombre, URL o app aparece como entidad no autorizada.
   Ejemplo: cmf_alertas("inversion garantizada")"

3. chile_indicadores_economicos() -> dict
   Descripcion: "Obtiene indicadores economicos actuales de Chile.
   UF, dolar, euro, UTM, IPC, IMACEC, TPM, bitcoin.
   Fuente: mindicador.cl, actualizado cada hora, sin autenticacion."

4. chile_consultar_ley(id_norma: str) -> dict
   Descripcion: "Consulta una ley chilena en la Biblioteca del Congreso Nacional.
   IDs utiles: 1187323 (Ley Fintech), 1040348 (SERNAC Financiero),
   141599 (Consumidor), 141763 (Datos Personales)."

Registrar 3 prompts con @mcp.prompt():

1. verificar_empresa(nombre: str) -> str
   "Verifica si una empresa financiera es legitima y segura."
   Genera texto que pide usar cmf_alertas para buscar en alertas de fraude
   y dar un resumen claro.

2. resumen_economico() -> str
   "Genera un resumen del panorama economico actual de Chile."
   Genera texto que pide usar chile_indicadores_economicos y cmf_indicadores
   y presentar la info de forma simple.

3. explicar_ley(id_norma: str) -> str
   "Explica una ley chilena en lenguaje simple y ciudadano."
   Genera texto que pide usar chile_consultar_ley y explicar que regula,
   a quien protege, derechos principales y acciones ciudadanas.

Al final:
if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "streamable-http"
    mcp.run(transport=transport)
```

---

## Prompt 6: Test y Dockerfile

```
Crea scripts/test_tools.py que:
- Importa las funciones directamente (sin MCP protocol)
- Ejecuta cada tool con asyncio.run()
- Imprime resultados en JSON truncado (max 300 chars)
- Lee CMF_API_KEY de variable de entorno

Crea Dockerfile:
- Base: python:3.12-slim
- Copia pyproject.toml, instala dependencias
- Copia mcp_server.py y mcp_tools/
- Expone puerto 8080
- CMD: python mcp_server.py
```

---

## Prompt 7: Probar en local

```
Prueba el MCP server:

1. Crea un entorno virtual e instala dependencias:
   python -m venv .venv
   .venv/Scripts/activate  (o source .venv/bin/activate en Linux/Mac)
   pip install -e .

2. Ejecuta el test directo:
   python scripts/test_tools.py

3. Levanta el MCP Inspector:
   npx @modelcontextprotocol/inspector python mcp_server.py stdio

4. En el inspector, prueba cada tool:
   - cmf_indicadores (sin parametros)
   - cmf_alertas con busqueda "forex"
   - chile_indicadores_economicos (sin parametros)
   - chile_consultar_ley con id_norma "1187323"

5. Prueba cada prompt:
   - verificar_empresa con nombre "CryptoChile"
   - resumen_economico (sin parametros)
   - explicar_ley con id_norma "1187323"
```

---

## Notas tecnicas importantes

### Cache
- CMF indicadores: TTLCache 24h (datos cambian 1 vez al dia)
- CMF alertas: TTLCache 24h (pagina se actualiza esporadicamente)
- mindicador.cl: TTLCache 1h (se actualiza cada hora)
- BCN leyes: sin cache (consulta ligera, datos estaticos)

### Manejo de errores
- Cada tool retorna un dict con key "error" si falla la consulta
- httpx.RequestError se captura en cada funcion
- No se lanzan excepciones al MCP server, siempre se retorna un dict

### Transportes MCP
- `python mcp_server.py` → streamable-http en puerto 8080 (para red/deploy)
- `python mcp_server.py stdio` → stdin/stdout (para Claude Desktop, Claude Code, Inspector)

### Seguridad
- Modo stdio: seguro por defecto, no abre puertos
- Modo HTTP: sin autenticacion incluida, agregar reverse proxy o middleware si se expone a internet
