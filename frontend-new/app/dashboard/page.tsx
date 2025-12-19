"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useChatHistory } from "@/hooks/useChatHistory";
import { EmptyState } from "@/components/chat/EmptyState";
import { ChatInput } from "@/components/chat/ChatInput";

export default function DashboardPage() {
    const router = useRouter();
    const { createNewChat } = useChatHistory();

    const handleQuerySelect = (query: string) => {
        // In a real app, we might pass this query to the new chat
        const newChatId = createNewChat();
        router.push(`/dashboard/chat/${newChatId}`);
    };

    const handleSend = (message: string) => {
        const newChatId = createNewChat();
        router.push(`/dashboard/chat/${newChatId}`);
    };

    return (
        <div className="flex h-full flex-col">
            <div className="flex-1 overflow-y-auto">
                <EmptyState onQuerySelect={handleQuerySelect} />
            </div>
            <ChatInput onSend={handleSend} />
        </div>
    );
}
