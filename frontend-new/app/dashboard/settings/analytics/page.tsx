'use client';

/**
 * Feedback Analytics Dashboard
 * 
 * Shows chat response quality analytics for team admins.
 * Includes:
 * - Summary statistics (positive/negative rates)
 * - Recent negative feedback with context
 * - Source quality metrics (problematic documents)
 * 
 * Related Files:
 * - backend/api/v1/feedback.py (API endpoints)
 * - docs/ChatFeedback_Implementation_Spec.md (specification)
 */

import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    BarChart3,
    ThumbsUp,
    ThumbsDown,
    FileText,
    RefreshCw,
    TrendingDown,
    AlertTriangle,
    MessageSquare,
    ShieldAlert,
    Calendar,
} from 'lucide-react';
import { SettingsPageHeader } from "@/components/settings/SettingsPageHeader";
import { SettingsStatCard } from "@/components/settings/SettingsStatCard";
import { SettingsEmptyState } from "@/components/settings/SettingsEmptyState";
import { subDays, format, startOfDay, endOfDay } from 'date-fns';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { useProfile } from '@/hooks/useProfile';

// =============================================================================
// Types
// =============================================================================

interface FeedbackSummary {
    positive_count: number;
    negative_count: number;
    total_count: number;
    negative_rate_pct: number;
}

interface FeedbackItem {
    id: string;
    rating: 'positive' | 'negative';
    feedback_text: string | null;
    query_text: string;
    answer_preview: string;
    sources: Array<{
        label?: string;
        type?: string;
        url?: string;
    }>;
    user_email: string;
    created_at: string;
}

interface FeedbackResponse {
    items: FeedbackItem[];
    total: number;
    has_more: boolean;
    summary: FeedbackSummary;
}

interface SourceMetric {
    source_label: string;
    source_type: string | null;
    source_url: string | null;
    positive_count: number;
    negative_count: number;
    total_feedback: number;
    negative_rate_pct: number;
    last_feedback_at: string | null;
}

interface SourceMetricsResponse {
    items: SourceMetric[];
    total: number;
}

// =============================================================================
// Date Range Presets
// =============================================================================

interface DateRange {
    from: Date | null;
    to: Date | null;
}

const DATE_RANGE_PRESETS = [
    { label: 'Last 7 days', value: '7d', getDates: () => ({ from: subDays(new Date(), 7), to: new Date() }) },
    { label: 'Last 30 days', value: '30d', getDates: () => ({ from: subDays(new Date(), 30), to: new Date() }) },
    { label: 'Last 90 days', value: '90d', getDates: () => ({ from: subDays(new Date(), 90), to: new Date() }) },
    { label: 'All time', value: 'all', getDates: () => ({ from: null, to: null }) },
];

// =============================================================================
// API Functions
// =============================================================================

async function fetchFeedback(
    rating?: string, 
    limit: number = 20,
    fromDate?: Date | null,
    toDate?: Date | null
): Promise<FeedbackResponse> {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    if (rating) params.set('rating', rating);
    if (fromDate) params.set('from_date', startOfDay(fromDate).toISOString());
    if (toDate) params.set('to_date', endOfDay(toDate).toISOString());
    
    const response = await api.get(`/analytics/feedback?${params.toString()}`);
    return response.data;
}

async function fetchSourceMetrics(
    fromDate?: Date | null,
    toDate?: Date | null
): Promise<SourceMetricsResponse> {
    const params = new URLSearchParams();
    params.set('min_feedback_count', '3');
    params.set('limit', '10');
    if (fromDate) params.set('from_date', startOfDay(fromDate).toISOString());
    if (toDate) params.set('to_date', endOfDay(toDate).toISOString());
    
    const response = await api.get(`/analytics/feedback/sources?${params.toString()}`);
    return response.data;
}

// =============================================================================
// Component
// =============================================================================

