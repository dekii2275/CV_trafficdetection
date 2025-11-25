from fastapi import APIRouter
from fastapi.responses import JSONResponse
from api import state
import asyncio
from services.AnalyzeOnRoadForMultiProcessing import AnalyzeOnRoadForMultiprocessing
from fastapi.responses import Response
from fastapi import WebSocket, WebSocketDisconnect
from utils.jwt_handler import get_current_user, get_current_user_ws
from fastapi import Depends
from utils.transport_utils import enrich_info_with_thresholds

router = APIRouter()

@router.on_event("startup")
def start_up():
    if state.analyzer is None:
        state.analyzer = AnalyzeOnRoadForMultiprocessing()
        state.analyzer.run_multiprocessing()

@router.get(
    path='/roads_name',
    summary="Lấy danh sách tên đường",
    description="API trả về danh sách tên các tuyến đường đang được giám sát trong hệ thống. Endpoint này KHÔNG yêu cầu xác thực JWT."
)
async def get_road_names():
    """
    API trả về danh sách tên các tuyến đường (KHÔNG xác thực JWT).
    Endpoint này là public để frontend có thể load danh sách đường trước khi user login.
    """
    return JSONResponse(content={"road_names": state.analyzer.names})

@router.websocket(
    "/ws/frames/{road_name}",
    name="WebSocket trả về frame hình ảnh tuyến đường, có xác thực qua header, cookie, query params",
    )
async def websocket_frames(
    websocket: WebSocket, 
    road_name: str,
    current_user = Depends(get_current_user_ws)
):
    """
    WebSocket endpoint để stream video frames của tuyến đường theo thời gian thực.
    
    Args:
        road_name: Tên tuyến đường cần xem
        current_user: User đã được xác thực (tự động inject bởi FastAPI)
        
    Authentication:
        Yêu cầu token qua query params (?token=...), cookie (access_token), hoặc header (Authorization: Bearer ...)
    """
    await websocket.accept()
    
    try:
        while True:
            frame_bytes = await asyncio.to_thread(state.analyzer.get_frame_road, road_name)
            await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(1/30)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(e)
        await websocket.close()
        
@router.websocket(
    "/ws/info/{road_name}",
    name="WebSocket trả về thông tin phương tiện tuyến đường có xác thực qua header, cookie, query params",
)
async def websocket_info(
    websocket: WebSocket, 
    road_name: str,
    current_user = Depends(get_current_user_ws)
):
    """
    WebSocket endpoint để nhận thông tin phương tiện của tuyến đường theo thời gian thực.
    
    Args:
        road_name: Tên tuyến đường cần xem thông tin
        current_user: User đã được xác thực (tự động inject bởi FastAPI)
        
    Authentication:
        Yêu cầu token qua query params (?token=...), cookie (access_token), hoặc header (Authorization: Bearer ...)
    
    Returns:
        JSON data chứa thông tin phương tiện, cập nhật mỗi 5 giây
    """
    await websocket.accept()
    
    try:
        while True:
            data = await asyncio.to_thread(state.analyzer.get_info_road, road_name)
            # Enrich with per-road thresholds classification when possible
            try:
                enriched = enrich_info_with_thresholds(data, road_name)
            except Exception:
                enriched = data

            await websocket.send_json(enriched)
            await asyncio.sleep(1/50)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"detail": f"Internal error: {str(e)}"})
        await websocket.close()

@router.get(
    path='/info/{road_name}',
    summary="Lấy thông tin phương tiện trên đường",
    description="API trả về thông tin phương tiện của tuyến đường (số lượng xe, tốc độ trung bình, v.v.). Endpoint này KHÔNG yêu cầu xác thực JWT."
)
async def get_info_road(road_name: str):
    """
    API trả về thông tin phương tiện của tuyến đường road_name (KHÔNG xác thực JWT).
    """
    data = await asyncio.to_thread(state.analyzer.get_info_road, road_name)
    if data is None:
        return JSONResponse(content={
            "Lỗi: Dữ liệu bị lỗi, kiểm tra road_services"
            }, status_code=500)
    # Enrich with per-road thresholds classification when possible
    try:
        enriched = enrich_info_with_thresholds(data, road_name)
    except Exception:
        enriched = data

    return JSONResponse(content=enriched)

@router.get(
    path='/frames/{road_name}',
    summary="Lấy frame hình ảnh của đường (có xác thực)",
    description="API trả về frame hình ảnh (JPEG) hiện tại của tuyến đường. Yêu cầu xác thực JWT qua Authorization header, cookie, hoặc query parameter (?token=...)."
)
async def get_frame_road(road_name: str, current_user=Depends(get_current_user)):
    """
    Lấy frame hình ảnh hiện tại của tuyến đường (yêu cầu xác thực).
    
    Args:
        road_name: Tên tuyến đường
        current_user: User đã được xác thực (tự động inject bởi FastAPI)
    
    Authentication:
        Token có thể được gửi qua: OAUTH2
    
    Returns:
        Response: Image JPEG của frame hiện tại
    """
    frame_bytes = await asyncio.to_thread(state.analyzer.get_frame_road, road_name)
    if frame_bytes is None:
        return JSONResponse(
            content={"error": "Lỗi: Dữ liệu bị lỗi, kiểm tra core"},
            status_code=500
        )
    return Response(content=frame_bytes, media_type="image/jpeg")


@router.get(
    path='/frames_no_auth/{road_name}',
    summary="Lấy frame hình ảnh (không xác thực)",
    description="API trả về frame hình ảnh (JPEG) hiện tại của tuyến đường. Endpoint này KHÔNG yêu cầu xác thực JWT - dùng cho mục đích demo hoặc public."
)   
async def get_frame_road_no_auth(road_name: str):
    frame_bytes = await asyncio.to_thread(state.analyzer.get_frame_road, road_name)
    if frame_bytes is None:
        return JSONResponse(
            content={"error": "Lỗi: Dữ liệu bị lỗi, kiểm tra core"},
            status_code=500
        )
    return Response(content=frame_bytes, media_type="image/jpeg")