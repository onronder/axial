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

// --- DATA SOURCES MOCK DATA ---

export interface DataSource {
    id: string;
    name: string;
    type: string;
    status: "active" | "error" | "disconnected" | "connected";
    lastSync: string;
    icon: string;
    description: string;
    category: "files" | "cloud" | "web" | "database" | "apps";
}

export const CATEGORY_LABELS: Record<string, string> = {
    files: "Files",
    cloud: "Cloud Storage",
    web: "Web Resources",
    database: "Databases",
    apps: "Applications",
};

export const DATA_SOURCES: DataSource[] = [
    {
        id: "ds1",
        name: "Google Drive",
        type: "google_drive",
        status: "connected",
        lastSync: "2 mins ago",
        icon: "https://upload.wikimedia.org/wikipedia/commons/1/12/Google_Drive_icon_%282020%29.svg",
        description: "Connect your Google Drive to sync documents.",
        category: "cloud",
    },
    {
        id: "ds2",
        name: "Notion",
        type: "notion",
        status: "disconnected",
        lastSync: "-",
        icon: "https://upload.wikimedia.org/wikipedia/commons/e/e9/Notion-logo.svg",
        description: "Import pages and databases from Notion.",
        category: "apps",
    },
    {
        id: "ds3",
        name: "Website Crawler",
        type: "crawler",
        status: "active",
        lastSync: "1 hour ago",
        icon: "globe",
        description: "Crawl and index your company website.",
        category: "web",
    },
    {
        id: "ds4",
        name: "Local Upload",
        type: "local",
        status: "active",
        lastSync: "Just now",
        icon: "upload",
        description: "Upload PDF, DOCX, and TXT files manually.",
        category: "files",
    },
];

export interface Document {
    id: string;
    name: string;
    source: string;
    sourceType: 'drive' | 'web' | 'upload' | 'notion' | 'slack';
    status: 'indexed' | 'processing' | 'error';
    addedAt: string;
    size?: number;
}

export const mockDocuments: Document[] = [
    { id: '1', name: 'Project Requirements.pdf', source: 'Google Drive', sourceType: 'drive', status: 'indexed', addedAt: new Date().toISOString(), size: 1024 * 1024 * 2.5 },
    { id: '2', name: 'Competitor Analysis', source: 'Notion', sourceType: 'notion', status: 'processing', addedAt: new Date().toISOString() },
    { id: '3', name: 'Q4 Marketing Plan', source: 'Slack', sourceType: 'slack', status: 'indexed', addedAt: new Date(Date.now() - 86400000).toISOString(), size: 1024 * 500 }
];
