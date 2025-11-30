"""
RAG ChatBot Agent - Chatbot với Retrieval-Augmented Generation
Sử dụng Gemini API + Vector Search để trả lời câu hỏi về luật giao thông
"""

import google.generativeai as genai
from typing import List, Dict, Optional, AsyncIterator
import os
import asyncio
from datetime import datetime

from app.services.rag_services.vector_store import get_vector_store


class ChatBotAgent:
    """
    RAG-powered chatbot cho tư vấn luật giao thông Việt Nam
    """
    
    def __init__(self):
        """
        Khởi tạo ChatBot với Gemini API và Vector Store
        """
        # Load API key từ environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY không được thiết lập trong environment variables")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Khởi tạo Vector Store
        print("🔄 Initializing Vector Store...")
        self.vector_store = get_vector_store()
        
        # System prompt
        self.system_prompt = """
        Bạn là một chuyên gia tư vấn luật giao thông Việt Nam.

        NHIỆM VỤ:
        - Trả lời chính xác các câu hỏi về luật giao thông dựa trên thông tin được cung cấp
        - Trích dẫn rõ ràng điều luật, khoản, điểm liên quan
        - Giải thích dễ hiểu cho người dân
        - Nếu không có thông tin trong tài liệu, hãy nói rõ "Tôi không tìm thấy thông tin này trong các văn bản luật hiện có"

        QUY TẮC:
        1. Luôn trích dẫn nguồn: "Theo Điều X Luật Y/Z/QH..."
        2. Ưu tiên luật mới nhất nếu có nhiều văn bản
        3. Cảnh báo nếu có thay đổi luật gần đây
        4. Đưa ra ví dụ cụ thể khi có thể
        5. Không bịa đặt thông tin"""
        
        print("ChatBotAgent initialized successfully")
    
    async def get_response(
        self,
        message: str,
        session_id: str,
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 5
    ) -> Dict:
        try:
            # BƯỚC 1: Retrieve relevant documents
            print(f"Searching for relevant laws: '{message}'")
            search_results = self.vector_store.search(
                query=message,
                top_k=top_k
            )
            
            # BƯỚC 2: Chuẩn bị context từ retrieved documents
            context = self._format_context(search_results)
            
            # BƯỚC 3: Format conversation history
            history_text = self._format_history(conversation_history) if conversation_history else ""
            
            # BƯỚC 4: Tạo prompt với context
            full_prompt = f"""{self.system_prompt}

            THÔNG TIN LUẬT LIÊN QUAN:
            {context}

            LỊCH SỬ HỘI THOẠI:
            {history_text}

            CÂU HỎI: {message}

            TRẢ LỜI:
            """
            
            # BƯỚC 5: Generate response từ Gemini
            print("Generating response with Gemini...")
            response = await self._generate_with_gemini(full_prompt)
            
            # BƯỚC 6: Extract sources để trả về
            sources = self._extract_sources(search_results)
            
            return {
                "message": response,
                "sources": sources,
                "image": None,
                "retrieved_docs": len(search_results)
            }
            
        except Exception as e:
            print(f"Error in get_response: {e}")
            return {
                "message": f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn: {str(e)}",
                "sources": [],
                "image": None
            }
    
    async def _generate_with_gemini(self, prompt: str) -> str:
        """
        Gọi Gemini API để generate response
        """
        try:
            # Sử dụng generate_content_async cho async operation
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
            raise
    
    async def stream_response(
        self,
        message: str,
        session_id: str,
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 5
    ) -> AsyncIterator[str]:
        """
        Stream response cho WebSocket (từng chunk)
        """
        try:
            # Retrieve documents
            search_results = self.vector_store.search(query=message, top_k=top_k)
            context = self._format_context(search_results)
            history_text = self._format_history(conversation_history) if conversation_history else ""
            
            full_prompt = f"""{self.system_prompt}

                THÔNG TIN LUẬT LIÊN QUAN:
                {context}

                LỊCH SỬ HỘI THOẠI:
                {history_text}

                CÂU HỎI: {message}

                TRẢ LỜI:
                """
            
            # Stream từ Gemini
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"Lỗi: {str(e)}"
    
    def _format_context(self, search_results: List[Dict]) -> str:
        """
        Format retrieved documents thành context cho prompt
        """
        if not search_results:
            return "Không tìm thấy thông tin liên quan."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            metadata = result['metadata']
            doc_text = result['document']
            similarity = result['similarity_score']
            
            context_parts.append(f"""
                [Tài liệu {i}] - Độ liên quan: {similarity:.2%}
                Nguồn: {metadata.get('law_name', 'N/A')} - Điều {metadata.get('article_number', 'N/A')}
                Tiêu đề: {metadata.get('article_title', 'N/A')}
                Nội dung:
                {doc_text}
                ---""")
        
        return "\n".join(context_parts)
    
    def _format_history(self, history: List[Dict]) -> str:
        """
        Format conversation history cho prompt
        """
        if not history:
            return "Không có lịch sử hội thoại."
        
        history_parts = []
        for msg in history[-5:]:  # Chỉ lấy 5 tin nhắn gần nhất
            role = "Người dùng" if msg['role'] == 'user' else "Trợ lý"
            history_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(history_parts)
    
    def _extract_sources(self, search_results: List[Dict]) -> List[Dict]:
        """
        Trích xuất thông tin nguồn để trả về cho client
        """
        sources = []
        for result in search_results:
            metadata = result['metadata']
            sources.append({
                "law_name": metadata.get('law_name', 'N/A'),
                "article": metadata.get('article_number', 'N/A'),
                "title": metadata.get('article_title', 'N/A'),
                "source_file": metadata.get('source_file', 'N/A'),
                "similarity": f"{result['similarity_score']:.2%}"
            })
        
        return sources
    
    def get_stats(self) -> Dict:
        """
        Lấy thống kê về vector store
        """
        return self.vector_store.get_collection_info()


# Singleton instance
_agent = None

def get_agent() -> ChatBotAgent:
    """
    Get hoặc tạo ChatBotAgent instance (singleton)
    """
    global _agent
    if _agent is None:
        _agent = ChatBotAgent()
    return _agent