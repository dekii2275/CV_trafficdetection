from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.schemas.ChatRequest import ChatRequest
from app.schemas.ChatResponse import ChatResponse
from app.services.rag_services.ChatBotAgent import get_agent
import uuid
from typing import Dict

router = APIRouter()

# Lưu trữ sessions cho từng user
active_sessions: Dict[str, dict] = {}

@router.on_event("startup")
async def start_up():
    """Khởi tạo RAG Agent khi server start"""
    print("🚀 Initializing RAG Chat Agent...")
    try:
        agent = get_agent()
        stats = agent.get_stats()
        print(f"✅ RAG Agent initialized successfully")
        print(f"📊 Vector DB: {stats['total_documents']} documents loaded")
    except Exception as e:
        print(f"❌ Failed to initialize RAG Agent: {e}")
        raise

@router.post(
    path="/chat",
    response_model=ChatResponse,
    summary="Chat với AI về Luật Giao Thông",
    description="Gửi câu hỏi về luật giao thông và nhận câu trả lời có trích dẫn."
)
async def chat(request: ChatRequest):
    """
    Endpoint đồng bộ cho RAG chatbot
    
    Args:
        request: ChatRequest chứa message và optional session_id
    
    Returns:
        ChatResponse với câu trả lời và sources
    """
    try:
        # Get agent instance
        agent = get_agent()
        
        # Tạo hoặc lấy session_id
        session_id = getattr(request, 'session_id', None) or str(uuid.uuid4())
        
        # Lấy conversation history từ session
        conversation_history = active_sessions.get(session_id, {}).get("history", [])
        
        # Gọi RAG agent
        response = await agent.get_response(
            message=request.message,
            session_id=session_id,
            conversation_history=conversation_history
        )
        
        # Cập nhật session history
        if session_id not in active_sessions:
            active_sessions[session_id] = {"history": []}
        
        active_sessions[session_id]["history"].append({
            "role": "user",
            "content": request.message
        })
        active_sessions[session_id]["history"].append({
            "role": "assistant",
            "content": response["message"]
        })
        
        # Giới hạn history (chỉ giữ 10 tin nhắn gần nhất)
        if len(active_sessions[session_id]["history"]) > 10:
            active_sessions[session_id]["history"] = active_sessions[session_id]["history"][-10:]
        
        return ChatResponse(
            message=response["message"],
            image=response.get("image") if response.get("image") else [], 
            session_id=session_id,
            sources=response.get("sources", [])
        )
        
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý tin nhắn: {str(e)}"
        )

@router.get(
    path="/chat/stats",
    summary="Thống kê Vector Database"
)
async def get_stats():
    """Lấy thông tin về vector database"""
    try:
        agent = get_agent()
        stats = agent.get_stats()
        return {
            "vector_db": stats,
            "active_sessions": len(active_sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint cho chat real-time với streaming
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    print(f"✅ WebSocket connected: {session_id}")
    
    try:
        # Gửi session_id cho client
        await websocket.send_json({
            "type": "session_init",
            "session_id": session_id
        })
        
        # Khởi tạo session history
        if session_id not in active_sessions:
            active_sessions[session_id] = {"history": []}
        
        agent = get_agent()
        
        while True:
            # Nhận tin nhắn từ client
            data = await websocket.receive_json()
            user_message = data.get("message", "").strip()
            
            if not user_message:
                await websocket.send_json({
                    "type": "error",
                    "message": "Vui lòng nhập câu hỏi của bạn."
                })
                continue
            
            try:
                # Lấy conversation history
                conversation_history = active_sessions[session_id]["history"]
                
                # Status: đang tìm kiếm
                await websocket.send_json({
                    "type": "status",
                    "message": "🔍 Đang tìm kiếm thông tin luật giao thông..."
                })
                
                # Get response
                response = await agent.get_response(
                    message=user_message,
                    session_id=session_id,
                    conversation_history=conversation_history
                )
                
                # Cập nhật history
                active_sessions[session_id]["history"].append({
                    "role": "user",
                    "content": user_message
                })
                active_sessions[session_id]["history"].append({
                    "role": "assistant",
                    "content": response["message"]
                })
                
                # Giới hạn history
                if len(active_sessions[session_id]["history"]) > 10:
                    active_sessions[session_id]["history"] = active_sessions[session_id]["history"][-10:]
                
                # Gửi response
                await websocket.send_json({
                    "type": "complete",
                    "message": response["message"],
                    "image": response.get("image"),
                    "sources": response.get("sources", []),
                    "retrieved_docs": response.get("retrieved_docs", 0)
                })
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Lỗi: {str(e)}"
                })
    
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {session_id}")
        if session_id in active_sessions:
            del active_sessions[session_id]
    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Đã xảy ra lỗi. Vui lòng kết nối lại."
            })
        except:
            pass
    finally:
        await websocket.close()

@router.delete("/chat/session/{session_id}")
async def clear_session(session_id: str):
    """Xóa lịch sử chat của một session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Đã xóa lịch sử chat"}
    return {"message": "Session không tồn tại"}