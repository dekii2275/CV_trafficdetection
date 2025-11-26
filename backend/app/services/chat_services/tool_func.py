import json
from langchain_core.tools import tool
from typing import Annotated
from app.core.config import settings_network
from app.api import state
BASE_URL = f"{settings_network.BASE_URL_API}/api/v1"

@tool
def get_roads() -> str:
    """Lấy danh sách các tuyến đường hiện có từ hệ thống.
    Trả về chuỗi JSON chứa danh sách tên các tuyến đường.
    """
    if state.analyzer is None:
        return json.dumps({"error": "Analyzer chưa được khởi tạo"}, ensure_ascii=False)
    
    road_names = state.analyzer.names
    if not road_names:
        return json.dumps({"roads": [], "message": "Không có tuyến đường nào."}, ensure_ascii=False)
    
    return json.dumps({"roads": road_names}, ensure_ascii=False)
    
@tool
def get_frame_road(road_name: Annotated[str, "Tên tuyến đường"]) -> str:
    """Lấy url bytecode cho frame (ảnh) hiện tại của tuyến đường theo tên (road_name).
    Trả về url của ảnh JPEG.
    """
    try:
        url = f"{BASE_URL}/frames_no_auth/{road_name}"
        return url
    except Exception as e:
        return f"Lỗi không xác định: {str(e)}"

@tool
def get_info_road(road_name: Annotated[str, "Tên tuyến đường"]) -> str:
    """Lấy thông tin (info) hiện tại của tuyến đường theo tên (road_name).
    Trả về chuỗi JSON chứa số lượng xe, tốc độ, v.v.
    """
    if state.analyzer is None:
        return json.dumps({"error": "Analyzer chưa được khởi tạo"}, ensure_ascii=False)
    
    data = state.analyzer.get_info_road(road_name)
    if not data:
        return json.dumps({"error": f"Không có dữ liệu cho tuyến đường '{road_name}'"}, ensure_ascii=False)
    
    return json.dumps(data, ensure_ascii=False)