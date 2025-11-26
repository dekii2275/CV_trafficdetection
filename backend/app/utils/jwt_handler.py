from typing import Optional, Union
from fastapi import Request, WebSocket

def extract_token(source: Union[Request, WebSocket]) -> Optional[str]:
    """
    Extract token từ Request hoặc WebSocket.
    Dùng nếu sau này bạn muốn thêm API WS có token riêng.
    """
    if not source:
        return None

    token = None
    auth_header = source.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]

    if not token:
        token = source.cookies.get("access_token")

    if not token:
        token = source.query_params.get("token")

    return token
