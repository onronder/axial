"use client";

import { useMemo } from "react";
import { MessageSquare, Loader2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useChatHistory, groupConversationsByDate } from "@/hooks/useChatHistory";
import { ChatHistoryItem } from "./ChatHistoryItem";

/**
 * Chat history list component with grouping by date.
 * 
 * Features:
 * - Groups chats by Today, Yesterday, Previous 7 Days, Older
 * - Loading skeleton while fetching
 * - Empty state for new users
 * - Memoized grouping for performance
 */
export function ChatHistoryList() {
  const { chatId } = useParams();
  const { conversations, isLoading } = useChatHistory();

  // Memoize grouping to avoid recalculation on every render
  const groupedConversations = useMemo(
    () => groupConversationsByDate(conversations),
    [conversations]
  );

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-2 px-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="h-10 bg-sidebar-accent/30 rounded-md animate-pulse"
            style={{ opacity: 1 - i * 0.15 }}
          />
        ))}
      </div>
    );
  }

  // Empty state
  if (conversations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
        <MessageSquare className="h-8 w-8 text-sidebar-foreground/30 mb-2" />
        <p className="text-sm text-sidebar-foreground/50">No conversations yet</p>
        <p className="text-xs text-sidebar-foreground/40 mt-1">Start a new chat to begin</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 px-2 pr-1">
      {groupedConversations.map((group) => (
        <div key={group.label}>
          <p className="px-2 py-1 text-xs font-medium text-sidebar-foreground/50 uppercase tracking-wider">
            {group.label}
          </p>
          <div className="space-y-0.5">
            {group.conversations.map((conversation) => (
              <ChatHistoryItem
                key={conversation.id}
                conversation={conversation}
                isActive={chatId === conversation.id}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
