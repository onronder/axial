'use client';

export interface ChatConversation {
    id: string;
    title: string;
    date: string;
}

export const useChatHistory = () => {
    const conversations: ChatConversation[] = [
        { id: "1", title: "Project Analysis", date: new Date().toISOString() },
        { id: "2", title: "Marketing Plan", date: new Date().toISOString() }
    ];

    return {
        conversations,
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
