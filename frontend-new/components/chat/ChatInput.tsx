"use client";

import { useState, useRef, KeyboardEvent } from "react";
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

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  selectedModel: ModelId;
  onModelSelect: (model: ModelId) => void;
}

export function ChatInput({ onSend, disabled, selectedModel, onModelSelect }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  // Internal state removed: const [selectedModel, setSelectedModel] = useState<ModelId>('fast');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
    <div className="border-t border-border bg-background/95 backdrop-blur-xl p-4">
      <div className="mx-auto max-w-3xl">
        {/* Model Selector Pill */}
        <div className="mb-2 flex justify-center">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-7 gap-1.5 rounded-full border-primary/20 bg-primary/5 px-3 text-xs font-medium text-primary hover:bg-primary/10 hover:text-primary transition-all"
              >
                {activeModelName}
                <ChevronDown className="h-3 w-3 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="center" className="w-[200px]">
              {validModels.map((model) => (
                <DropdownMenuItem
                  key={model.id}
                  onClick={() => onModelSelect(model.id)}
                  className="flex flex-col items-start gap-0.5 py-2 cursor-pointer"
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
            relative flex items-end gap-2 rounded-2xl border bg-card p-2 
            transition-all duration-300
            ${isFocused
              ? 'border-primary/50 shadow-lg shadow-primary/10 ring-4 ring-primary/5'
              : 'border-border shadow-sm hover:border-primary/30 hover:shadow-md'
            }
          `}
        >
          {/* Gradient border overlay on focus */}
          {isFocused && (
            <div className="absolute inset-0 -z-10 rounded-2xl bg-gradient-to-r from-primary/20 via-accent/20 to-primary/20 blur-xl opacity-50" />
          )}

          {/* Attachment button */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 h-9 w-9 text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
            disabled={disabled}
          >
            <Paperclip className="h-5 w-5" />
          </Button>

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
            className="min-h-[40px] max-h-[200px] flex-1 resize-none border-0 bg-transparent p-2 text-sm focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60"
            rows={1}
            disabled={disabled}
          />

          {/* Send button with gradient */}
          <Button
            onClick={handleSend}
            disabled={!message.trim() || disabled}
            variant="gradient"
            size="icon"
            className={`
              shrink-0 h-9 w-9 transition-all duration-300
              ${message.trim() ? 'scale-100 opacity-100' : 'scale-95 opacity-70'}
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