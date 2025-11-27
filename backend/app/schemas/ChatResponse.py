from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ChatResponse(BaseModel):
    message: str = Field(..., description="Phản hồi của Agent dưới dạng văn bản (không được chèn thêm link của hình ảnh)")
    image: Optional[List[str]] = None
    session_id: Optional[str] = None  # THÊM
    sources: Optional[List[Dict]] = []  # THÊM
    sources: Optional[List[Dict]] = []