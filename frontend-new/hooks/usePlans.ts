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
}

const FALLBACK_PLANS: PricingPlan[] = [
    {
        id: 'starter',
        name: 'Starter',
        description: 'For individuals building a second brain.',
        price_amount: 499,  // $4.99 in cents
        price_currency: 'usd',
        interval: 'month',
        type: 'starter'
    },
    {
        id: 'pro',
        name: 'Pro',
        description: 'For power users and teams.',
        price_amount: 1999,  // $19.99 in cents
        price_currency: 'usd',
        interval: 'month',
        type: 'pro'
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
