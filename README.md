# MCP CMF Tools

MCP Server con herramientas de regulacion financiera chilena. Consulta indicadores economicos (CMF, mindicador.cl) y alertas de fraude.

## Tools disponibles

| Tool | Descripcion | Requiere API Key |
|---|---|---|
| `cmf_indicadores` | UF, dolar, euro, UTM desde la API CMF | Si |
| `cmf_alertas` | Busca alertas de fraude en la CMF | No |
| `chile_indicadores_economicos` | UF, dolar, IPC, TPM, bitcoin desde mindicador.cl | No |

## Prompts disponibles

| Prompt | Parametros | Descripcion |
|---|---|---|
| `verificar_empresa` | `nombre` | Verifica si una empresa aparece en alertas de fraude CMF |
| `resumen_economico` | ninguno | Panorama economico actual de Chile |

---

## Requisitos

- Python 3.11+
- API Key de la CMF (opcional, gratis en https://api.cmfchile.cl)

## Instalacion

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd mcp-cmf-tools

# Crear entorno virtual
python -m venv .venv

# Activar entorno
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Instalar dependencias
pip install -e .

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu CMF_API_KEY
```

---

## Uso local

### Opcion 1: MCP Inspector (interfaz visual)

La forma mas sencilla de probar las tools y prompts es con MCP Inspector:

```bash
npx @modelcontextprotocol/inspector python mcp_server.py stdio
```

Esto abre una interfaz web (por defecto en `http://localhost:6274`) donde puedes:

- Ver la lista de tools y prompts registrados
- Invocar cada tool con parametros de prueba
- Ver las respuestas en formato JSON

> En Windows, puede ser necesario usar la ruta completa del Python del venv:
> ```bash
> npx @modelcontextprotocol/inspector .venv/Scripts/python.exe mcp_server.py stdio
> ```

### Opcion 2: Claude Desktop

Agrega la siguiente configuracion en tu archivo `claude_desktop_config.json`:

**Ubicacion del archivo:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cmf-tools": {
      "command": "python",
      "args": ["/ruta/absoluta/al/proyecto/mcp_server.py", "stdio"],
      "env": {
        "CMF_API_KEY": "tu-api-key-aqui"
      }
    }
  }
}
```

> Reemplaza `/ruta/absoluta/al/proyecto/` con la ruta donde clonaste el repositorio.
> Si usas un entorno virtual, apunta al Python del venv en lugar de `python`.

Reinicia Claude Desktop despues de guardar el archivo. Las tools apareceran automaticamente en el chat.

### Opcion 3: Claude Code (CLI)

Agrega el MCP server en tu configuracion de Claude Code:

```bash
claude mcp add cmf-tools -- python /ruta/absoluta/al/proyecto/mcp_server.py stdio
```

O manualmente en `.claude/settings.json`:

```json
{
  "mcpServers": {
    "cmf-tools": {
      "command": "python",
      "args": ["/ruta/absoluta/al/proyecto/mcp_server.py", "stdio"],
      "env": {
        "CMF_API_KEY": "tu-api-key-aqui"
      }
    }
  }
}
```

### Opcion 4: Test directo (sin MCP)

Para probar las funciones directamente sin levantar el servidor MCP:

```bash
python scripts/test_tools.py
```

---

## Ejemplos de uso

Una vez conectado desde Claude Desktop o Claude Code, puedes hacer preguntas como:

- "Cuanto vale la UF hoy?"
- "Dame el panorama economico de Chile"
- "Busca si 'InverMax' aparece en alertas de fraude"

---

## Seguridad

### Modo local (stdio) — por defecto

En modo **stdio** el servidor se comunica unicamente por stdin/stdout con el proceso que lo invoca (Claude Desktop, Claude Code, MCP Inspector). **No abre puertos de red** y no es accesible desde fuera de tu maquina.

Este es el modo recomendado para uso personal y desarrollo.

### Variables de entorno

| Variable | Descripcion | Obligatoria |
|---|---|---|
| `CMF_API_KEY` | API Key de la CMF para indicadores financieros | No (pero `cmf_indicadores` no funcionara sin ella) |
| `PORT` | Puerto para modo HTTP (default: 8080) | No |

> La `CMF_API_KEY` se obtiene gratis en https://api.cmfchile.cl. Las demas tools funcionan sin ella.

---

## Despliegue en servidor (modo HTTP)

Para exponer el MCP server en red (uso remoto, deploy en cloud), el servidor arranca en modo **streamable-http**:

```bash
python mcp_server.py
# Escucha en http://0.0.0.0:8080
```

### Agregar autenticacion

El servidor **no incluye autenticacion por defecto**. Si lo expones en internet, debes agregar una capa de seguridad. Hay dos opciones:

#### Opcion A: Reverse proxy con autenticacion (recomendado)

Usa nginx, Caddy o un API Gateway delante del MCP server que valide un token o API key antes de pasar la request.

Ejemplo con Caddy:

```
mcp.tudominio.com {
    @auth {
        header Authorization "Bearer {env.MCP_AUTH_TOKEN}"
    }
    handle @auth {
        reverse_proxy localhost:8080
    }
    respond 401
}
```

#### Opcion B: Autenticacion en el codigo

Modifica `mcp_server.py` para validar un header de autenticacion. Ejemplo basico:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if MCP_AUTH_TOKEN:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if token != MCP_AUTH_TOKEN:
                return JSONResponse({"error": "No autorizado"}, status_code=401)
        return await call_next(request)

# Agregar antes de mcp.run():
app = mcp.streamable_http_app()
app.add_middleware(AuthMiddleware)
```

Y definir el token en las variables de entorno:

```bash
MCP_AUTH_TOKEN=un-token-secreto-aqui
```

### Deploy con Docker

```bash
docker build -t mcp-cmf-tools .
docker run -p 8080:8080 -e CMF_API_KEY=tu-key -e MCP_AUTH_TOKEN=tu-token mcp-cmf-tools
```

### Conectar un cliente remoto al servidor HTTP

Una vez desplegado, los clientes MCP pueden conectarse apuntando a la URL del servidor en lugar de usar stdio:

```json
{
  "mcpServers": {
    "cmf-tools": {
      "url": "https://mcp.tudominio.com",
      "headers": {
        "Authorization": "Bearer tu-token-aqui"
      }
    }
  }
}
```

---

## Estructura del proyecto

```
mcp-cmf-tools/
├── mcp_server.py          # Entry point: FastMCP (3 tools + 2 prompts)
├── mcp_tools/
│   ├── cmf.py             # indicadores_cmf, alertas_fraude
│   └── mindicador.py      # indicadores_economicos
├── scripts/
│   └── test_tools.py      # Test directo de las tools
├── Dockerfile             # Deploy en contenedor
├── pyproject.toml         # Dependencias Python
├── .env.example           # Template de variables de entorno
└── .gitignore
```

## Fuentes de datos

| Fuente | URL | Autenticacion |
|---|---|---|
| API CMF | https://api.cmfchile.cl | API Key (gratis) |
| mindicador.cl | https://mindicador.cl/api | No requiere |
| CMF Alertas | https://www.cmfchile.cl | No requiere |