export default function FeedbackAnalyticsPage() {
    const { profile, isLoading: profileLoading } = useProfile();
    const [ratingFilter, setRatingFilter] = useState<string>('all');
    const [feedbackLimit, setFeedbackLimit] = useState(20);
    const [dateRangePreset, setDateRangePreset] = useState<string>('30d');
    const [dateRange, setDateRange] = useState<DateRange>(() => 
        DATE_RANGE_PRESETS.find(p => p.value === '30d')?.getDates() ?? { from: null, to: null }
    );
    
    // Handle date range preset change
    const handleDateRangeChange = useCallback((preset: string) => {
        setDateRangePreset(preset);
        const presetConfig = DATE_RANGE_PRESETS.find(p => p.value === preset);
        if (presetConfig) {
            setDateRange(presetConfig.getDates());
        }
        setFeedbackLimit(20); // Reset pagination
    }, []);
    
    // Reset limit when filter changes
    useEffect(() => {
        setFeedbackLimit(20);
    }, [ratingFilter]);
    
    // Authorization check - only admins and owners can view analytics
    const isAuthorized = !profile?.role || profile?.role === 'admin'; // No role means owner
    
    // Fetch feedback data
    const { 
        data: feedbackData, 
        isLoading: feedbackLoading, 
        isFetching: feedbackFetching,
        error: feedbackError,
        refetch: refetchFeedback,
    } = useQuery({
        queryKey: ['feedback', ratingFilter, feedbackLimit, dateRange.from?.toISOString(), dateRange.to?.toISOString()],
        queryFn: () => fetchFeedback(
            ratingFilter === 'all' ? undefined : ratingFilter, 
            feedbackLimit,
            dateRange.from,
            dateRange.to
        ),
        staleTime: 60_000, // 1 minute
        enabled: isAuthorized && !profileLoading,
    });
    
    // Fetch source metrics
    const { 
        data: sourceMetrics, 
        isLoading: metricsLoading,
        refetch: refetchMetrics,
    } = useQuery({
        queryKey: ['sourceMetrics', dateRange.from?.toISOString(), dateRange.to?.toISOString()],
        queryFn: () => fetchSourceMetrics(dateRange.from, dateRange.to),
        staleTime: 60_000,
        enabled: isAuthorized && !profileLoading,
    });
    
    const handleRefresh = useCallback(() => {
        refetchFeedback();
        refetchMetrics();
    }, [refetchFeedback, refetchMetrics]);
    
    const handleLoadMore = useCallback(() => {
        setFeedbackLimit(prev => prev + 20);
    }, []);
    
    // Loading state while checking authorization
    if (profileLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Spinner className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }
    
    // Authorization check - show access denied for non-admins
    if (!isAuthorized) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <ShieldAlert className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
                    <p className="text-muted-foreground">
                        Analytics are only available to team admins and owners.
                    </p>
                </div>
            </div>
        );
    }
    
    const summary = feedbackData?.summary;
    
    return (
        <div className="space-y-8">
            <SettingsPageHeader
                icon={BarChart3}
                title="Analytics"
                description="Monitor AI response quality based on user feedback"
                actions={
                    <div className="flex items-center gap-2">
                        <Select value={dateRangePreset} onValueChange={handleDateRangeChange}>
                            <SelectTrigger className="w-[150px]">
                                <Calendar className="h-4 w-4 mr-2" />
                                <SelectValue placeholder="Date range" />
                            </SelectTrigger>
                            <SelectContent>
                                {DATE_RANGE_PRESETS.map((preset) => (
                                    <SelectItem key={preset.value} value={preset.value}>
                                        {preset.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleRefresh}
                            className="gap-2"
                        >
                            <RefreshCw className="h-4 w-4" />
                            Refresh
                        </Button>
                    </div>
                }
            />
            
            {/* Date Range Display */}
            {dateRange.from && dateRange.to && (
                <p className="text-sm text-muted-foreground -mt-4">
                    Showing data from {format(dateRange.from, 'MMM d, yyyy')} to {format(dateRange.to, 'MMM d, yyyy')}
                </p>
            )}
            
            {/* Summary Cards */}
            <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
                <SettingsStatCard
                    icon={MessageSquare}
                    iconColorClass="text-primary"
                    iconBgClass="bg-primary/10"
                    label="Total Feedback"
                    value={feedbackLoading ? "..." : summary?.total_count ?? 0}
                />
                <SettingsStatCard
                    icon={ThumbsUp}
                    iconColorClass="text-green-500"
                    iconBgClass="bg-green-500/10"
                    label="Positive"
                    value={feedbackLoading ? "..." : summary?.positive_count ?? 0}
                    className="border-green-200 dark:border-green-900"
                />
                <SettingsStatCard
                    icon={ThumbsDown}
                    iconColorClass="text-red-500"
                    iconBgClass="bg-red-500/10"
                    label="Negative"
                    value={feedbackLoading ? "..." : summary?.negative_count ?? 0}
                    className="border-red-200 dark:border-red-900"
                />
                <SettingsStatCard
                    icon={TrendingDown}
                    iconColorClass="text-amber-500"
                    iconBgClass="bg-amber-500/10"
                    label="Negative Rate"
                    value={feedbackLoading ? "..." : `${summary?.negative_rate_pct ?? 0}%`}
                    description={
                        (summary?.negative_rate_pct ?? 0) > 20
                            ? "Above average"
                            : "Looking good"
                    }
                />
            </div>
            
            {/* Source Quality Metrics */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                        <CardTitle>Problem Sources</CardTitle>
                    </div>
                    <CardDescription>
                        Documents that frequently appear in negative feedback
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {metricsLoading ? (
                        <div className="space-y-2">
                            {[...Array(5)].map((_, i) => (
                                <Skeleton key={i} className="h-12 w-full" />
                            ))}
                        </div>
                    ) : sourceMetrics?.items.length === 0 ? (
                        <SettingsEmptyState
                            icon={FileText}
                            title="No problem sources identified yet"
                            description="Sources with 3+ feedback ratings will appear here"
                        />
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Source</TableHead>
                                    <TableHead>Type</TableHead>
                                    <TableHead className="text-center">👍</TableHead>
                                    <TableHead className="text-center">👎</TableHead>
                                    <TableHead className="text-right">Negative Rate</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {sourceMetrics?.items.map((source) => (
                                    <TableRow key={`${source.source_label}-${source.source_type}`}>
                                        <TableCell className="font-medium max-w-[200px] truncate">
                                            {source.source_label}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="text-xs">
                                                {source.source_type || 'Unknown'}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-center text-green-600">
                                            {source.positive_count}
                                        </TableCell>
                                        <TableCell className="text-center text-red-600">
                                            {source.negative_count}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <span className={cn(
                                                "font-medium",
                                                source.negative_rate_pct > 50 
                                                    ? "text-red-600" 
                                                    : source.negative_rate_pct > 25 
                                                        ? "text-amber-600" 
                                                        : "text-muted-foreground"
                                            )}>
                                                {source.negative_rate_pct}%
                                            </span>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
            
            {/* Recent Feedback */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <BarChart3 className="h-5 w-5" />
                            <CardTitle>Recent Feedback</CardTitle>
                        </div>
                        <Select value={ratingFilter} onValueChange={setRatingFilter}>
                            <SelectTrigger className="w-[150px]">
                                <SelectValue placeholder="Filter by rating" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Ratings</SelectItem>
                                <SelectItem value="positive">Positive Only</SelectItem>
                                <SelectItem value="negative">Negative Only</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <CardDescription>
                        User feedback on AI responses
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {feedbackLoading ? (
                        <div className="space-y-4">
                            {[...Array(5)].map((_, i) => (
                                <Skeleton key={i} className="h-24 w-full" />
                            ))}
                        </div>
                    ) : feedbackError ? (
                        <div className="text-center py-8 text-muted-foreground">
                            <p>Failed to load feedback. You may not have admin access.</p>
                        </div>
                    ) : feedbackData?.items.length === 0 ? (
                        <SettingsEmptyState
                            icon={MessageSquare}
                            title="No feedback collected yet"
                            description="User ratings on AI responses will appear here"
                        />
                    ) : (
                        <div className="space-y-4">
                            {feedbackData?.items.map((item) => (
                                <FeedbackCard key={item.id} feedback={item} />
                            ))}
                            
                            {feedbackData?.has_more && (
                                <div className="text-center pt-4">
                                    <Button 
                                        variant="outline" 
                                        size="sm"
                                        onClick={handleLoadMore}
                                        disabled={feedbackFetching}
                                    >
                                        {feedbackFetching && <Spinner className="h-4 w-4 mr-2 animate-spin" />}
                                        Load More
                                    </Button>
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

// =============================================================================
// Sub-components
// =============================================================================

interface FeedbackCardProps {
    feedback: FeedbackItem;
}

function FeedbackCard({ feedback }: FeedbackCardProps) {
    const isNegative = feedback.rating === 'negative';
    
    return (
        <div className={cn(
            "p-4 rounded-lg border",
            isNegative 
                ? "border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/20" 
                : "border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-950/20"
        )}>
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0 space-y-2">
                    {/* Query */}
                    <div>
                        <p className="text-xs font-medium text-muted-foreground">Question</p>
                        <p className="text-sm truncate">{feedback.query_text}</p>
                    </div>
                    
                    {/* Answer Preview */}
                    <div>
                        <p className="text-xs font-medium text-muted-foreground">Response</p>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                            {feedback.answer_preview}
                        </p>
                    </div>
                    
                    {/* Comment (if any) */}
                    {feedback.feedback_text && (
                        <div className="pt-2 border-t">
                            <p className="text-xs font-medium text-muted-foreground">User Comment</p>
                            <p className="text-sm italic">&quot;{feedback.feedback_text}&quot;</p>
                        </div>
                    )}
                    
                    {/* Sources */}
                    {feedback.sources.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                            {feedback.sources.slice(0, 3).map((source, i) => (
                                <Badge key={i} variant="secondary" className="text-xs">
                                    {source.label || source.type || 'Source'}
                                </Badge>
                            ))}
                            {feedback.sources.length > 3 && (
                                <Badge variant="secondary" className="text-xs">
                                    +{feedback.sources.length - 3} more
                                </Badge>
                            )}
                        </div>
                    )}
                </div>
                
                {/* Rating & Meta */}
                <div className="flex flex-col items-end gap-1 text-right shrink-0">
                    <div className={cn(
                        "p-2 rounded-full",
                        isNegative ? "bg-red-100 dark:bg-red-900/30" : "bg-green-100 dark:bg-green-900/30"
                    )}>
                        {isNegative ? (
                            <ThumbsDown className="h-4 w-4 text-red-600 dark:text-red-400" />
                        ) : (
                            <ThumbsUp className="h-4 w-4 text-green-600 dark:text-green-400" />
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                        {feedback.user_email}
                    </p>
                    <p className="text-xs text-muted-foreground">
                        {new Date(feedback.created_at).toLocaleDateString()}
                    </p>
                </div>
            </div>
        </div>
    );
}
