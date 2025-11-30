"""
Script để build vector database từ các file luật giao thông.
Đã sửa lỗi Import LangChain và lỗi tham số dòng lệnh.

"""

import sys
import os
import re
import shutil
from typing import List
from pathlib import Path
import docx  

try:
    
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.schema import Document
    except ImportError:
        from langchain.docstore.document import Document


FILE_PATH = Path(__file__).resolve()

PROJECT_ROOT = FILE_PATH.parents[3] 
BACKEND_ROOT = FILE_PATH.parents[2] 


sys.path.append(str(BACKEND_ROOT))

ABS_DOCS_DIR = PROJECT_ROOT / "data" / "law_documents"
ABS_DB_DIR = PROJECT_ROOT / "data" / "chroma_db"

# Import service của bạn
try:
    from app.services.rag_services.vector_store import VectorStoreService
except ImportError as e:
    print(f"Lỗi Import Service: {e}")
    print(f"Đảm bảo bạn đang đứng ở thư mục 'backend' và file vector_store.py tồn tại.")
    sys.exit(1)


class TrafficLawProcessor:
    """
    Xử lý văn bản luật: Tách Điều -> Khoản -> Điểm để tránh mất thông tin
    """
    def __init__(self):
        # Regex tìm "Điều X."
        self.article_pattern = r"(^|\n)(Điều \d+\..*?)(?=\nĐiều \d+\.|$)"
        # Regex tìm "1. ", "2. " (Khoản)
        self.clause_pattern = r"(^|\n)(\d+)\.\s+(.*?)(?=(\n\d+\.\s+)|$)"
        # Regex tìm "a) ", "b) ", "đ) " (Điểm)
        self.point_pattern = r"(^|\n)([a-zđ])\)\s+(.*?)(?=(\n[a-zđ]\))|$)" 
    
    def read_docx(self, file_path: str) -> str:
        """Đọc file .docx và chuyển thành string"""
        try:
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                txt = para.text.strip()
                if txt:
                    full_text.append(txt)
            return "\n".join(full_text)
        except Exception as e:
            print(f"Lỗi đọc file {file_path}: {e}")
            return ""

    def identify_vehicle_type(self, text: str) -> str:
        """Nhận diện loại xe từ tiêu đề Điều luật"""
        text_lower = text.lower()
        if "xe ô tô" in text_lower: return "oto"
        if "xe mô tô" in text_lower or "xe gắn máy" in text_lower: return "xemay"
        if "xe đạp" in text_lower or "xe thô sơ" in text_lower: return "xedap"
        if "người đi bộ" in text_lower: return "nguoidibo"
        return "chung"

    def process_document(self, file_path: str) -> List[Document]:
        text = self.read_docx(file_path)
        if not text: return []
        
        chunks = []
        source_name = Path(file_path).name
        
        # B1: Tách các Điều
        articles = re.finditer(self.article_pattern, text, re.DOTALL)
        
        for art_match in articles:
            article_full_text = art_match.group(2)
            # Lấy dòng đầu tiên làm tiêu đề (VD: Điều 5. Xử phạt...)
            article_header = article_full_text.strip().split('\n')[0]
            vehicle_type = self.identify_vehicle_type(article_header)
            
            # B2: Tách các Khoản (Clauses) trong Điều
            clauses = re.finditer(self.clause_pattern, article_full_text, re.DOTALL)
            has_clauses = False
            
            for clause_match in clauses:
                has_clauses = True
                clause_num = clause_match.group(2)
                clause_body = clause_match.group(3).strip()
                
                # B3: Tách các Điểm (Points: a, b, c...) trong Khoản
                points = list(re.finditer(self.point_pattern, clause_body, re.DOTALL))
                
                if points:
                    # Lấy phần dẫn nhập (VD: "Phạt tiền từ 200k... hành vi sau:")
                    intro_text = clause_body[:points[0].start()].strip()
                    
                    for p_match in points:
                        p_label = p_match.group(2) # a, b, c
                        p_content = p_match.group(3).strip()
                        
                        # Tạo nội dung Chunk chi tiết
                        full_content = (
                            f"ĐIỀU LUẬT: {article_header}\n"
                            f"MỨC PHẠT (Khoản {clause_num}): {intro_text}\n"
                            f"HÀNH VI VI PHẠM (Điểm {p_label}): {p_content}"
                        )
                        
                        chunks.append(Document(
                            page_content=full_content,
                            metadata={
                                "source": source_name,
                                "article": article_header.split('.')[0], # VD: Điều 5
                                "vehicle": vehicle_type,
                                "level": "point" # Cấp độ chi tiết nhất
                            }
                        ))
                else:
                    # Nếu không có điểm a,b,c -> Lấy nguyên Khoản
                    full_content = (
                        f"ĐIỀU LUẬT: {article_header}\n"
                        f"NỘI DUNG (Khoản {clause_num}): {clause_body}"
                    )
                    chunks.append(Document(
                        page_content=full_content,
                        metadata={
                            "source": source_name,
                            "article": article_header.split('.')[0],
                            "vehicle": vehicle_type,
                            "level": "clause"
                        }
                    ))

            # Nếu Điều quá ngắn không có khoản (chỉ có text)
            if not has_clauses:
                chunks.append(Document(
                    page_content=article_full_text, 
                    metadata={"source": source_name, "vehicle": vehicle_type, "level": "article"}
                ))
                
        return chunks

