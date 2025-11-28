import "./styles/globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import ChatBubble from "./components/chatbot/ChatBubble";

export const metadata: Metadata = {
  title: "Traffic AI Dashboard",
  description: "Vehicle detection and counting dashboard",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#0F172A] text-white antialiased">
        {children}
        <ChatBubble />
      </body>
    </html>
  );
}