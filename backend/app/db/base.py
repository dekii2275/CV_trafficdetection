from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings_server


engine = create_async_engine(
    settings_server.DATABASE_URL,
    echo=False,            # Bạn có thể bật True nếu muốn xem SQL log
    future=True
)

# Async Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base cho tất cả models
Base = declarative_base()



async def create_tables():
    """
    Tạo tất cả bảng trong database.
    Import models tại đây để tránh lỗi circular import.
    """

    from app.models.TokenLLM import TokenLLM
    from app.models.chat_message import ChatMessage

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """
    Dependency để inject session DB vào API.
    """
    async with AsyncSessionLocal() as session:
        yield session
