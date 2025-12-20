"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useChatHistory } from "@/hooks/useChatHistory";
import { EmptyState } from "@/components/chat/EmptyState";
import { ChatInput } from "@/components/chat/ChatInput";

export default function DashboardPage() {
    const router = useRouter();
    const { createNewChat } = useChatHistory();

    const handleQuerySelect = async (query: string) => {
        try {
            const newChatId = await createNewChat();
            router.push(`/dashboard/chat/${newChatId}`);
        } catch {
            // Error is already handled in createNewChat with toast
        }
    };

    const handleSend = async (message: string) => {
        try {
            const newChatId = await createNewChat();
            router.push(`/dashboard/chat/${newChatId}`);
        } catch {
            // Error is already handled in createNewChat with toast
        }
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
