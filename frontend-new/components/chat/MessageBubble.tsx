import { User } from "lucide-react";
import { Message } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { SourceCardGrid, SourceMetadata } from "./SourceCard";

interface MessageBubbleProps {
  message: Message & { sources?: SourceMetadata[] };
  isStreaming?: boolean;
}

/**
 * Renders content with inline citations [1], [2] as styled badges
 */
function renderContentWithCitations(content: string): React.ReactNode[] {
  // Match citation patterns like [1], [2], [3], [1][2], etc.
  const citationPattern = /\[(\d+)\]/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = citationPattern.exec(content)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }

    // Add citation badge
    const citationNum = match[1];
    parts.push(
      <span
        key={`citation-${match.index}`}
        className="inline-flex items-center justify-center h-4 min-w-4 px-1 mx-0.5 text-[10px] font-bold rounded bg-primary/20 text-primary cursor-pointer hover:bg-primary/30 transition-colors"
        title={`Source ${citationNum}`}
      >
        {citationNum}
      </span>
    );

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
}

/**
 * Renders a line of content, handling markdown-like formatting and citations
 */
function renderLine(line: string, key: number): React.ReactNode {
  if (line.startsWith("**") && line.endsWith("**")) {
    return (
      <p key={key} className="font-semibold mt-3 first:mt-0">
        {renderContentWithCitations(line.replace(/\*\*/g, ""))}
      </p>
    );
  }
  if (line.startsWith("- ")) {
    return (
      <li key={key} className="ml-4 list-disc">
        {renderContentWithCitations(line.substring(2))}
      </li>
    );
  }
  if (line.trim() === "") {
    return <br key={key} />;
  }
  return (
    <p key={key} className="leading-relaxed">
      {renderContentWithCitations(line)}
    </p>
  );
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
            {message.content.split("\n").map((line: string, i: number) =>
              renderLine(line, i)
            )}
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