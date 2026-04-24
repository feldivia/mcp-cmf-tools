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
