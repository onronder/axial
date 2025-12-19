"use client";

import { useParams } from "next/navigation";
import { ChatArea } from "@/components/chat/ChatArea";
import { useChatHistory } from "@/hooks/useChatHistory";

export default function ChatPage() {
    const params = useParams();
    const chatId = params.chatId as string;
    const { getMessagesById } = useChatHistory();

    const initialMessages = getMessagesById(chatId);

    return (
        <div className="h-full">
            <ChatArea initialMessages={initialMessages} />
        </div>
    );
}
