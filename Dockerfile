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
