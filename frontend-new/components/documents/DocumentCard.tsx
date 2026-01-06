/**
 * Document Card Component
 * 
 * Individual document card with delete functionality.
 */

"use client";

import { FileText, Trash2, Calendar, HardDrive } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from '@/components/ui/alert-dialog';


import { Document } from '@/types';

interface DocumentCardProps {
    document: Document;
    viewMode: 'grid' | 'list';
    onDelete: () => void;
}

function formatFileSize(bytes: number | undefined): string {
    if (!bytes || bytes < 1024) return `${bytes || 0} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
}

export function DocumentCard({ document, viewMode, onDelete }: DocumentCardProps) {
    if (viewMode === 'list') {
        return (
            <Card className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center gap-4">
                    <div className="flex-shrink-0">
                        <div className="rounded-lg bg-primary/10 p-3">
                            <FileText className="h-6 w-6 text-primary" />
                        </div>
                    </div>

                    <div className="flex-1 min-w-0">
                        <h3 className="font-medium truncate">{document.name}</h3>
                        <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                                <HardDrive className="h-3 w-3" />
                                {formatFileSize(document.size)}
                            </span>
                            <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {formatDate(document.addedAt)}
                            </span>
                            <span>{document.source}</span>
                        </div>
                    </div>

                    <AlertDialog>
                        <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="icon" className="flex-shrink-0">
                                <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                            <AlertDialogHeader>
                                <AlertDialogTitle>Delete Document?</AlertDialogTitle>
                                <AlertDialogDescription>
                                    This will permanently delete "{document.name}" and all its data.
                                    This action cannot be undone.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={onDelete} className="bg-destructive hover:bg-destructive/90">
                                    Delete
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>
                </div>
            </Card>
        );
    }

    // Grid view
    return (
        <Card className="p-6 hover:shadow-lg transition-all duration-300 group">
            <div className="space-y-4">
                <div className="flex items-start justify-between">
                    <div className="rounded-lg bg-primary/10 p-3 group-hover:bg-primary/20 transition-colors">
                        <FileText className="h-8 w-8 text-primary" />
                    </div>

                    <AlertDialog>
                        <AlertDialogTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                            <AlertDialogHeader>
                                <AlertDialogTitle>Delete Document?</AlertDialogTitle>
                                <AlertDialogDescription>
                                    This will permanently delete "{document.name}" and all its data.
                                    This action cannot be undone.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={onDelete} className="bg-destructive hover:bg-destructive/90">
                                    Delete
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>
                </div>

                <div>
                    <h3 className="font-semibold truncate" title={document.name}>
                        {document.name}
                    </h3>
                    <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                            <HardDrive className="h-3 w-3" />
                            {formatFileSize(document.size)}
                        </div>
                        <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(document.addedAt)}
                        </div>
                        <div>{document.source}</div>
                    </div>
                </div>
            </div>
        </Card>
    );
}
