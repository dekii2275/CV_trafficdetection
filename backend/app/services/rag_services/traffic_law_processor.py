# import re
# from typing import List, Dict, Any
# from langchain_core.documents import Document
# import docx # Cần cài: pip install python-docx

# class TrafficLawProcessor:
#     """
#     Xử lý văn bản luật giao thông: Tách Điều -> Khoản -> Điểm
#     """
#     def __init__(self):
#         # Regex các mẫu phổ biến
#         self.article_pattern = r"(^|\n)(Điều \d+\..*?)(?=\nĐiều \d+\.|$)"
#         self.clause_pattern = r"(^|\n)(\d+)\.\s+(.*?)(?=(\n\d+\.\s+)|$)"
#         # Regex tìm điểm: a), b), đ) ...
#         self.point_pattern = r"(^|\n)([a-zđ])\)\s+(.*?)(?=(\n[a-zđ]\))|$)" 
    
#     def read_docx(self, file_path: str) -> str:
#         """Đọc file .docx và làm sạch cơ bản"""
#         doc = docx.Document(file_path)
#         full_text = []
#         for para in doc.paragraphs:
#             txt = para.text.strip()
#             if txt:
#                 full_text.append(txt)
#         return "\n".join(full_text)

#     def identify_vehicle_type(self, text: str) -> str:
#         """Xác định loại xe từ tiêu đề Điều"""
#         text_lower = text.lower()
#         if "xe ô tô" in text_lower: return "oto"
#         if "xe mô tô" in text_lower or "xe gắn máy" in text_lower: return "xemay"
#         if "xe đạp" in text_lower or "xe thô sơ" in text_lower: return "xedap"
#         if "người đi bộ" in text_lower: return "nguoidibo"
#         return "chung"

#     def process_document(self, file_path: str) -> List[Document]:
#         text = self.read_docx(file_path)
#         chunks = []
#         source_name = Path(file_path).name
        
#         # 1. Tách các Điều
#         articles = re.finditer(self.article_pattern, text, re.DOTALL)
        
#         for art_match in articles:
#             article_full_text = art_match.group(2)
            
#             # Lấy tiêu đề Điều (Dòng đầu tiên)
#             # VD: "Điều 6. Xử phạt người điều khiển xe mô tô..."
#             article_header = article_full_text.strip().split('\n')[0]
#             vehicle_type = self.identify_vehicle_type(article_header)
            
#             # 2. Tách các Khoản trong Điều
#             clauses = re.finditer(self.clause_pattern, article_full_text, re.DOTALL)
#             has_clauses = False
            
#             for clause_match in clauses:
#                 has_clauses = True
#                 clause_num = clause_match.group(2)
#                 clause_body = clause_match.group(3).strip()
                
#                 # --- XỬ LÝ SÂU: Tách các Điểm (a, b, c) trong Khoản ---
#                 # Nếu Khoản quá dài hoặc có các điểm a, b, c -> Cắt nhỏ tiếp
#                 points = list(re.finditer(self.point_pattern, clause_body, re.DOTALL))
                
#                 if points:
#                     # Lấy phần dẫn nhập của khoản (VD: "Phạt tiền từ 100k-200k đối với hành vi:")
#                     # Thường là phần text trước điểm a)
#                     intro_text = clause_body[:points[0].start()].strip()
                    
#                     for p_match in points:
#                         p_label = p_match.group(2) # a, b, c...
#                         p_content = p_match.group(3).strip()
                        
#                         # Tạo Chunk chi tiết cấp Điểm
#                         full_content = (
#                             f"ĐIỀU LUẬT: {article_header}\n"
#                             f"MỨC PHẠT (Khoản {clause_num}): {intro_text}\n"
#                             f"HÀNH VI VI PHẠM (Điểm {p_label}): {p_content}"
#                         )
                        
#                         chunks.append(Document(
#                             page_content=full_content,
#                             metadata={
#                                 "source": source_name,
#                                 "article": article_header.split('.')[0],
#                                 "vehicle": vehicle_type,
#                                 "level": "point" # Cấp độ điểm
#                             }
#                         ))
#                 else:
#                     # Nếu không có điểm a,b,c -> Lấy nguyên Khoản
#                     full_content = (
#                         f"ĐIỀU LUẬT: {article_header}\n"
#                         f"NỘI DUNG (Khoản {clause_num}): {clause_body}"
#                     )
#                     chunks.append(Document(
#                         page_content=full_content,
#                         metadata={
#                             "source": source_name,
#                             "article": article_header.split('.')[0],
#                             "vehicle": vehicle_type,
#                             "level": "clause"
#                         }
#                     ))

#             # Nếu Điều không có khoản (chỉ có text ngắn)
#             if not has_clauses:
#                 chunks.append(Document(
#                     page_content=article_full_text, 
#                     metadata={"source": source_name, "vehicle": vehicle_type}
#                 ))
                
#         return chunks