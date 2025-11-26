from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
import asyncio
from app.api import state
from app.core.config import settings_metric_transport
from app.services.road_services.AnalyzeOnRoad import AnalyzeOnRoad
from app.utils.transport_utils import enrich_info_with_thresholds
import threading
import traceback

router = APIRouter()


def start_analyzer_single_thread():
    if state.analyzer is not None:
        print("Analyzer đã được khởi tạo trước đó → bỏ qua.")
        return

    print("Khởi tạo Analyzer (single-thread)...")

    try:
        analyzer = AnalyzeOnRoad(
            path_video=settings_metric_transport.PATH_VIDEOS[0],
            meter_per_pixel=settings_metric_transport.METER_PER_PIXELS[0],
            region=settings_metric_transport.REGIONS[0],
            show=False
        )

        state.analyzer = analyzer

        worker = threading.Thread(
            target=analyzer.process_on_single_video,
            daemon=False
        )
        worker.start()

        state.worker_thread = worker   

        print("Analyzer đã chạy trong background thread.")

    except Exception as e:
        print("Lỗi khi khởi tạo Analyzer:", e)
        traceback.print_exc()
        state.analyzer = None

@router.on_event("startup")
def startup_event():
    """
    Sự kiện startup của FastAPI.
    """
    start_analyzer_single_thread()

@router.on_event("shutdown")
def shutdown_event():
    print("FastAPI shutdown → chuẩn bị dừng Analyzer...")

    if state.analyzer:
        try:
            state.analyzer.stop()    
            print("Đã bật stop_flag cho Analyzer.")
        except:
            pass
        
    if hasattr(state, "worker_thread"):
        t = state.worker_thread
        if t.is_alive():
            print("Đang chờ thread xử lý livestream dừng...")
            t.join(timeout=5)

    print("Shutdown hoàn tất.")

@router.get("/roads_name")
async def get_road_names():
    """Trả về danh sách tên các đường."""
    return {"road_names": [state.analyzer.name]}


@router.get("/info/{road_name}")
async def get_info_road(road_name: str):
    """Lấy thông tin phương tiện."""
    data = await asyncio.to_thread(state.analyzer.get_info_road, road_name)
    if data is None:
        return JSONResponse({"error": "Không có dữ liệu"}, status_code=500)

    try:
        enriched = enrich_info_with_thresholds(data, road_name)
    except:
        enriched = data

    return JSONResponse(enriched)


@router.get("/frames/{road_name}")
async def get_frame_road(road_name: str):
    frame_bytes = await asyncio.to_thread(state.analyzer.get_frame_road, road_name)
    if frame_bytes is None:
        return JSONResponse({"error": "Không có dữ liệu"}, status_code=500)

    return Response(content=frame_bytes, media_type="image/jpeg")


@router.get("/frames_no_auth/{road_name}")
async def get_frame_no_auth(road_name: str):
    frame_bytes = await asyncio.to_thread(state.analyzer.get_frame_road, road_name)
    if frame_bytes is None:
        return JSONResponse({"error": "Không có dữ liệu"}, status_code=500)

    return Response(content=frame_bytes, media_type="image/jpeg")


# ========================== WEBSOCKETS ==========================

@router.websocket("/ws/frames/{road_name}")
async def ws_frames(websocket: WebSocket, road_name: str):
    await websocket.accept()
    try:
        while True:
            frame_bytes = await asyncio.to_thread(state.analyzer.get_frame_road, road_name)
            if frame_bytes:
                await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(1/30)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/info/{road_name}")
async def ws_info(websocket: WebSocket, road_name: str):
    await websocket.accept()
    try:
        while True:
            data = await asyncio.to_thread(state.analyzer.get_info_road, road_name)
            try:
                enriched = enrich_info_with_thresholds(data, road_name)
            except:
                enriched = data

            await websocket.send_json(enriched)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
