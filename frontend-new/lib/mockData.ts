export interface User {
    id: string;
    name: string;
    avatar?: string;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
}

export interface ChatConversation {
    id: string;
    title: string;
    date: string;
    messages: Message[];
}

// Starter Queries for Empty State
export const starterQueries = [
    {
        title: "Summarize this document",
        description: "Get a quick overview of the key points",
        icon: "file-text",
    },
    {
        title: "Analyze risks",
        description: "Identify potential issues and concerns",
        icon: "alert-triangle",
    },
    {
        title: "Compare versions",
        description: "See what changed between document versions",
        icon: "git-compare",
    },
    {
        title: "Extract data",
        description: "Pull specific data points into a table",
        icon: "file-bar-chart",
    },
];

// Dummy Data
export const mockUsers: User[] = [
    { id: '1', name: 'John Doe', avatar: '' }
];

export const mockConversations: ChatConversation[] = [
    {
        id: '1',
        title: 'Project Analysis',
        date: new Date().toISOString(),
        messages: [
            { id: 'm1', role: 'user', content: 'Analyze this data.', timestamp: new Date().toISOString() },
            { id: 'm2', role: 'assistant', content: 'Sure, here is the summary...', timestamp: new Date().toISOString() }
        ]
    }
];

// Map for easier path/id lookup if legacy code needs it
export const mockMessages: Record<string, Message[]> = {
    "1": mockConversations[0].messages,
    "2": []
};
