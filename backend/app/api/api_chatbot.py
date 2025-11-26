from app.api import state
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.schemas.ChatRequest import ChatRequest
from app.schemas.ChatResponse import ChatResponse
from app.services.chat_services.ChatBotAgent import ChatBotAgent

router = APIRouter()


@router.on_event("startup")
def start_up():
    if not hasattr(state, 'agent') or state.agent is None:
        print("Đang khởi tạo Chat Agent...")
        try:
            state.agent = ChatBotAgent()
            print("Khởi tạo Chat Agent thành công")
        except Exception as e:
            print(f"Không thể khởi tạo Chat Agent: {e}")
            state.agent = None


@router.post(
    path="/chat",
    response_model=ChatResponse,
    summary="Chat với AI Assistant",
    description="Gửi tin nhắn đến ChatBot và nhận phản hồi."
)
async def chat_no_auth(request: ChatRequest):
    data = await state.agent.get_response(request.message, id=9999)
    return ChatResponse(
        message=data["message"],
        image=data["image"]
    )


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket chat cho ChatBot.
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")

            if not user_message:
                await websocket.send_json({
                    "message": "Bạn chưa nhập tin nhắn.",
                    "image": None
                })
                continue

            response = await state.agent.get_response(user_message, id=9999)

            await websocket.send_json({
                "message": response["message"],
                "image": response["image"]
            })

    except WebSocketDisconnect:
        print("WebSocket client disconnected")

    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "message": f"Lỗi: {str(e)}",
                "image": None
            })
        except:
            pass
        await websocket.close()
