"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { ChatArea } from "@/components/chat/ChatArea";
import { useChatHistory, Message } from "@/hooks/useChatHistory";
import { Loader2 } from "lucide-react";

export default function ChatPage() {
    const params = useParams();
    const chatId = params.chatId as string;
    const { getMessagesById } = useChatHistory();
    const hasFetched = useRef(false);

    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Prevent double-fetch
        if (hasFetched.current) return;
        hasFetched.current = true;

        const loadMessages = async () => {
            setIsLoading(true);
            try {
                console.log('📄 [ChatPage] Loading messages for:', chatId);
                const msgs = await getMessagesById(chatId);
                console.log('📄 [ChatPage] Loaded', msgs.length, 'messages');
                setMessages(msgs);
            } catch (error) {
                console.error('📄 [ChatPage] Failed to load messages:', error);
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
                conversationId={chatId}
            />
        </div>
    );
}
