"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { ChatArea } from "@/components/chat/ChatArea";
import { useChatHistory, Message } from "@/hooks/useChatHistory";
import { Loader2 } from "lucide-react";

export default function ChatPage() {
    const params = useParams();
    const chatId = params.chatId as string;
    const { getMessagesById } = useChatHistory();

    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const loadMessages = async () => {
            if (!chatId || chatId === 'new-chat-id') {
                // New chat, no messages to load
                setMessages([]);
                setIsLoading(false);
                return;
            }

            setIsLoading(true);
            try {
                const msgs = await getMessagesById(chatId);
                setMessages(msgs);
            } catch (error) {
                console.error('Failed to load messages:', error);
                setMessages([]);
            } finally {
                setIsLoading(false);
            }
        };

        loadMessages();
    }, [chatId, getMessagesById]);

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="h-full">
            <ChatArea
                initialMessages={messages}
                conversationId={chatId !== 'new-chat-id' ? chatId : undefined}
            />
        </div>
    );
}
