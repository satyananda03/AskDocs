import uuid
import os
import traceback
import shutil
import tempfile
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
import json
from src.infrastructure.redis import redis_client
from src.pageindex.indexer.build_index import build_index
from src.schemas.upload_schema import UploadResponse

router = APIRouter(tags=["aidocs-upload"])

@router.post("/upload")
async def upload_documents(background_tasks: BackgroundTasks,
                            file: UploadFile = File(...),
                            session_id: Optional[str] = Form(None)) -> UploadResponse:
    try:
        if not session_id:
            session_id = str(uuid.uuid4())
        else:
            # Jika user kirim session_id (Re-upload), bersihkan data lama dulu
            await redis_client.client.delete(f"aidocs:{session_id}:index")
            await redis_client.client.delete(f"aidocs:{session_id}:stream") 
            await redis_client.client.delete(f"aidocs:{session_id}:doc_name")

        # 2. Simpan file ke Temporary Path yang aman
        original_ext = os.path.splitext(file.filename)[-1].lower()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=original_ext)  
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()

        # AMBIL NAMA ASLI FILE DARI FRONTEND
        original_filename = file.filename

        # 3. Lempar tugas ke Background Task (Tambahkan original_filename di sini)
        background_tasks.add_task(
            build_index, 
            temp_file.name, 
            original_filename, # <--- Parameter baru yang kita tambahkan
            session_id
        )

        return UploadResponse(
            status_code = 200, 
            message = "Upload sukses, pemrosesan dimulai.", 
            session_id = session_id)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/upload/stream")
async def upload_stream(session_id: str) -> StreamingResponse:
    async def stream_task():
        last_id = "0" # Membaca Stream dari awal (mencegah pesan hilang)
        stream_key = f"aidocs:{session_id}:stream"
        try:
            while True:
                # XREAD: Block selama 2 detik menunggu event baru
                events = await redis_client.client.xread(
                    {stream_key: last_id}, 
                    count=1, 
                    block=2000
                )
                
                if events:
                    # Parse respons XREAD dari Redis
                    for _stream_name, messages in events:
                        for msg_id, msg_data in messages:
                            last_id = msg_id
                            
                            # Kirim data ke Frontend (Format SSE wajib pakai awalan 'data: ' dan diakhiri '\n\n')
                            yield f"data: {json.dumps(msg_data)}\n\n"
                            
                            # Hentikan stream jika proses selesai atau error
                            if msg_data.get("status") in ["completed", "error"]:
                                return 
                
                # Memberi napas pada event loop
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            # Terjadi jika client/browser menutup tab
            pass

    return StreamingResponse(stream_task(), media_type="text/event-stream")