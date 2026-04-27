FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY mcp_server.py ./
COPY mcp_tools/ ./mcp_tools/

EXPOSE 8080
CMD ["python", "mcp_server.py"]
