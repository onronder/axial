'use client';


import { mockMessages, ChatConversation, Message } from "@/lib/mockData";

export type { ChatConversation };

export const useChatHistory = () => {
    const conversations: ChatConversation[] = [
        { id: "1", title: "Project Analysis", date: new Date().toISOString(), messages: [] },
        { id: "2", title: "Marketing Plan", date: new Date().toISOString(), messages: [] }
    ];

    const getMessagesById = (id: string): Message[] => {
        return mockMessages[id] || [];
    };

    return {
        conversations,
        getMessagesById,
        createNewChat: () => "new-chat-id",
        deleteChat: (id: string) => console.log("Delete", id),
        renameChat: (id: string, title: string) => console.log("Rename", id, title),
    };
};

export interface GroupedConversation {
    label: string;
    conversations: ChatConversation[];
}

export const groupConversationsByDate = (conversations: ChatConversation[]): GroupedConversation[] => {
    return [{ label: "Today", conversations }];
};
