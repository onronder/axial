"use client";

import { MessageSquare } from "lucide-react";
import { useParams } from "next/navigation";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatHistory, groupConversationsByDate } from "@/hooks/useChatHistory";
import { ChatHistoryItem } from "./ChatHistoryItem";

export function ChatHistoryList() {
  const { chatId } = useParams();
  const { conversations } = useChatHistory();

  const groupedConversations = groupConversationsByDate(conversations);

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
    <ScrollArea className="flex-1">
      <div className="space-y-4 px-2">
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
    </ScrollArea>
  );
}
