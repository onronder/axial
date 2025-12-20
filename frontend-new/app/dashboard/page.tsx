"use client";

import { ChatArea } from "@/components/chat/ChatArea";

export default function DashboardPage() {
    // Dashboard now just shows ChatArea with no conversation
    // Chat will be created when user sends first message
    return (
        <div className="h-full">
            <ChatArea />
        </div>
    );
}
