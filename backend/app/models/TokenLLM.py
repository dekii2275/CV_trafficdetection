from sqlalchemy import Column, Integer
from app.db.base import Base


class TokenLLM(Base):
    __tablename__ = "token_llm"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Token còn lại cho chatbot
    token = Column(Integer, nullable=False, default=5000)
