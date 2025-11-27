"use client";

import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { MessageCircle, X } from "lucide-react";

type ChatMessage = {
  id: string;
  sender: "user" | "bot";
  text: string;
};

const FAQ_SNIPPETS: Record<string, string> = {
  traffic: "Hệ thống theo dõi mật độ giao thông theo thời gian thực.",
  camera: "Bạn có thể kết nối camera IP hoặc file video có sẵn.",
  deploy: "Ứng dụng có thể triển khai trên server hoặc edge device.",
  alert: "Cảnh báo được gửi khi phát hiện ùn tắc hoặc sự cố bất thường.",
};

export default function ChatBubble() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: crypto.randomUUID(),
      sender: "bot",
      text: "Xin chào! Tôi có thể giúp gì cho bạn về hệ thống giao thông thông minh?",
    },
  ]);
  const listRef = useRef<HTMLDivElement>(null);

  const lastMessageId = useMemo(() => messages[messages.length - 1]?.id, [messages]);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({
        top: listRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  };

  const handleSend = () => {
    if (!input.trim()) return;
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      sender: "user",
      text: input.trim(),
    };
    setMessages((prev: ChatMessage[]) => [...prev, userMessage]);
    setInput("");

    const reply = getBotReply(userMessage.text);
    setTimeout(() => {
      setMessages((prev: ChatMessage[]) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: "bot",
          text: reply,
        },
      ]);
    }, 600);
  };

  const getBotReply = (text: string) => {
    const lower = text.toLowerCase();
    for (const key of Object.keys(FAQ_SNIPPETS)) {
      if (lower.includes(key)) {
        return FAQ_SNIPPETS[key];
      }
    }
    return "Cảm ơn bạn! Đội ngũ sẽ phản hồi chi tiết trong thời gian sớm nhất.";
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-50 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition"
          aria-label="Mở chatbot"
        >
          <MessageCircle size={28} />
        </button>
      )}

      {open && (
        <div className="fixed bottom-5 right-5 w-[28rem] h-[34rem] bg-white border border-gray-300 shadow-xl z-50 flex flex-col overflow-hidden rounded-none">
          <div className="flex items-center justify-between bg-blue-600 text-white px-4 py-2">
            <h2 className="font-semibold">Chatbot</h2>
            <button onClick={() => setOpen(false)} aria-label="Đóng chatbot">
              <X size={24} />
            </button>
          </div>

          <div
            ref={listRef}
            className="flex-1 p-3 overflow-y-auto text-sm text-gray-800 space-y-2 bg-gray-50"
          >
            {messages.map((message: ChatMessage) => (
              <div
                key={message.id}
                className={`px-3 py-2 rounded-lg max-w-[85%] ${
                  message.sender === "user"
                    ? "bg-blue-600 text-white ml-auto"
                    : "bg-white border text-gray-800"
                }`}
              >
                {message.text}
              </div>
            ))}
          </div>

          <div className="p-4 border-t flex">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhập tin nhắn..."
              className="flex-1 border px-3 py-2 focus:outline-blue-500"
            />
            <button
              onClick={handleSend}
              className="ml-2 bg-blue-600 text-white px-4 py-2 hover:bg-blue-700 disabled:opacity-50"
              disabled={!input.trim()}
            >
              Gửi
            </button>
          </div>
        </div>
      )}
    </>
  );
}
