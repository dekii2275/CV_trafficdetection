"""
Vector Store Service - Quản lý embeddings và similarity search
Sử dụng ChromaDB để lưu trữ và truy vấn vector embeddings
"""

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import os
from pathlib import Path

class VectorStoreService:
    """
    Service quản lý vector database cho RAG chatbot luật giao thông
    """
    
    def __init__(
        self,
        collection_name: str = "traffic_laws",
        # Chúng ta sẽ tính toán đường dẫn tuyệt đối bên trong, không tin tưởng tham số truyền vào
        persist_directory: str = None, 
        embedding_model: str = "keepitreal/vietnamese-sbert"
    ):
        self.collection_name = collection_name
        
        # --- FIX QUAN TRỌNG: Tự động lấy đường dẫn tuyệt đối ---
        # 1. Xác định vị trí file vector_store.py hiện tại
        current_file_path = Path(__file__).resolve()
        
        # 2. Lùi ra 4 cấp để về thư mục gốc dự án (app -> services -> rag_services -> file này)
        # Tùy cấu trúc folder của bạn, đoạn này sẽ tìm về thư mục chứa folder 'data'
        # Giả sử file này nằm ở: .../CV_trafficdetection/backend/app/services/rag_services/vector_store.py
        project_root = current_file_path.parent.parent.parent.parent.parent
        
        # 3. Tạo đường dẫn tuyệt đối đến data/chroma_db
        if persist_directory is None:
            # Nếu chạy uvicorn ở trong backend, ta cần trỏ ra ngoài hoặc vào đúng chỗ
            # Cách an toàn nhất: Tạo folder data ngay tại project root
            self.persist_directory = os.path.join(str(project_root), "data", "chroma_db")
        else:
            self.persist_directory = persist_directory

        print(f"📂 Vector DB Absolute Path: {self.persist_directory}")
        
        # Tạo thư mục nếu chưa tồn tại
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # --- FIX QUAN TRỌNG: Dùng PersistentClient ---
        # PersistentClient bắt buộc ghi dữ liệu xuống đĩa cứng
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo ChromaDB: {e}")
            raise e
        
        # Khởi tạo hoặc lấy collection
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Vietnamese traffic law embeddings"}
            )
            print(f"✅ Collection ready: {collection_name} (Docs: {self.collection.count()})")
        except Exception as e:
            print(f"❌ Error getting collection: {e}")
            raise e
        
        # Load embedding model
        print(f"🔄 Loading embedding model: {embedding_model}")
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            print("✅ Embedding model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            raise e
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict],
        ids: Optional[List[str]] = None
    ) -> None:
        if not documents:
            return
        
        print(f"🔄 Creating embeddings for {len(documents)} documents...")
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True
        ).tolist()
        
        if ids is None:
            ids = [f"doc_{i}_{os.urandom(4).hex()}" for i in range(len(documents))]
        
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ Added {len(documents)} documents. Total now: {self.collection.count()}")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True
        ).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )
        
        formatted_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i],
                    "similarity_score": 1 - results['distances'][0][i]
                })
        
        return formatted_results
    
    def delete_collection(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"🗑️ Deleted collection: {self.collection_name}")
        except:
            pass
    
    def get_collection_info(self) -> Dict:
        return {
            "name": self.collection_name,
            "total_documents": self.collection.count(),
            "persist_directory": self.persist_directory
        }
    
    def reset_and_rebuild(self) -> None:
        self.delete_collection()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Vietnamese traffic law embeddings"}
        )
        print(f"🔄 Reset collection: {self.collection_name}")


# Singleton instance
_vector_store = None

def get_vector_store() -> VectorStoreService:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store