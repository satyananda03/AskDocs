from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from src.schemas.chat_schema import ChatRequest
from src.core.logging import get_logger
from src.core.config import settings
from src.graph.state import RAGState
from src.infrastructure.redis import redis_client
import langwatch
from src.graph.workflow import aidocs_workflow
from src.services.history_service import ChatHistoryRedis
from langchain_core.runnables import RunnableConfig
import json
import asyncio
import uuid
import re

logger = get_logger(__name__)
router = APIRouter(tags=["aidocs-chat"])

aidocs_chat_history = ChatHistoryRedis(
    redis_instance=redis_client, 
    num_history=settings.max_loaded_history,
    key_prefix="aidocs" 
)

@router.post("/chat/stream")
async def aidocs_agent_stream(request: ChatRequest) -> StreamingResponse:
    async def stream():
        session_id = request.session_id or str(uuid.uuid4())
        with langwatch.trace(name="aidocs_agent_stream", metadata={"thread_id": session_id}) as trace:
            try:
                index_key = f"aidocs:{session_id}:index"
                page_index = await redis_client.client.get(index_key)
                # JIKA DATA TIDAK ADA INDEX di REDIS (TTL HABIS ATAU SESI SALAH)
                if not page_index:
                    logger.warning(f"Sesi {session_id} tidak ditemukan atau kadaluarsa di Redis.")
                    error_payload = {
                        "error": "Sesi dokumen sudah kadaluarsa. Silahkan upload ulang dokumen.",
                        "done": True,
                    }
                    yield f"data: {json.dumps(error_payload)}\n\n"
                    return 
                
                full_history_dicts = await aidocs_chat_history.get_full_history(session_id)
                history_messages = await aidocs_chat_history.convert_to_messages(full_history_dicts)
                initial_state = RAGState(
                    query=request.message,
                    structure=json.loads(page_index)["structure"],
                    visited_ids=[],
                    gathered_texts=[],
                    gathered_titles=[],
                    is_sufficient=False,
                    missing_info=request.message,
                    iterations=0,
                    early_stop=False,
                    answer="",
                    chat_history=history_messages,
                    _pending_node_ids=[],
                )

                trace.update(input=request.message)

                # Streaming Answer
                full_response = ""
                final_state = None
                async for chunk in aidocs_workflow.astream(initial_state, stream_mode="values", config=RunnableConfig(callbacks=[trace.get_langchain_callback()])):
                    final_state = chunk
                    answer = chunk.get("answer", "")
                    if not answer or answer == full_response:
                        continue
                    new_content = answer[len(full_response):]
                    full_response = answer
                    tokens = re.split(r'(\s+)', new_content)
                    for token in tokens:
                        if token:
                            yield f"data: {json.dumps({'content': token, 'done': False})}\n\n"
                            if not token.isspace():
                                await asyncio.sleep(0.02)

                if final_state is None:
                    final_state = initial_state

                trace.update(output=full_response)

                # Update history redis & browser
                await aidocs_chat_history.save_history(
                    session_id=session_id,
                    question=request.message,
                    answer=full_response
                )
                new_chat_history_browser = full_history_dicts + [{"question": request.message, "answer": full_response}]
                citations = final_state.get("citations", {})
                logger.info(f"CITATIONS : {citations}")
                final_chunk = {
                    "content": "",
                    "done": True,
                    "aidocs_session_id": session_id,
                    "citations": citations,
                    "history": new_chat_history_browser,
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"

            except Exception as e:
                logger.error(f"ai-docs agent stream error: {e}", exc_info=True)
                trace.update(error=str(e))
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")