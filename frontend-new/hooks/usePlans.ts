import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { AxiosError } from 'axios';

export interface PricingPlan {
    id: string;
    name: string;
    description: string;
    price_amount: number;
    price_currency: string;
    interval: string;
    type: 'starter' | 'pro' | 'enterprise';
    features: string[];
    button_text: string;
    button_variant: 'default' | 'outline' | 'ghost';
    popular: boolean;
}

const FALLBACK_PLANS: PricingPlan[] = [
    {
        id: 'starter',
        name: 'Starter',
        description: 'Perfect for trying out Axio Hub',
        price_amount: 499,
        price_currency: 'usd',
        interval: 'month',
        type: 'starter',
        features: ["100 queries/month", "2 connected sources", "Basic RAG search"],
        button_text: "Get Started",
        button_variant: "outline",
        popular: false
    },
    {
        id: 'pro',
        name: 'Pro',
        description: 'For professionals who need more',
        price_amount: 2900,
        price_currency: 'usd',
        interval: 'month',
        type: 'pro',
        features: ["Unlimited queries", "Unlimited sources", "Hybrid RAG + semantic", "Priority support"],
        button_text: "Start Free Trial",
        button_variant: "default",
        popular: true
    }
];

export function usePlans() {
    const [plans, setPlans] = useState<PricingPlan[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const controller = new AbortController();

        async function fetchPlans() {
            try {
                setIsLoading(true);
                // Fetch from the backend proxy which gets data from Polar
                // NOTE: api.get returns the full AxiosResponse, we need .data
                const response = await api.get<PricingPlan[]>('/billing/plans', {
                    signal: controller.signal
                });

                const data = response.data;

                if (Array.isArray(data) && data.length > 0) {
                    setPlans(data);
                    setError(null);
                } else {
                    // Fallback if API returns empty array (e.g. Polar token issue)
                    console.warn("[usePlans] API returned empty plans, using fallback.");
                    throw new Error("Empty plans returned from API");
                }
            } catch (err) {
                if (err instanceof AxiosError && err.code === 'ERR_CANCELED') {
                    // Ignore cancellation errors
                    return;
                }

                console.error('[usePlans] Failed to fetch plans:', err);
                setError(err instanceof Error ? err : new Error('Unknown error fetching plans'));

                // Fallback static plans to ensure UI never looks broken
                setPlans(FALLBACK_PLANS);
            } finally {
                // Only update loading if not aborted (though unsafe check, logic usually fine)
                if (!controller.signal.aborted) {
                    setIsLoading(false);
                }
            }
        }

        fetchPlans();

        return () => {
            controller.abort();
        };
    }, []);

    return { plans, isLoading, error };
}
