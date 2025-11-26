from fastapi import APIRouter, HTTPException, Query,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List, Optional
from datetime import datetime

from app.models.chat_message import ChatMessage
from app.schemas.ChatMessage import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessageListResponse,
)
from app.db.base import get_db

router = APIRouter()


# ---------------------------------------------------------------------
# 1) CREATE MESSAGE — PUBLIC
# ---------------------------------------------------------------------
@router.post(
    "/messages",
    response_model=ChatMessageResponse,
    status_code=201,
    summary="Lưu tin nhắn chat (PUBLIC)",
)
async def create_chat_message(
    message_data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Lưu 1 tin nhắn chat (không cần đăng nhập).
    """
    new_message = ChatMessage(
        message=message_data.message,
        is_user=message_data.is_user,
        images=message_data.images,
        extra_data=message_data.extra_data,
        user_id=None  # Không còn user
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    return new_message


# ---------------------------------------------------------------------
# 2) GET CHAT HISTORY — PUBLIC
# ---------------------------------------------------------------------
@router.get(
    "/messages",
    response_model=List[ChatMessageListResponse],
    summary="Lấy lịch sử chat (PUBLIC)",
)
async def get_chat_history(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    since: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy toàn bộ lịch sử chat (không phân theo user).
    """
    query = select(ChatMessage)

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
        )
        for msg in messages
    ]


# ---------------------------------------------------------------------
# 3) DELETE ALL MESSAGES — PUBLIC
# ---------------------------------------------------------------------
@router.delete(
    "/messages",
    status_code=204,
    summary="Xóa toàn bộ lịch sử chat (PUBLIC)",
)
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
):
    """
    Xóa tất cả tin nhắn trong database (public).
    """
    await db.execute(delete(ChatMessage))
    await db.commit()
    return None


# ---------------------------------------------------------------------
# 4) DELETE ONE MESSAGE — PUBLIC
# ---------------------------------------------------------------------
@router.delete(
    "/messages/{message_id}",
    status_code=204,
    summary="Xóa 1 tin nhắn theo ID (PUBLIC)",
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


# ---------------------------------------------------------------------
# 5) COUNT MESSAGES — PUBLIC
# ---------------------------------------------------------------------
@router.get(
    "/messages/count",
    summary="Đếm tổng số tin nhắn (PUBLIC)",
)
async def get_message_count(
    db: AsyncSession = Depends(get_db),
):
    """
    Trả về tổng số tin nhắn.
    """
    from sqlalchemy import func
    result = await db.execute(select(func.count(ChatMessage.id)))
    count = result.scalar()
    return {"count": count}
