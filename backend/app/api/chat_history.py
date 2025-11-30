from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, func, and_
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.models.chat_message import ChatMessage
from app.schemas.ChatMessage import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessageListResponse,
)
from app.db.base import get_db

router = APIRouter()



# 1) CREATE MESSAGE với Session ID

@router.post(
    "/messages",
    response_model=ChatMessageResponse,
    status_code=201,
    summary="Lưu tin nhắn chat với session tracking",
)
async def create_chat_message(
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Lưu tin nhắn chat với session_id để phân biệt các cuộc hội thoại.
    
    - Mỗi session đại diện cho 1 cuộc trò chuyện liên tục
    - session_id được tạo tự động nếu không có
    """
    # Tạo session_id mới nếu không có
    session_id = message_data.session_id if hasattr(message_data, 'session_id') else str(uuid.uuid4())
    
    new_message = ChatMessage(
        message=message_data.message,
        is_user=message_data.is_user,
        images=message_data.images,
        extra_data=message_data.extra_data,
        session_id=session_id,  # Thêm session tracking
        user_id=None  # Có thể thêm user_id sau
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    return new_message



# 2) GET CHAT HISTORY theo Session

@router.get(
    "/messages",
    response_model=List[ChatMessageListResponse],
    summary="Lấy lịch sử chat theo session",
)
async def get_chat_history(
    session_id: Optional[str] = Query(default=None, description="Session ID để lọc"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    since: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy lịch sử chat:
    - Nếu có session_id: chỉ lấy tin nhắn của session đó
    - Nếu không: lấy tất cả (dùng cho admin)
    """
    query = select(ChatMessage)

    # Lọc theo session nếu có
    if session_id:
        query = query.where(ChatMessage.session_id == session_id)

    # Lọc theo thời gian
    if since:
        query = query.where(ChatMessage.created_at > since)

    query = query.order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        ChatMessageListResponse(
            id=str(msg.id),
            text=msg.message,
            user=msg.is_user,
            time=msg.created_at.strftime("%H:%M:%S"),
            image=msg.images,
            created_at=msg.created_at.isoformat(),
            session_id=msg.session_id,  # Trả về session_id
        )
        for msg in messages
    ]



# 3) GET CONVERSATION CONTEXT (cho RAG)

@router.get(
    "/messages/context/{session_id}",
    summary="Lấy context hội thoại cho RAG",
)
async def get_conversation_context(
    session_id: str,
    last_n: int = Query(default=10, ge=1, le=50, description="Số tin nhắn gần nhất"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy N tin nhắn gần nhất của 1 session để làm context cho RAG.
    
    Dùng cho: ChatBotAgent cần lịch sử hội thoại để trả lời chính xác.
    """
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(last_n)
    )
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Đảo ngược để có thứ tự từ cũ → mới
    messages.reverse()
    
    # Format cho LLM
    context = [
        {
            "role": "user" if msg.is_user else "assistant",
            "content": msg.message,
            "timestamp": msg.created_at.isoformat()
        }
        for msg in messages
    ]
    
    return {
        "session_id": session_id,
        "message_count": len(context),
        "context": context
    }



# 4) LIST ALL SESSIONS

@router.get(
    "/sessions",
    summary="Lấy danh sách tất cả sessions",
)
async def list_sessions(
    active_only: bool = Query(default=False, description="Chỉ lấy session hoạt động trong 24h"),
    db: AsyncSession = Depends(get_db),
):
    """
    Liệt kê tất cả sessions với metadata.
    """
    # Subquery để lấy thông tin session
    query = (
        select(
            ChatMessage.session_id,
            func.min(ChatMessage.created_at).label("first_message_at"),
            func.max(ChatMessage.created_at).label("last_message_at"),
            func.count(ChatMessage.id).label("message_count")
        )
        .group_by(ChatMessage.session_id)
    )
    
    # Lọc session active trong 24h
    if active_only:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        query = query.having(func.max(ChatMessage.created_at) > cutoff)
    
    query = query.order_by(func.max(ChatMessage.created_at).desc())
    
    result = await db.execute(query)
    sessions = result.all()
    
    return {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "first_message_at": s.first_message_at.isoformat(),
                "last_message_at": s.last_message_at.isoformat(),
                "message_count": s.message_count,
                "duration_minutes": int((s.last_message_at - s.first_message_at).total_seconds() / 60)
            }
            for s in sessions
        ]
    }



# 5) DELETE SESSION

@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    summary="Xóa toàn bộ lịch sử của 1 session",
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa tất cả tin nhắn của 1 session (user muốn xóa lịch sử chat).
    """
    result = await db.execute(
        delete(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.commit()
    return None



# 6) DELETE OLD SESSIONS

@router.delete(
    "/sessions/cleanup",
    summary="Xóa sessions cũ (>30 ngày)",
)
async def cleanup_old_sessions(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa tự động sessions không hoạt động quá X ngày.
    
    Dùng cho: Scheduled job để dọn dẹp database.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Lấy các session_id cũ
    old_sessions_query = (
        select(ChatMessage.session_id)
        .group_by(ChatMessage.session_id)
        .having(func.max(ChatMessage.created_at) < cutoff_date)
    )
    
    result = await db.execute(old_sessions_query)
    old_session_ids = [row[0] for row in result.all()]
    
    if not old_session_ids:
        return {"deleted_sessions": 0, "message": "No old sessions to delete"}
    
    # Xóa tin nhắn của các session cũ
    delete_result = await db.execute(
        delete(ChatMessage).where(ChatMessage.session_id.in_(old_session_ids))
    )
    
    await db.commit()
    
    return {
        "deleted_sessions": len(old_session_ids),
        "deleted_messages": delete_result.rowcount,
        "cutoff_date": cutoff_date.isoformat()
    }



# 7) GET SESSION STATISTICS

@router.get(
    "/statistics",
    summary="Thống kê sử dụng chatbot",
)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Thống kê tổng quan về usage của chatbot.
    """
    # Tổng số messages
    total_messages = await db.execute(select(func.count(ChatMessage.id)))
    total_count = total_messages.scalar()
    
    # Tổng số sessions
    total_sessions = await db.execute(
        select(func.count(func.distinct(ChatMessage.session_id)))
    )
    session_count = total_sessions.scalar()
    
    # Messages trong 24h
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    messages_24h = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.created_at > cutoff_24h)
    )
    count_24h = messages_24h.scalar()
    
    # Average messages per session
    avg_msg_per_session = total_count / session_count if session_count > 0 else 0
    
    return {
        "total_messages": total_count,
        "total_sessions": session_count,
        "messages_last_24h": count_24h,
        "avg_messages_per_session": round(avg_msg_per_session, 2),
        "generated_at": datetime.utcnow().isoformat()
    }



# 8) DELETE ONE MESSAGE

@router.delete(
    "/messages/{message_id}",
    status_code=204,
    summary="Xóa 1 tin nhắn cụ thể",
)
async def delete_chat_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa 1 tin nhắn theo ID.
    """
    query = select(ChatMessage).where(ChatMessage.id == message_id)
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    await db.delete(message)
    await db.commit()
    return None