import json
import os
import asyncio
from src.services.llm_service import get_llm
from types import SimpleNamespace as config
from src.core.logging import get_logger
from src.core.stream import stream_event
from src.infrastructure.redis import redis_client
from src.pageindex.indexer.page_index import page_index_main

logger = get_logger(__name__)

llm = get_llm(
    model_id="amazon.nova-pro-v1:0",
    max_tokens=1500,        
    streaming=False,
    temperature=0.0  
)

opt = config(
    toc_check_page_num=15,
    max_page_num_each_node=10,
    max_token_num_each_node=15000,
    if_add_node_id="yes",
    if_add_node_summary="yes",
    if_add_doc_description="no",
    if_add_node_text="yes",
)

async def build_index(file_path: str, original_filename: str, session_id: str):
    try:
        loop = asyncio.get_event_loop()
        index_task = loop.run_in_executor(None, page_index_main, file_path, opt, llm)
        # Variasi pesan agar UI terlihat hidup
        loading_messages = [
            "Membaca dan mengurai halaman dokumen...",
            "Membaca dan mengurai halaman dokumen...",                                      
            "Membangun struktur hierarki dokumen...",        
            "Membuat summary dokumen...",        
            "Harap tunggu, proses masih berjalan...", 
        ]
        counter = 0
        while not index_task.done():
            msg = loading_messages[counter % len(loading_messages)]
            await stream_event(session_id, "extracting", msg)
            for _ in range(4):
                if index_task.done(): break
                await asyncio.sleep(1)
            counter += 1
        result = index_task.result() # ambil hasil
        await stream_event(session_id, "indexing", "Menyimpan table of content...")
        # 1. Simpan index (data berat)
        index_key = f"aidocs:{session_id}:index"
        await redis_client.client.setex(index_key, 86400, json.dumps(result))
        # 2. Simpan nama dokumen (data ringan)
        doc_name_key = f"aidocs:{session_id}:doc_name"
        await redis_client.client.setex(doc_name_key, 86400, original_filename)
        
        await stream_event(session_id, "completed", "Dokumen siap digunakan!")

    except Exception as e:
        logger.error(f"Gagal memproses dokumen {session_id}: {str(e)}")
        await stream_event(session_id, "error", f"Terjadi kesalahan sistem: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)