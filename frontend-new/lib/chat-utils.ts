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
