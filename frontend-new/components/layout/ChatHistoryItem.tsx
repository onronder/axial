"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { MoreHorizontal, Pencil, Trash2, Loader2 } from "lucide-react";
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
  const params = useParams();
  const currentChatId = params.chatId as string;

  const { deleteChat, renameChat } = useChatHistory();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showRenameDialog, setShowRenameDialog] = useState(false);
  const [newTitle, setNewTitle] = useState(conversation.title);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleRename = async () => {
    await renameChat(conversation.id, newTitle);
    setShowRenameDialog(false);
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteChat(conversation.id);
      setShowDeleteDialog(false);

      // Only navigate if we're currently viewing the deleted chat
      if (currentChatId === conversation.id) {
        router.replace("/dashboard/chat/new");
      }
    } catch (error) {
      console.error("Delete failed:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      {/* 
        CRITICAL FIX: Dropdown is now OUTSIDE the Link component.
        This prevents clicks on the menu from triggering navigation.
      */}
      <div className="group relative flex items-center">
        {/* Chat Link - navigates to conversation */}
        <Link
          href={`/dashboard/chat/${conversation.id}`}
          className={cn(
            "flex-1 flex items-center rounded-lg px-3 py-2.5 text-sm cursor-pointer transition-all duration-150 pr-10",
            isActive
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-sidebar-foreground hover:bg-sidebar-accent/50"
          )}
        >
          <span className="flex-1 min-w-0 truncate">
            {conversation.title}
          </span>
        </Link>

        {/* Three-dots menu - OUTSIDE the Link, positioned absolutely */}
        <div
          className={cn(
            "absolute right-1 top-1/2 -translate-y-1/2 shrink-0 transition-opacity duration-150",
            isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
          )}
        >
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className={cn(
                  "flex items-center justify-center w-7 h-7 rounded-md transition-colors",
                  "bg-sidebar-accent hover:bg-sidebar-border",
                  "text-sidebar-foreground/70 hover:text-sidebar-foreground",
                  "focus:outline-none focus:ring-2 focus:ring-primary/50"
                )}
                onClick={(e) => {
                  // Prevent any bubbling to parent elements
                  e.stopPropagation();
                }}
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
                onSelect={(e) => {
                  e.preventDefault();
                  setNewTitle(conversation.title);
                  setShowRenameDialog(true);
                }}
              >
                <Pencil className="mr-2 h-4 w-4" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={(e) => {
                  e.preventDefault();
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
      </div>

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
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
