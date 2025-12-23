"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ChatConversation, useChatHistory } from "@/hooks/useChatHistory";

interface ChatHistoryItemProps {
  conversation: ChatConversation;
  isActive: boolean;
}

export function ChatHistoryItem({ conversation, isActive }: ChatHistoryItemProps) {
  const router = useRouter();
  const { deleteChat, renameChat } = useChatHistory();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showRenameDialog, setShowRenameDialog] = useState(false);
  const [newTitle, setNewTitle] = useState(conversation.title);

  const handleRename = () => {
    renameChat(conversation.id, newTitle);
    setShowRenameDialog(false);
  };

  const handleDelete = () => {
    deleteChat(conversation.id);
    setShowDeleteDialog(false);
    // Navigate to new chat after deletion
    router.push("/dashboard/chat/new");
  };

  return (
    <>
      <Link
        href={`/dashboard/chat/${conversation.id}`}
        className={cn(
          "group relative flex items-center rounded-lg px-3 py-2.5 text-sm cursor-pointer transition-colors block",
          isActive
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground hover:bg-sidebar-accent/50"
        )}
      >
        {/* Title with max-width to leave room for button */}
        <span className="truncate pr-8 flex-1">
          {conversation.title}
        </span>

        {/* Three-dots button - always visible on active, visible on hover otherwise */}
        <div
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2 transition-opacity",
            isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
          )}
        >
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <button
                className="p-1.5 rounded-md hover:bg-sidebar-border/50 text-sidebar-foreground/70 hover:text-sidebar-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              side="bottom"
              sideOffset={5}
              className="w-40 z-[100]"
            >
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  setNewTitle(conversation.title);
                  setShowRenameDialog(true);
                }}
              >
                <Pencil className="mr-2 h-4 w-4" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  setShowDeleteDialog(true);
                }}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </Link>

      {/* Rename Dialog */}
      <Dialog open={showRenameDialog} onOpenChange={setShowRenameDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Chat</DialogTitle>
            <DialogDescription>Enter a new name for this conversation.</DialogDescription>
          </DialogHeader>
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Chat name"
            onKeyDown={(e) => e.key === "Enter" && handleRename()}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRenameDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleRename}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Chat?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete "{conversation.title}". This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