def build_vector_database(documents_dir: str = str(ABS_DOCS_DIR), reset: bool = False):
    print("\n" + "="*60)
    print("RAG BUILDER: SMART CHUNKING (Luật Giao Thông)")
    print("="*60)
    print(f"Đọc tài liệu từ: {documents_dir}")
    print(f"Lưu Database tại: {ABS_DB_DIR}")
    
    # Xử lý tham số Reset
    if reset:
        if ABS_DB_DIR.exists():
            print(f"Đang xóa database cũ để làm sạch dữ liệu...")
            shutil.rmtree(ABS_DB_DIR)
        else:
            print("Không tìm thấy database cũ, sẽ tạo mới hoàn toàn.")
    
    # Init Vector Store
    print("Đang khởi tạo Vector Store...")
    vector_store = VectorStoreService(
        collection_name="traffic_laws",
        persist_directory=str(ABS_DB_DIR)
    )

    # Xử lý file
    processor = TrafficLawProcessor()
    all_documents = []
    
    if not os.path.exists(documents_dir):
        print(f"LỖI: Thư mục tài liệu không tồn tại: {documents_dir}")
        print(f"Vui lòng tạo thư mục này và copy file .docx vào đó.")
        return

    files = [f for f in os.listdir(documents_dir) if f.endswith(".docx") or f.endswith(".doc")]
    if not files:
        print(f"CẢNH BÁO: Thư mục {documents_dir} trống! Hãy copy file luật vào.")
        return

    for filename in files:
        file_path = os.path.join(documents_dir, filename)
        print(f"\nĐang xử lý file: {filename}...")
        
        chunks = processor.process_document(file_path)
        all_documents.extend(chunks)
        print(f"   -> Tạo được {len(chunks)} chunks dữ liệu.")

    if not all_documents:
        print(" Không tạo được dữ liệu nào. Kiểm tra lại nội dung file input.")
        return

    # Lưu vào ChromaDB
    print(f"\n Đang lưu {len(all_documents)} chunks vào Database (Quá trình này có thể mất vài phút)...")
    
    texts = [doc.page_content for doc in all_documents]
    metadatas = [doc.metadata for doc in all_documents]
    
    vector_store.add_documents(documents=texts, metadatas=metadatas)
    print("\nXÂY DỰNG DATABASE THÀNH CÔNG!")


# 5. HÀM TEST TRUY VẤN

def test_search(query: str):
    print("\n" + "="*60)
    print(f"TEST TRUY VẤN THỬ: \"{query}\"")
    print("="*60)
    
    if not ABS_DB_DIR.exists():
        print("Database chưa được xây dựng. Hãy chạy lệnh build trước.")
        return

    vector_store = VectorStoreService(
        collection_name="traffic_laws",
        persist_directory=str(ABS_DB_DIR)
    )
    
    results = vector_store.search(query, top_k=3)
    
    print(f"🔍 Tìm thấy {len(results)} kết quả liên quan nhất:\n")
    for i, res in enumerate(results, 1):
        # Lấy thông tin an toàn
        score = res.get('similarity_score', 0)
        meta = res.get('metadata', {})
        content = res.get('document', '')
        
        # Làm gọn nội dung để hiển thị
        preview = content[:250].replace('\n', ' ') + "..."
        
        print(f"--- Top {i} (Độ khớp: {score:.2f}) ---")
        print(f"Nguồn: {meta.get('source', 'N/A')} | {meta.get('article', 'N/A')}")
        print(f"Nội dung: {preview}\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tool build dữ liệu cho Chatbot Giao thông")
    
    parser.add_argument("--reset", action="store_true", help="Xóa sạch DB cũ và build lại từ đầu")
    
    parser.add_argument("--test-query", type=str, default="không đội mũ bảo hiểm phạt bao nhiêu", help="Câu hỏi để test thử sau khi build")
    
    parser.add_argument("--skip-build", action="store_true", help="Chỉ chạy test, không build lại DB")
    
    args = parser.parse_args()
    
    if not args.skip_build:
        build_vector_database(reset=args.reset)
    
    test_search(args.test_query)