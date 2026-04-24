# RegulBot — Estado del Proyecto

> Última actualización: 2026-04-21

---

## Resumen

RegulBot es un traductor de regulación financiera chilena con MCP Server embebido + chat frontend React. Un solo servicio Python (FastAPI) con 5 tools conectadas a APIs reales (CMF, mindicador.cl, BCN).

---

## Componentes Construidos

### Backend (Python/FastAPI)

| Archivo | Estado | Descripción |
|---|---|---|
| `server.py` | ✅ Creado | Entry point: FastAPI + MCP embebido en `/mcp` + health check |
| `mcp_tools/cmf.py` | ✅ Creado | 3 tools: verificar_institucion, indicadores_cmf, alertas_fraude |
| `mcp_tools/mindicador.py` | ✅ Creado | 1 tool: indicadores_economicos (mindicador.cl, sin auth) |
| `mcp_tools/bcn.py` | ✅ Creado | 1 tool: consultar_ley (leychile.cl) + dict NORMAS |
| `chat/claude_bridge.py` | ✅ Creado | Puente MCP→Claude tool_use con loop de hasta 3 iteraciones |
| `chat/endpoint.py` | ✅ Creado | POST /api/chat con SSE streaming |

### Frontend (React/Vite/Tailwind)

| Archivo | Estado | Descripción |
|---|---|---|
| `frontend/src/App.jsx` | ✅ Creado | Pantalla Welcome → ChatWindow |
| `frontend/src/components/Welcome.jsx` | ✅ Creado | 4 preguntas sugeridas con badges MCP |
| `frontend/src/components/ChatWindow.jsx` | ✅ Creado | Chat con SSE, input, scroll automático |
| `frontend/src/components/Message.jsx` | ✅ Creado | Burbujas user/assistant + tools + tokens |
| `frontend/src/components/ToolBadge.jsx` | ✅ Creado | Badge animado (pulse) por tool activa |
| `frontend/vite.config.js` | ✅ Creado | Proxy /api → localhost:8080 |
| `frontend/src/index.css` | ✅ Creado | Tailwind v4 import |

### Datos y Configuración

| Archivo | Estado | Descripción |
|---|---|---|
| `data/context.md` | ✅ Creado | System prompt regulatorio con reglas y formato |
| `data/alertas_fraude.json` | ✅ Creado | 10 alertas de ejemplo (simuladas) |
| `pyproject.toml` | ✅ Creado | Dependencias + build-system + packages |
| `Dockerfile` | ✅ Creado | Multi-stage: node (frontend) + python (backend) |
| `.env.example` | ✅ Creado | Template de variables de entorno |
| `.gitignore` | ✅ Creado | Excluye .venv, node_modules, .env, dist |

### Scripts

| Archivo | Estado | Descripción |
|---|---|---|
| `scripts/prepare_alerts.py` | ✅ Creado | Descarga/genera alertas CMF → JSON |
| `scripts/test_tools.py` | ✅ Creado | Test directo de cada tool async |

### Dependencias

| Tipo | Estado | Detalle |
|---|---|---|
| Python (.venv) | ✅ Instalado | fastapi, uvicorn, anthropic, mcp, httpx, cachetools, pydantic |
| Node (frontend) | ✅ Instalado | react 19, vite 6, tailwindcss 4, @vitejs/plugin-react |

---

## NO Construido / Pendiente

### Prioritarios (para demo funcional)

- [ ] **Configurar .env** — Crear archivo `.env` con ANTHROPIC_API_KEY y CMF_API_KEY
- [ ] **Probar backend** — Ejecutar `uvicorn server:app --reload --port 8080` y verificar /api/health
- [ ] **Probar frontend** — Ejecutar `cd frontend && npm run dev` y verificar UI
- [ ] **Test end-to-end** — Probar las 4 preguntas de Welcome y validar tool execution
- [ ] **Build frontend** — `cd frontend && npm run build` para generar dist/

### Secundarios (mejoras)

- [ ] **Alertas reales CMF** — El script prepare_alerts.py usa datos de ejemplo; conectar al XLSX real
- [ ] **Glosario financiero** — Archivo `data/glosario_financiero.json` mencionado en instrucciones pero no prioritario
- [ ] **Markdown rendering** — Message.jsx usa whitespace-pre-wrap; podría usar react-markdown
- [ ] **Hook useChat.js** — Mencionado en instrucciones, actualmente la lógica está en ChatWindow.jsx directamente

### Deploy

- [ ] **Git init + push** — Inicializar repo y subir a GitHub
- [ ] **Railway deploy** — Conectar repo, configurar env vars, deploy automático
- [ ] **Dominio/HTTPS** — Railway provee HTTPS automático

---

## Cómo Ejecutar

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 2. Backend
source .venv/Scripts/activate
uvicorn server:app --reload --port 8080

# 3. Frontend (otra terminal)
cd frontend
npm run dev
# Abre http://localhost:5173
```

---

## Arquitectura

```
React (Vite :5173) → proxy /api → FastAPI (:8080) → Claude Sonnet (tool_use) → MCP Tools
                                        ↓
                                   /mcp endpoint (para Claude Desktop/Claude Code)
```

## Tools MCP Disponibles

1. **cmf_verificar_institucion** — Verifica regulación CMF de un banco/fintech
2. **cmf_indicadores** — UF, dólar, euro, UTM desde API CMF
3. **cmf_alertas** — Busca en alertas de fraude CMF
4. **chile_indicadores_economicos** — Indicadores desde mindicador.cl
5. **chile_consultar_ley** — Consulta leyes en leychile.cl/BCN
