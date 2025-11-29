from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from typing import List, Dict

# Import Schemas
from app.schemas.ChatRequest import ChatRequest
from app.schemas.ChatResponse import ChatResponse

# Import Services
from app.services.rag_services.ChatBotAgent import get_agent

# Import Database & Models
from app.db.base import SessionLocal
from app.models.chat_message import ChatMessage # Đảm bảo bạn đã tạo file này ở bước trước

router = APIRouter()

# --- HELPER FUNCTIONS (Xử lý Database) ---

def get_db_history(session_id: str, limit: int = 10) -> List[Dict]:
    """
    Lấy 10 tin nhắn gần nhất từ DB để làm context cho AI
    """
    db: Session = SessionLocal()
    try:
        # Lấy tin nhắn mới nhất, sắp xếp ngược thời gian
        messages = db.query(ChatMessage)\
            .filter(ChatMessage.session_id == session_id)\
            .order_by(desc(ChatMessage.created_at))\
            .limit(limit)\
            .all()
        
        # Đảo ngược lại để đúng thứ tự thời gian (Cũ -> Mới) cho AI hiểu
        history = []
        for msg in reversed(messages):
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        return history
    except Exception as e:
        print(f"⚠️ Lỗi lấy lịch sử DB: {e}")
        return []
    finally:
        db.close()

def save_to_db(session_id: str, role: str, content: str, sources: list = None, images: list = None):
    """
    Lưu tin nhắn vào Database
    """
    db: Session = SessionLocal()
    try:
        new_msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources, # Lưu nguồn trích dẫn (cho câu trả lời của AI)
            images=images    # Lưu ảnh (nếu có)
        )
        db.add(new_msg)
        db.commit()
    except Exception as e:
        print(f"❌ Lỗi lưu DB: {e}")
        db.rollback()
    finally:
        db.close()

# --- API ENDPOINTS ---

@router.on_event("startup")
async def start_up():
    """Khởi tạo RAG Agent"""
    print("🚀 Initializing RAG Chat Agent...")
    try:
        agent = get_agent()
        stats = agent.get_stats()
        print(f"✅ RAG Agent initialized. Vector DB: {stats['total_documents']} docs")
    except Exception as e:
        print(f"❌ Failed to initialize RAG Agent: {e}")


@router.post(
    path="/chat",
    response_model=ChatResponse,
    summary="Chat với AI (Lưu DB)",
)
async def chat(request: ChatRequest):
    try:
        agent = get_agent()
        
        # 1. Xử lý Session ID
        session_id = getattr(request, 'session_id', None) or str(uuid.uuid4())
        
        # 2. Lưu câu hỏi của User vào DB NGAY LẬP TỨC
        save_to_db(session_id, "user", request.message)
        
        # 3. Lấy lịch sử từ DB để AI có ngữ cảnh
        conversation_history = get_db_history(session_id)
        
        # 4. Gọi AI xử lý
        response = await agent.get_response(
            message=request.message,
            session_id=session_id,
            conversation_history=conversation_history
        )
        
        # 5. Lưu câu trả lời của AI vào DB
        save_to_db(
            session_id, 
            "assistant", 
            response["message"], 
            sources=response.get("sources"),
            images=response.get("image")
        )
        
        return ChatResponse(
            message=response["message"],
            image=response.get("image") if response.get("image") else [], 
            session_id=session_id,
            sources=response.get("sources", [])
        )
        
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket Chat (Có lưu Database)
    """
    await websocket.accept()
    # Tạo session mới cho mỗi kết nối WS (hoặc nhận từ client nếu cần)
    session_id = str(uuid.uuid4())
    
    print(f"✅ WS Connected: {session_id}")
    
    try:
        await websocket.send_json({"type": "session_init", "session_id": session_id})
        agent = get_agent()
        
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "").strip()
            
            if not user_message: continue
            
            # 1. Lưu User Message vào DB
            save_to_db(session_id, "user", user_message)
            
            try:
                # 2. Lấy lịch sử DB
                conversation_history = get_db_history(session_id)
                
                await websocket.send_json({"type": "status", "message": "🔍 Đang tra cứu luật..."})
                
                # 3. Gọi AI
                response = await agent.get_response(
                    message=user_message,
                    session_id=session_id,
                    conversation_history=conversation_history
                )
                
                # 4. Lưu AI Message vào DB
                save_to_db(
                    session_id, 
                    "assistant", 
                    response["message"],
                    sources=response.get("sources"),
                    images=response.get("image")
                )
                
                # 5. Phản hồi Client
                await websocket.send_json({
                    "type": "complete",
                    "message": response["message"],
                    "image": response.get("image"),
                    "sources": response.get("sources", []),
                })
                
            except Exception as e:
                print(f"❌ Error processing: {e}")
                await websocket.send_json({"type": "error", "message": str(e)})
    
    except WebSocketDisconnect:
        print(f"🔌 WS Disconnected: {session_id}")
    except Exception as e:
        print(f"❌ WS Error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

# Endpoint xóa lịch sử (Optional)
@router.delete("/chat/session/{session_id}")
async def clear_session(session_id: str):
    db = SessionLocal()
    try:
        # Xóa tất cả tin nhắn của session_id này
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
        db.commit()
        return {"message": "Đã xóa lịch sử chat trong DB"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()