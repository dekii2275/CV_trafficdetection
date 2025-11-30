from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings_server

ASYNC_DATABASE_URL = settings_server.DATABASE_URL

SYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("+asyncpg", "")


engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=sync_engine
)

Base = declarative_base()



async def create_tables():
    """
    Tạo bảng (Async) khi khởi động server.
    """
    # Import tất cả models vào đây để SQLAlchemy nhận diện
    from app.models.chat_message import ChatMessage
    # from app.models.traffic_log import TrafficLog (Nếu bạn đã tạo file này)

    async with engine.begin() as conn:
        # Xóa comment dòng dưới nếu muốn reset sạch DB mỗi lần chạy (Cẩn thận!)
        # await conn.run_sync(Base.metadata.drop_all)
        
        await conn.run_sync(Base.metadata.create_all)
        print(" Database tables created successfully")

async def get_db():
    """
    Dependency Async cho FastAPI Router
    Sử dụng: async def endpoint(db: AsyncSession = Depends(get_db))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()