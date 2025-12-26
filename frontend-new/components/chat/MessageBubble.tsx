import { User } from "lucide-react";
import { Message } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { SourceCardGrid, SourceMetadata } from "./SourceCard";

interface MessageBubbleProps {
  message: Message & { sources?: SourceMetadata[] };
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex items-start gap-3 animate-fade-in",
        isUser && "flex-row-reverse"
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-axio-gradient shadow-brand"
            : "bg-muted"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <AxioLogo variant="icon" size="sm" />
        )}
      </div>
      <div className={cn("max-w-[80%]", isUser && "text-right")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3",
            isUser
              ? "bg-axio-gradient text-white shadow-brand"
              : "bg-muted text-foreground"
          )}
        >
          <div className={cn("prose prose-sm max-w-none", isUser ? "prose-invert" : "dark:prose-invert")}>
            {message.content.split("\n").map((line: string, i: number) => {
              if (line.startsWith("**") && line.endsWith("**")) {
                return (
                  <p key={i} className="font-semibold mt-3 first:mt-0">
                    {line.replace(/\*\*/g, "")}
                  </p>
                );
              }
              if (line.startsWith("- ")) {
                return (
                  <li key={i} className="ml-4 list-disc">
                    {line.substring(2)}
                  </li>
                );
              }
              if (line.trim() === "") {
                return <br key={i} />;
              }
              return <p key={i} className="leading-relaxed">{line}</p>;
            })}
            {isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse rounded-sm" />
            )}
          </div>
        </div>

        {/* Source Citations */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCardGrid sources={message.sources} className="mt-2" />
        )}
      </div>
    </div>
  );
}