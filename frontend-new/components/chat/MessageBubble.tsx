"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, User } from "lucide-react";
import { Message as MockMessage } from "@/lib/mockData";
import { Source } from "@/types";
import { cn } from "@/lib/utils";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { SourceMetadata } from "./SourceCard";
import { SourcePillList } from "./SourcePill";
import { FeedbackButtons } from "./FeedbackButtons";
import { type FeedbackRating, type SourceSnapshot } from "@/hooks/useFeedback";

interface MessageBubbleProps {
  message: MockMessage & {
    sources?: SourceMetadata[] | Source[];
    warning?: string;
    faithfulness_warning?: string;
    citations_stripped?: number;
  };
  isStreaming?: boolean;
  faithfulness_warning?: string;
  /** The user's question that prompted this response (for feedback context) */
  previousUserQuery?: string;
  /** Current feedback rating for this message (if any) */
  feedbackRating?: FeedbackRating;
  /** Callback when user submits feedback */
  onFeedbackSubmit?: (
    messageId: string,
    rating: FeedbackRating,
    feedbackText?: string
  ) => Promise<void>;
  /** Whether feedback submission is in progress */
  isFeedbackSubmitting?: boolean;
}

const CITATION_REGEX = /\[(\d+)\]/g;

type CitationSegment =
  | { type: "text"; value: string }
  | { type: "citation"; value: number; key: string };

type ParsedLine = {
  kind: "heading" | "bullet" | "text" | "blank";
  segments: CitationSegment[];
};

function parseCitations(content: string): CitationSegment[] {
  CITATION_REGEX.lastIndex = 0;
  const segments: CitationSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = CITATION_REGEX.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", value: content.slice(lastIndex, match.index) });
    }

    const citationNum = parseInt(match[1], 10);
    segments.push({
      type: "citation",
      value: citationNum,
      key: `citation-${match.index}`,
    });

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    segments.push({ type: "text", value: content.slice(lastIndex) });
  }

  return segments.length > 0 ? segments : [{ type: "text", value: content }];
}

function parseLine(line: string): ParsedLine {
  if (line.trim() === "") {
    return { kind: "blank", segments: [] };
  }
  if (line.startsWith("**") && line.endsWith("**")) {
    return { kind: "heading", segments: parseCitations(line.replace(/\*\*/g, "")) };
  }
  if (line.startsWith("- ")) {
    return { kind: "bullet", segments: parseCitations(line.substring(2)) };
  }
  return { kind: "text", segments: parseCitations(line) };
}

function renderSegments(
  segments: CitationSegment[],
  highlightedIndex: number | null,
  setHighlightedIndex: (index: number | null) => void
): React.ReactNode[] {
  return segments.map((segment, idx) => {
    if (segment.type === "text") {
      return segment.value;
    }

    const isHighlighted = highlightedIndex === segment.value;
    return (
      <span
        key={`${segment.key}-${idx}`}
        className={cn(
          "inline-flex items-center justify-center h-4 min-w-4 px-1 mx-0.5 text-[10px] font-bold rounded cursor-pointer",
          "transition-all duration-150 motion-reduce:transition-none",
          isHighlighted
            ? "bg-primary text-primary-foreground ring-2 ring-primary ring-offset-1"
            : "bg-primary/20 text-primary hover:bg-primary/30"
        )}
        role="button"
        tabIndex={0}
        title={`Source ${segment.value}`}
        aria-label={`Citation ${segment.value}, click to highlight source`}
        onMouseEnter={() => setHighlightedIndex(segment.value)}
        onMouseLeave={() => setHighlightedIndex(null)}
        onFocus={() => setHighlightedIndex(segment.value)}
        onBlur={() => setHighlightedIndex(null)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            setHighlightedIndex(isHighlighted ? null : segment.value);
          }
        }}
      >
        {segment.value}
      </span>
    );
  });
}

/**
 * Renders a line of content, handling markdown-like formatting and citations
 */
