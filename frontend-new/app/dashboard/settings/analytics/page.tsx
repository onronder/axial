'use client';

/**
 * Feedback Analytics Dashboard
 *
 * Shows chat response quality analytics for team admins.
 * Includes:
 * - Summary statistics (positive/negative rates)
 * - Trend chart from dedicated endpoint (full date range, not paginated subset)
 * - Source quality metrics (problematic documents)
 * - Recent feedback with context
 *
 * Related Files:
 * - backend/api/v1/feedback.py (API endpoints)
 * - hooks/useAnalytics.ts (data fetching hook)
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
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
import { subDays, format } from 'date-fns';
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
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import useAnalytics, { type FeedbackItem, type DateRange } from '@/hooks/useAnalytics';

// =============================================================================
// Date Range Presets
// =============================================================================

const DATE_RANGE_PRESETS = [
    { label: 'Last 7 days', value: '7d', getDates: () => ({ from: subDays(new Date(), 7), to: new Date() }) },
    { label: 'Last 30 days', value: '30d', getDates: () => ({ from: subDays(new Date(), 30), to: new Date() }) },
    { label: 'Last 90 days', value: '90d', getDates: () => ({ from: subDays(new Date(), 90), to: new Date() }) },
    { label: 'All time', value: 'all', getDates: () => ({ from: null, to: null }) },
];

// =============================================================================
// Chart Configuration
// =============================================================================

const feedbackChartConfig = {
    positive: { label: "Positive", color: "var(--color-green-500, #22c55e)" },
    negative: { label: "Negative", color: "var(--color-red-500, #ef4444)" },
} satisfies ChartConfig;

const ratingDistConfig = {
    count: { label: "Count" },
    positive: { label: "Positive", color: "var(--color-green-500, #22c55e)" },
    negative: { label: "Negative", color: "var(--color-red-500, #ef4444)" },
} satisfies ChartConfig;

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
    // Must have a loaded profile; null/undefined profile means loading/error → deny
    const isAuthorized = profile != null && (!profile.role || profile.role === 'admin');

    // Use the analytics hook for all data fetching
    const {
        feedbackData,
        summary,
        feedbackItems,
        hasMoreFeedback,
        sourceMetrics,
        trendData,
        isLoadingFeedback,
        isFetchingFeedback,
        isLoadingMetrics,
        feedbackError,
        refetchAll,
    } = useAnalytics({
        rating: ratingFilter === 'all' ? undefined : ratingFilter as 'positive' | 'negative',
        limit: feedbackLimit,
        dateRange,
        enabled: isAuthorized && !profileLoading,
    });

    const handleRefresh = useCallback(() => {
        refetchAll();
    }, [refetchAll]);

    const handleLoadMore = useCallback(() => {
        setFeedbackLimit(prev => prev + 20);
    }, []);

    // Transform trend data for chart (rename fields for recharts)
    const chartTrendData = useMemo(
        () => trendData.map(d => ({
            date: format(new Date(d.date), 'MMM d'),
            positive: d.positive_count,
            negative: d.negative_count,
        })),
        [trendData]
    );

    const ratingDistData = useMemo(
        () =>
            summary
                ? [
                      { name: 'Positive', count: summary.positive_count, fill: 'var(--color-green-500, #22c55e)' },
                      { name: 'Negative', count: summary.negative_count, fill: 'var(--color-red-500, #ef4444)' },
                  ]
                : [],
        [summary]
    );

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
                    value={isLoadingFeedback ? "..." : summary?.total_count ?? 0}
                />
                <SettingsStatCard
                    icon={ThumbsUp}
                    iconColorClass="text-green-500"
                    iconBgClass="bg-green-500/10"
                    label="Positive"
                    value={isLoadingFeedback ? "..." : summary?.positive_count ?? 0}
                    className="border-green-200 dark:border-green-900"
                />
                <SettingsStatCard
                    icon={ThumbsDown}
                    iconColorClass="text-red-500"
                    iconBgClass="bg-red-500/10"
                    label="Negative"
                    value={isLoadingFeedback ? "..." : summary?.negative_count ?? 0}
                    className="border-red-200 dark:border-red-900"
                />
                <SettingsStatCard
                    icon={TrendingDown}
                    iconColorClass="text-amber-500"
                    iconBgClass="bg-amber-500/10"
                    label="Negative Rate"
                    value={isLoadingFeedback ? "..." : `${summary?.negative_rate_pct ?? 0}%`}
                    description={
                        (summary?.negative_rate_pct ?? 0) > 20
                            ? "Above average"
                            : "Looking good"
                    }
                />
            </div>

            {/* Charts */}
            {!isLoadingFeedback && chartTrendData.length > 1 && (
                <div className="grid gap-4 md:grid-cols-2">
                    {/* Feedback Trend Line Chart */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Feedback Trend</CardTitle>
                            <CardDescription>Positive vs negative feedback over time</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ChartContainer config={feedbackChartConfig} className="h-[220px] w-full">
                                <LineChart data={chartTrendData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                    <XAxis dataKey="date" fontSize={12} tickLine={false} axisLine={false} />
                                    <YAxis fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
                                    <ChartTooltip content={<ChartTooltipContent />} />
                                    <Line type="monotone" dataKey="positive" stroke="var(--color-green-500, #22c55e)" strokeWidth={2} dot={false} />
                                    <Line type="monotone" dataKey="negative" stroke="var(--color-red-500, #ef4444)" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ChartContainer>
                        </CardContent>
                    </Card>

                    {/* Rating Distribution Bar Chart */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Rating Distribution</CardTitle>
                            <CardDescription>Total positive vs negative ratings</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ChartContainer config={ratingDistConfig} className="h-[220px] w-full">
                                <BarChart data={ratingDistData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                    <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
                                    <YAxis fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
                                    <ChartTooltip content={<ChartTooltipContent />} />
                                    <Bar dataKey="count" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ChartContainer>
                        </CardContent>
                    </Card>
                </div>
            )}

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
                    {isLoadingMetrics ? (
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
                    {isLoadingFeedback ? (
                        <div className="space-y-4">
                            {[...Array(5)].map((_, i) => (
                                <Skeleton key={i} className="h-24 w-full" />
                            ))}
                        </div>
                    ) : feedbackError ? (
                        <div className="text-center py-8 text-muted-foreground">
                            <p>Failed to load feedback. You may not have admin access.</p>
                        </div>
                    ) : feedbackItems.length === 0 ? (
                        <SettingsEmptyState
                            icon={MessageSquare}
                            title="No feedback collected yet"
                            description="User ratings on AI responses will appear here"
                        />
                    ) : (
                        <div className="space-y-4">
                            {feedbackItems.map((item) => (
                                <FeedbackCard key={item.id} feedback={item} />
                            ))}

                            {hasMoreFeedback && (
                                <div className="text-center pt-4">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleLoadMore}
                                        disabled={isFetchingFeedback}
                                    >
                                        {isFetchingFeedback && <Spinner className="h-4 w-4 mr-2 animate-spin" />}
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
