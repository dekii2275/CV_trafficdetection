"""
Document Processor - Xử lý và chia nhỏ văn bản luật giao thông
"""

from pathlib import Path
from typing import List, Dict, Tuple
import docx
import re


class DocumentProcessor:
    """
    Xử lý văn bản luật từ .doc/.docx files
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        """
        Args:
            chunk_size: Độ dài tối đa của mỗi chunk (ký tự)
            chunk_overlap: Số ký tự overlap giữa các chunk
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def read_docx(self, file_path: str) -> str:
        """
        Đọc nội dung từ file .docx
        """
        try:
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            return "\n".join(full_text)
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return ""
    
    def extract_law_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Tách văn bản thành các điều luật riêng biệt
        
        Pattern:
        - Điều 1. Tiêu đề
        - 1. Nội dung điểm 1
        - 2. Nội dung điểm 2
        """
        sections = []
        
        # Pattern để tìm các Điều luật
        article_pattern = r'Điều\s+(\d+)[.\s]+([^\n]+)'
        
        # Tìm tất cả các Điều
        articles = list(re.finditer(article_pattern, text))
        
        for i, match in enumerate(articles):
            article_num = match.group(1)
            article_title = match.group(2).strip()
            
            # Lấy nội dung từ Điều hiện tại đến Điều tiếp theo
            start_pos = match.end()
            end_pos = articles[i + 1].start() if i + 1 < len(articles) else len(text)
            article_content = text[start_pos:end_pos].strip()
            
            sections.append({
                "article_number": article_num,
                "title": article_title,
                "content": article_content,
                "full_text": f"Điều {article_num}. {article_title}\n{article_content}"
            })
        
        return sections
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chia text thành các chunks nhỏ với overlap
        """
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # Tìm dấu câu gần nhất để không cắt giữa câu
            if end < text_length:
                # Tìm dấu câu (. ! ?) gần nhất
                for i in range(end, start + self.chunk_size // 2, -1):
                    if text[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
        
        return chunks
    
    def process_law_documents(
        self,
        documents_dir: str = "./data/law_documents"
    ) -> Tuple[List[str], List[Dict]]:
        """
        Xử lý tất cả văn bản luật trong thư mục
        
        Returns:
            (documents, metadatas) - Danh sách chunks và metadata tương ứng
        """
        documents = []
        metadatas = []
        doc_id = 0
        
        documents_path = Path(documents_dir)
        
        if not documents_path.exists():
            print(f"⚠️ Documents directory not found: {documents_dir}")
            return documents, metadatas
        
        # Xử lý từng file .doc/.docx
        law_files = list(documents_path.glob("*.doc")) + list(documents_path.glob("*.docx"))
        
        print(f"📄 Found {len(law_files)} law documents")
        
        for law_file in law_files:
            print(f"🔄 Processing: {law_file.name}")
            
            # Đọc nội dung
            full_text = self.read_docx(str(law_file))
            
            if not full_text:
                continue
            
            # Tách thành các Điều luật
            sections = self.extract_law_sections(full_text)
            
            # Xử lý từng Điều
            for section in sections:
                # Chunk nội dung nếu quá dài
                if len(section["full_text"]) > self.chunk_size:
                    chunks = self.chunk_text(section["full_text"])
                else:
                    chunks = [section["full_text"]]
                
                # Thêm vào danh sách
                for i, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "source_file": law_file.name,
                        "article_number": section["article_number"],
                        "article_title": section["title"],
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "law_name": self._extract_law_name(law_file.name)
                    })
                    doc_id += 1
        
        print(f"✅ Processed {len(documents)} chunks from {len(law_files)} documents")
        
        return documents, metadatas
    
    def _extract_law_name(self, filename: str) -> str:
        """
        Trích xuất tên luật từ filename
        Ví dụ: "36_2024_QH15_m_444251.doc" -> "Luật 36/2024/QH15"
        """
        # Remove extension
        name = filename.replace('.doc', '').replace('.docx', '')
        
        # Parse pattern: số_năm_cơquan
        parts = name.split('_')
        if len(parts) >= 3:
            return f"Luật {parts[0]}/{parts[1]}/{parts[2]}"
        
        return name
    
    def categorize_content(self, text: str) -> str:
        """
        Phân loại nội dung (để filter khi search)
        
        Returns:
            Category: "bien_bao", "phat_nguoi", "giay_phep", "tai_xe", etc.
        """
        text_lower = text.lower()
        
        categories = {
            "bien_bao": ["biển báo", "biển hiệu", "tín hiệu", "đèn giao thông"],
            "phat_nguoi": ["phạt", "vi phạm", "xử phạt", "mức phạt", "tiền phạt"],
            "giay_phep": ["giấy phép", "đăng ký", "đăng kiểm", "bằng lái"],
            "tai_xe": ["tài xế", "người lái", "người điều khiển"],
            "toc_do": ["tốc độ", "vượt quá", "km/h", "giới hạn tốc độ"],
            "an_toan": ["an toàn", "mũ bảo hiểm", "dây an toàn", "tai nạn"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return "general"


# Test function
if __name__ == "__main__":
    processor = DocumentProcessor()
    documents, metadatas = processor.process_law_documents()
    
    print(f"\n📊 Statistics:")
    print(f"Total chunks: {len(documents)}")
    print(f"\nSample chunk:")
    print(documents[0][:200] + "...")
    print(f"\nSample metadata:")
    print(metadatas[0])