function renderLine(
  parsed: ParsedLine,
  key: number,
  highlightedIndex: number | null,
  setHighlightedIndex: (index: number | null) => void
): React.ReactNode {
  if (parsed.kind === "blank") {
    return <br key={key} />;
  }

  const content = renderSegments(parsed.segments, highlightedIndex, setHighlightedIndex);

  if (parsed.kind === "heading") {
    return (
      <p key={key} className="font-semibold mt-3 first:mt-0">
        {content}
      </p>
    );
  }

  if (parsed.kind === "bullet") {
    return (
      <li key={key} className="ml-4 list-disc">
        {content}
      </li>
    );
  }

  return (
    <p key={key} className="leading-relaxed">
      {content}
    </p>
  );
}

export function MessageBubble({ 
  message, 
  isStreaming,
  faithfulness_warning,
  previousUserQuery,
  feedbackRating,
  onFeedbackSubmit,
  isFeedbackSubmitting,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const faithfulnessWarningText = faithfulness_warning ?? message.faithfulness_warning;
  const [highlightedCitationIndex, setHighlightedCitationIndex] = useState<number | null>(null);
  const parsedLines = useMemo(
    () => message.content.split("\n").map(parseLine),
    [message.content]
  );

  // Normalize sources to SourceMetadata format
  const normalizedSources: SourceMetadata[] = (message.sources || []).map((source, idx): SourceMetadata => {
    if (typeof source === "string") {
      return {
        index: idx + 1,
        type: "Source",
        label: source,
        url: undefined,
        page: undefined,
        section: undefined,
        source: source,
        source_type: "Source",
        title: source,
        source_url: undefined,
      };
    }

    const base = source as SourceMetadata;
    return {
      index: base.index ?? idx + 1,
      type: base.type ?? base.source_type ?? base.source,
      label: base.label ?? base.title ?? base.source,
      url: base.url ?? base.source_url,
      page: base.page,
      section: base.section,
      // Legacy fields
      source: base.source,
      source_type: base.source_type,
      title: base.title ?? base.label,
      source_url: base.source_url ?? base.url,
    };
  });

  return (
    <div
      className={cn(
        "flex items-start gap-3 animate-fade-in motion-reduce:animate-none",
        isUser && "flex-row-reverse"
      )}
      role="article"
      aria-label={`${isUser ? 'Your' : 'AI'} message`}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-axio-gradient shadow-brand"
            : "bg-muted border border-border"
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
              : "bg-muted/50 border border-border text-foreground backdrop-blur-sm shadow-md"
          )}
        >
          <div
            className={cn("prose prose-sm max-w-none", isUser ? "prose-invert" : "dark:prose-invert")}
            aria-live={isStreaming ? "polite" : undefined}
            aria-busy={isStreaming}
          >
            {parsedLines.map((line, i) =>
              renderLine(line, i, highlightedCitationIndex, setHighlightedCitationIndex)
            )}
            {isStreaming && (
              <span
                className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse motion-reduce:animate-none rounded-sm"
                aria-label="AI is typing"
              />
            )}
          </div>
        </div>

        {!isUser && faithfulnessWarningText && (
          <div
            data-testid="faithfulness-warning-banner"
            className="mt-2 flex items-start gap-2 rounded-md bg-warning/10 px-3 py-2 text-xs text-warning"
          >
            <AlertTriangle
              data-testid="faithfulness-warning-icon"
              className="mt-0.5 h-3.5 w-3.5 flex-shrink-0"
            />
            <span>{faithfulnessWarningText}</span>
          </div>
        )}

        {/* Source Citations - Inline pills matching marketing design */}
        {!isUser && normalizedSources.length > 0 && (
          <SourcePillList
            sources={normalizedSources}
            className="mt-3"
            highlightedIndex={highlightedCitationIndex}
            onSourceHover={setHighlightedCitationIndex}
          />
        )}
        
        {/* Feedback Buttons - Only for assistant messages, not during streaming */}
        {!isUser && !isStreaming && onFeedbackSubmit && message.id && (
          <FeedbackButtons
            messageId={message.id}
            sources={normalizedSources.map((s): SourceSnapshot => ({
              index: s.index,
              type: s.type,
              label: s.label,
              url: s.url,
              page: s.page,
              section: s.section,
            }))}
            queryText={previousUserQuery || ""}
            answerPreview={message.content.slice(0, 500)}
            currentRating={feedbackRating}
            onSubmit={onFeedbackSubmit}
            isSubmitting={isFeedbackSubmitting}
            className="mt-2"
          />
        )}
      </div>
    </div>
  );
}
