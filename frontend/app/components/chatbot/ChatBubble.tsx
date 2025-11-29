"use client";

import { useMemo, useRef, useState, useEffect, type KeyboardEvent } from "react";
import { MessageCircle, X, ExternalLink, Image as ImageIcon } from "lucide-react";

// --- Types định nghĩa dựa trên API Response ---
type Source = {
  source?: string;
  page_content?: string;
  metadata?: Record<string, any>;
};

type ChatMessage = {
  id: string;
  sender: "user" | "bot";
  text: string;
  // Các trường bổ sung từ API
  images?: string[]; // API trả về list ảnh (base64 hoặc url)
  sources?: Source[]; // API trả về list nguồn
};

type ApiChatResponse = {
  message: string;
  image?: string[];
  session_id: string;
  sources?: Source[];
};

export default function ChatBubble() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  // Lưu session_id để duy trì hội thoại liên tục
  const sessionIdRef = useRef<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: "welcome-msg",
      sender: "bot",
      text: "Xin chào! Tôi là trợ lý AI về Luật Giao Thông. Bạn cần tra cứu thông tin gì?",
    },
  ]);

  const listRef = useRef<HTMLDivElement>(null);

  // Tự động cuộn xuống cuối khi có tin nhắn mới hoặc đang loading
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTo({
        top: listRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isLoading, open]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userText = input.trim();
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      sender: "user",
      text: userText,
    };

    // 1. UI update ngay lập tức
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // 2. Gọi API với session_id hiện tại (nếu có)
      const payload = {
        message: userText,
        session_id: sessionIdRef.current, // Quan trọng: Gửi kèm session cũ để bot nhớ context
      };

      const response = await fetch("http://localhost:8000/api/v1/chat", { 
      // Lưu ý: Thêm http://localhost:8000 nếu chưa config proxy, và thêm /v1
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Lỗi kết nối server");
      }

      const data: ApiChatResponse = await response.json();

      // 3. Cập nhật Session ID từ server trả về (để dùng cho câu sau)
      if (data.session_id) {
        sessionIdRef.current = data.session_id;
      }

      // 4. Tạo bot message với đầy đủ dữ liệu (text, ảnh, nguồn)
      const botMessage: ChatMessage = {
        id: crypto.randomUUID(),
        sender: "bot",
        text: data.message,
        images: data.image,
        sources: data.sources,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        sender: "bot",
        text: "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  // Hàm helper để render danh sách nguồn (Sources)
  const renderSources = (sources?: Source[]) => {
    if (!sources || sources.length === 0) return null;
    
    // Lọc trùng lặp nguồn nếu cần
    const uniqueSources = Array.from(new Set(sources.map(s => s.source || "Tài liệu")));

    return (
      <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-600">
        <p className="font-semibold mb-1 flex items-center gap-1">
          <ExternalLink size={10} /> Nguồn tham khảo:
        </p>
        <ul className="list-disc pl-4 space-y-1">
          {uniqueSources.map((src, idx) => (
            <li key={idx} className="break-words">
              {src}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  // Hàm helper để render hình ảnh
  const renderImages = (images?: string[]) => {
    if (!images || images.length === 0) return null;

    return (
      <div className="mt-2 space-y-2">
        {images.map((imgSrc, idx) => (
          <div key={idx} className="relative rounded-lg overflow-hidden border border-gray-200">
            <img 
              src={`data:image/png;base64,${imgSrc}`} // Giả định API trả base64, nếu là URL thì bỏ đoạn `data:...`
              alt="Minh họa luật giao thông" 
              className="w-full h-auto object-cover max-h-48"
              onError={(e) => {
                 // Fallback nếu ảnh lỗi hoặc không phải base64 chuẩn
                 (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        ))}
      </div>
    );
  };

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-50 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-105"
          aria-label="Mở trợ lý giao thông"
        >
          <MessageCircle size={28} />
        </button>
      )}

      {open && (
        <div className="fixed bottom-5 right-5 w-[90vw] sm:w-[28rem] h-[34rem] bg-white border border-gray-300 shadow-2xl z-50 flex flex-col rounded-xl overflow-hidden font-sans">
          {/* Header */}
          <div className="flex items-center justify-between bg-gradient-to-r from-blue-600 to-blue-500 text-white px-4 py-3 shadow-md">
            <div className="flex flex-col">
              <h2 className="font-bold text-lg">Trợ Lý Luật Giao Thông</h2>
              <span className="text-xs opacity-90">Hỗ trợ tra cứu & giải đáp 24/7</span>
            </div>
            <button 
              onClick={() => setOpen(false)} 
              className="hover:bg-white/20 p-1 rounded transition"
              aria-label="Đóng chatbot"
            >
              <X size={24} />
            </button>
          </div>

          {/* Messages List */}
          <div
            ref={listRef}
            className="flex-1 p-4 overflow-y-auto bg-gray-50 space-y-4"
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex w-full ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`relative max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                    msg.sender === "user"
                      ? "bg-blue-600 text-white rounded-tr-none"
                      : "bg-white border border-gray-200 text-gray-800 rounded-tl-none"
                  }`}
                >
                  {/* Nội dung text */}
                  <div className="whitespace-pre-wrap">{msg.text}</div>

                  {/* Render Ảnh minh họa (nếu có) */}
                  {msg.sender === 'bot' && renderImages(msg.images)}

                  {/* Render Nguồn (nếu có) */}
                  {msg.sender === 'bot' && renderSources(msg.sources)}
                </div>
              </div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex justify-start w-full">
                <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="p-3 bg-white border-t border-gray-100">
            <div className="flex items-center gap-2 bg-gray-100 rounded-full px-4 py-2 border border-transparent focus-within:border-blue-400 focus-within:bg-white transition-all">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Nhập câu hỏi (VD: Vượt đèn đỏ phạt bao nhiêu?)..."
                className="flex-1 bg-transparent border-none focus:outline-none text-sm text-gray-800 placeholder:text-gray-400"
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className={`p-2 rounded-full transition-all ${
                  input.trim() && !isLoading 
                    ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm" 
                    : "bg-gray-300 text-gray-500 cursor-not-allowed"
                }`}
              >
                {/* Icon gửi (Send Arrow) */}
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </div>
            <div className="text-center mt-1">
              <span className="text-[10px] text-gray-400">AI có thể mắc lỗi. Hãy kiểm tra lại thông tin quan trọng.</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}