/**
 * Performance Monitoring Utility
 * 
 * Provides simple performance tracking for critical operations.
 */

interface PerformanceMetric {
    name: string;
    duration: number;
    timestamp: number;
}

class PerformanceMonitor {
    private metrics: PerformanceMetric[] = [];
    private maxMetrics = 100; // Keep last 100 metrics

    /**
     * Measure the execution time of a function
     */
    measure<T>(name: string, fn: () => T): T {
        const start = performance.now();
        try {
            const result = fn();
            return result;
        } finally {
            const duration = performance.now() - start;
            this.recordMetric(name, duration);
        }
    }

    /**
     * Measure async function execution time
     */
    async measureAsync<T>(name: string, fn: () => Promise<T>): Promise<T> {
        const start = performance.now();
        try {
            const result = await fn();
            return result;
        } finally {
            const duration = performance.now() - start;
            this.recordMetric(name, duration);
        }
    }

    /**
     * Record a performance metric
     */
    private recordMetric(name: string, duration: number) {
        const metric: PerformanceMetric = {
            name,
            duration,
            timestamp: Date.now(),
        };

        this.metrics.push(metric);

        // Keep only last N metrics
        if (this.metrics.length > this.maxMetrics) {
            this.metrics.shift();
        }

        // Log slow operations (>1s)
        if (duration > 1000) {
            console.warn(`⚠️ Slow operation: ${name} took ${duration.toFixed(2)}ms`);
        }

        // Send to analytics if available
        if (typeof window !== 'undefined' && (window as any).gtag) {
            (window as any).gtag('event', 'timing_complete', {
                name,
                value: Math.round(duration),
                event_category: 'Performance',
            });
        }
    }

    /**
     * Get performance summary
     */
    getSummary() {
        const grouped = this.metrics.reduce((acc, metric) => {
            if (!acc[metric.name]) {
                acc[metric.name] = [];
            }
            acc[metric.name].push(metric.duration);
            return acc;
        }, {} as Record<string, number[]>);

        return Object.entries(grouped).map(([name, durations]) => ({
            name,
            count: durations.length,
            avg: durations.reduce((a, b) => a + b, 0) / durations.length,
            min: Math.min(...durations),
            max: Math.max(...durations),
        }));
    }

    /**
     * Clear all metrics
     */
    clear() {
        this.metrics = [];
    }
}

// Export singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Convenience exports
export const measurePerformance = performanceMonitor.measure.bind(performanceMonitor);
export const measurePerformanceAsync = performanceMonitor.measureAsync.bind(performanceMonitor);
