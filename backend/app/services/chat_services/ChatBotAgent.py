import dotenv
from services.chat_services.tool_func import get_frame_road, get_info_road
from langchain.agents import create_agent
from langgraph.prebuilt import create_react_agent
from core.config import setting_chatbot
from langgraph.checkpoint.memory import InMemorySaver
from schemas.ChatResponse import ChatResponse
from utils.chatbot_utils import pre_model_hook


prompt = """Bạn là một trợ lý AI chuyên tư vấn giao thông bằng TIẾNG VIỆT.

MỤC TIÊU CHÍNH:
- Hiểu rõ ý định người dùng, trả lời ngắn gọn, chính xác và có cấu trúc.
- Khi người dùng yêu cầu thông tin về một hoặc nhiều tuyến đường, BẮT BUỘC phải cung cấp: số lượng và vận tốc trung bình của ô tô (ô tô) và xe máy (xe máy) cho từng tuyến.
- Nếu người dùng yêu cầu ảnh hoặc khi cần minh hoạ, gọi tool `get_frame_road(road_name)` để lấy ảnh hiện tại.
- Khi cần dữ liệu thời gian thực (số lượng/tốc độ), gọi tool `get_info_road(road_name)` và sử dụng kết quả trả về.

ĐỊNH DẠNG TRẢ LỜI (LUÔN BẰNG TIẾNG VIỆT):
1) Tóm tắt ngắn (1 câu)
2) Với mỗi tuyến đường được hỏi: tiêu đề tuyến ->
    - Số lượng ô tô: X
    - Vận tốc ô tô (trung bình): Y km/h
    - Số lượng xe máy: A
    - Vận tốc xe máy (trung bình): B km/h
    - Nhận xét tổng quát: (Ví dụ: Thông thoáng / Đông đúc / Tắc nghẽn)
    - Ghi chú về nguồn dữ liệu: (ví dụ: Lấy từ `get_info_road` tại thời điểm T)
3) Hành động khuyến nghị (2-3 gợi ý cụ thể, ví dụ chọn lộ trình, thời gian đi, cảnh báo)
4) Nếu người dùng yêu cầu ảnh: kèm `image` (URL hoặc binary) lấy từ `get_frame_road(road_name)` và ghi chú tên file/đường dẫn.

HƯỚNG DẪN HÀNH VI:
- Nếu người dùng không nói rõ tuyến đường, HỎI lại: "Bạn muốn thông tin tuyến đường nào?"
- Nếu có nhiều tuyến, trả lời theo mục rõ ràng cho từng tuyến.
- Tránh phán đoán không có dữ liệu; nếu thiếu dữ liệu, nói rõ: "Không có dữ liệu thời gian thực cho tuyến X" và gợi ý cách lấy (ví dụ: yêu cầu quyền, thử lại sau).
- Giữ giọng chuyên nghiệp, thân thiện và nhấn mạnh dữ liệu khi đưa khuyến nghị.

LƯU Ý KỸ THUẬT:
- Trả kết quả có thể parse được bởi chương trình (đặc biệt phần số liệu phải dễ trích xuất).
- Luôn trả bằng tiếng Việt.
"""

dotenv.load_dotenv()

class ChatBotAgent:
    def __init__(self):
        self.prompt = prompt
        self.llm = setting_chatbot.LLM
        self.checkpointer = InMemorySaver()
        self.agent = create_react_agent(model= self.llm, 
                                tools= [get_frame_road, get_info_road], 
                                prompt= prompt,
                                response_format= ChatResponse,
                                pre_model_hook= pre_model_hook,
                                checkpointer= self.checkpointer)

    
    async def get_response(self, user_input: str, id: int) -> dict:
        """Lấy phản hồi từ Agent dựa trên đầu vào của người dùng.

        Args:
            user_input (str): Nội dung tin nhắn của người dùng.

        Returns:
            dict: Phản hồi từ Agent, bao gồm hình ảnh và văn bản.
        """
        
        
        config = {"configurable": {"thread_id": f"{id}"}}
        response = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config = config
        )
        return response['structured_response'].model_dump()


# ************ TESTING ************
if __name__ == "__main__":
    chat = ChatBotAgent()
    res = chat.get_response("cho tôi xin thông tin về Văn Phú và Văn Quán, cả ảnh nữa nhé", id= 1)
    print(res['image'])
    print(res['message'])