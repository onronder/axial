"use client";

import { useState, useRef, KeyboardEvent, ChangeEvent } from "react";
import { Send, Paperclip, Sparkles, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { validModels, ModelId } from "@/lib/types";

/** Supported file types for attachment */
const ACCEPTED_FILE_TYPES = ".pdf,.doc,.docx,.txt,.md,.json,.csv,.xlsx,.xls";

interface ChatInputProps {
  onSend: (message: string) => void;
  /** Callback when files are selected for attachment */
  onFileSelect?: (files: File[]) => void;
  disabled?: boolean;
  selectedModel: ModelId;
  onModelSelect: (model: ModelId) => void;
}

export function ChatInput({ onSend, onFileSelect, disabled, selectedModel, onModelSelect }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Handle file attachment button click
   */
  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  /**
   * Handle file selection from input
   */
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    // Emit file selection to parent for handling
    onFileSelect?.(Array.from(files));

    // Reset input to allow re-selecting the same file
    e.target.value = '';
  };

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const activeModelName = validModels.find(m => m.id === selectedModel)?.name || 'Axio Fast';

  return (
    <div className="border-t border-border bg-muted/30 backdrop-blur-xl p-4">
      <div className="mx-auto max-w-4xl">
        {/* Model Selector Pill */}
        <div className="mb-2 flex justify-center">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 rounded-full border-border bg-muted/50 px-4 text-xs font-medium text-foreground hover:bg-accent hover:text-accent-foreground transition-all"
              >
                {activeModelName}
                <ChevronDown className="h-3 w-3 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="center" className="w-[200px]" aria-label="Select AI model">
              {validModels.map((model) => (
                <DropdownMenuItem
                  key={model.id}
                  onClick={() => onModelSelect(model.id)}
                  className="flex flex-col items-start gap-0.5 py-2 cursor-pointer"
                  aria-selected={selectedModel === model.id}
                >
                  <span className="font-medium text-sm">{model.name}</span>
                  <span className="text-xs text-muted-foreground">{model.description}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Premium input container with glow effect */}
        <div
          className={`
            relative flex items-end gap-2 rounded-2xl border border-border bg-muted/30 p-2 
            transition-all duration-300
            ${isFocused
              ? 'border-primary/50 shadow-glow ring-2 ring-primary/40'
              : 'shadow-sm hover:border-primary/30 hover:shadow-lg'
            }
          `}
        >
          {/* Gradient border overlay on focus */}
          {isFocused && (
            <div className="absolute inset-0 -z-10 rounded-2xl bg-gradient-to-r from-primary/20 via-accent/20 to-primary/10 blur-2xl opacity-60" />
          )}

          {/* Attachment button - only show if handler provided */}
          {onFileSelect && (
            <>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                multiple
                accept={ACCEPTED_FILE_TYPES}
                className="hidden"
                aria-label="Upload files"
              />
              <Button
                variant="ghost"
                size="icon"
                className="shrink-0 h-9 w-9 text-muted-foreground hover:text-primary hover:bg-accent transition-colors"
                disabled={disabled}
                onClick={handleFileClick}
                aria-label="Attach files"
              >
                <Paperclip className="h-5 w-5" />
              </Button>
            </>
          )}

          {/* Input area */}
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={`Ask ${activeModelName.split(" ")[0]} anything...`}
            className="min-h-[40px] max-h-[200px] flex-1 resize-none border-0 bg-transparent p-2 text-sm focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60 text-foreground"
            rows={1}
            disabled={disabled}
          />

          {/* Send button with gradient */}
          <Button
            onClick={handleSend}
            disabled={!message.trim() || disabled}
            variant="gradient"
            size="icon"
            aria-label="Send message"
            className={`
              shrink-0 h-9 w-9 transition-all duration-300 motion-reduce:transition-none
              ${message.trim() ? 'scale-100 opacity-100 shadow-glow' : 'scale-95 opacity-70 motion-reduce:scale-100'}
            `}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>

        {/* Footer text with AI indicator */}
        <div className="mt-2 flex items-center justify-center gap-1.5 text-xs text-muted-foreground/60">
          <Sparkles className="h-3 w-3" />
          <span>Powered by Axio Hub - Fittechs ©</span>
        </div>
      </div>
    </div>
  );
}
