/**
 * Chat-related utility functions
 */

/**
 * Generate a smart, concise title from the user's first message.
 * Similar to how Claude, Gemini, and ChatGPT auto-name conversations.
 */
export function generateSmartTitle(message: string): string {
    let title = message.trim();

    // Remove common question starters for cleaner titles
    const questionPrefixes = [
        /^(what is|what's|what are|whats)\s+/i,
        /^(how do i|how can i|how to)\s+/i,
        /^(can you|could you|would you)\s+/i,
        /^(tell me about|explain|describe)\s+/i,
        /^(i want to|i need to|i'm trying to)\s+/i,
        /^(help me|please help)\s+/i,
        /^(hi,?\s*|hello,?\s*|hey,?\s*)/i,
    ];

    for (const prefix of questionPrefixes) {
        title = title.replace(prefix, '');
    }

    // Capitalize first letter
    title = title.charAt(0).toUpperCase() + title.slice(1);

    // Truncate to reasonable length (max 50 chars)
    if (title.length > 50) {
        const truncated = title.substring(0, 50);
        const lastSpace = truncated.lastIndexOf(' ');
        title = lastSpace > 30 ? truncated.substring(0, lastSpace) + '...' : truncated + '...';
    }

    // Remove trailing punctuation for cleaner look
    title = title.replace(/[?.!,;:]+$/, '');

    // Fallback for empty/short titles
    return title.length < 3 ? 'New conversation' : title;
}

/**
 * Stream chat response from backend using SSE.
 * Yields tokens as they arrive.
 */
import { supabase } from '@/lib/supabase';
import { ModelId } from '@/lib/types';

export interface ChatPayload {
    query: string;
    conversation_id: string | null;
    history: { role: string; content: string }[];
    model: ModelId;
}

export type StreamEvent =
    | { type: 'token'; content: string }
    | { type: 'sources'; sources: any[] }
    | { type: 'done'; message_id?: string }
    | { type: 'error'; message: string };

export async function* streamChatResponse(payload: ChatPayload): AsyncGenerator<StreamEvent, void, unknown> {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    if (!token) {
        throw new Error("No authentication token found");
    }

    const response = await fetch('/api/py/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ...payload, stream: true }),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Chat API error: ${response.status} - ${errorText}`);
    }

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ""; // Keep incomplete chunk

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    if (jsonStr.trim() === '[DONE]') continue; // Standard SSE done

                    try {
                        const event = JSON.parse(jsonStr) as StreamEvent;
                        yield event;
                    } catch (e) {
                        console.warn("Failed to parse SSE event:", jsonStr);
                    }
                }
            }
        }
    } finally {
        reader.releaseLock();
    }
}
