/**
 * Document List Component
 * 
 * Displays all user documents with search and delete functionality.
 */

"use client";

import { useState, useMemo } from 'react';
import { Search, Grid, List, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useDocuments } from '@/hooks/useDocuments';
import { DocumentCard } from './DocumentCard';
import { cn } from '@/lib/utils';
import { useDebounce } from 'use-debounce';

type ViewMode = 'grid' | 'list';

export function DocumentList() {
    const { documents, isLoading, deleteDocument } = useDocuments();
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState<ViewMode>('grid');

    // ✅ PERFORMANCE: Debounce search to prevent excessive filtering
    const [debouncedSearch] = useDebounce(searchQuery, 300);

    const filteredDocuments = useMemo(() => {
        return documents.filter(doc =>
            doc.name.toLowerCase().includes(debouncedSearch.toLowerCase())
        );
    }, [documents, debouncedSearch]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="flex flex-col items-center gap-3">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground">Loading documents...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header with Search and View Toggle */}
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search documents..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                </div>

                <div className="flex gap-2">
                    <Button
                        variant={viewMode === 'grid' ? 'default' : 'outline'}
                        size="icon"
                        onClick={() => setViewMode('grid')}
                        aria-label="Grid view"
                    >
                        <Grid className="h-4 w-4" />
                    </Button>
                    <Button
                        variant={viewMode === 'list' ? 'default' : 'outline'}
                        size="icon"
                        onClick={() => setViewMode('list')}
                        aria-label="List view"
                    >
                        <List className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Document Count */}
            <div className="text-sm text-muted-foreground">
                {filteredDocuments.length} {filteredDocuments.length === 1 ? 'document' : 'documents'}
                {searchQuery && ` matching "${searchQuery}"`}
            </div>

            {/* Documents Grid/List */}
            {filteredDocuments.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-muted-foreground">
                        {searchQuery ? 'No documents found' : 'No documents yet'}
                    </p>
                </div>
            ) : (
                <div
                    className={cn(
                        viewMode === 'grid'
                            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
                            : 'space-y-2'
                    )}
                >
                    {filteredDocuments.map(doc => (
                        <DocumentCard
                            key={doc.id}
                            document={doc}
                            viewMode={viewMode}
                            onDelete={() => deleteDocument(doc.id)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
