from pydantic import BaseModel

class UploadResponse(BaseModel):
    status_code : int
    message : str
    session_id : str