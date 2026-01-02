"use client";

import { Check, Loader2, Zap, Sparkles, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useUsage } from "@/hooks/useUsage";
import { usePlans } from "@/hooks/usePlans";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { useState } from "react";

// Static plan definitions with actual Polar prices
const STATIC_PLANS = [
    {
        id: "starter",
        type: "starter",
        name: "Starter",
        description: "Perfect for trying out Axio Hub",
        price: "$4.99",
        interval: "month",
        icon: Zap,
        features: [
            "100 queries/month",
            "2 connected sources",
            "Basic RAG search",
            "Community support",
        ],
        buttonText: "Get Started",
        buttonVariant: "outline" as const,
    },
    {
        id: "pro",
        type: "pro",
        name: "Pro",
        description: "For professionals who need more",
        price: "$29",
        interval: "month",
        icon: Sparkles,
        popular: true,
        features: [
            "Unlimited queries",
            "Unlimited sources",
            "Hybrid RAG + semantic",
            "Priority support",
            "API access",
            "Team sharing (3 seats)",
        ],
        buttonText: "Start Free Trial",
        buttonVariant: "default" as const,
    },
    {
        id: "enterprise",
        type: "enterprise",
        name: "Enterprise",
        description: "For organizations at scale",
        price: "Contact Us",
        interval: "",
        icon: Building2,
        features: [
            "Everything in Pro",
            "SSO & SAML",
            "Custom integrations",
            "Dedicated support",
            "SLA guarantee",
            "On-premise option",
        ],
        buttonText: "Contact Sales",
        buttonVariant: "ghost" as const,
    },
];

export function PaywallGuard({ children }: { children: React.ReactNode }) {
    const { plan: currentPlan, isLoading: isUsageLoading } = useUsage();
    const { plans: apiPlans, isLoading: isPlansLoading } = usePlans();
    const { toast } = useToast();
    const [isCheckoutLoading, setIsCheckoutLoading] = useState<string | null>(null);

    const isLoading = isUsageLoading || isPlansLoading;

    // Check if user has a valid paid plan
    const hasAccess = ['starter', 'pro', 'enterprise'].includes(currentPlan || '');

    if (isLoading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (hasAccess) {
        return <>{children}</>;
    }

    // Merge API prices with static plans (API prices take precedence)
    const displayPlans = STATIC_PLANS.map(staticPlan => {
        const apiPlan = apiPlans.find(p => p.type === staticPlan.type);
        if (apiPlan && apiPlan.price_amount !== undefined) {
            return {
                ...staticPlan,
                price: apiPlan.price_amount === 0
                    ? "$0"
                    : new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: apiPlan.price_currency
                    }).format(apiPlan.price_amount / 100),
                interval: apiPlan.interval || staticPlan.interval,
            };
        }
        return staticPlan;
    });

    const handleUpgrade = async (planType: string) => {
        // Enterprise: open email directly without loading state
        if (planType === 'enterprise') {
            window.open("mailto:sales@axiohub.io?subject=Enterprise%20Plan%20Inquiry&body=Hi%2C%20I'm%20interested%20in%20the%20Enterprise%20plan.%0A%0APlease%20contact%20me%20to%20discuss%20pricing%20and%20features.", "_self");
            return;
        }

        try {
            setIsCheckoutLoading(planType);

            const response = await api.post('/billing/checkout', { plan: planType });
            if (response.data?.url) {
                window.location.href = response.data.url;
            } else {
                throw new Error(response.data?.error || "No checkout URL");
            }
        } catch (error) {
            toast({
                title: "Error",
                description: "Failed to start checkout. Please try again.",
                variant: "destructive",
            });
        } finally {
            setIsCheckoutLoading(null);
        }
    };

    return (
        <div className="min-h-screen bg-background/50 py-16 px-4">
            {/* Header - matches original "Simple pricing" design */}
            <div className="text-center space-y-4 mb-12">
                <h1 className="text-5xl font-extrabold tracking-tight">
                    <span className="text-white">Simple </span>
                    <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
                        pricing
                    </span>
                </h1>
                <p className="text-muted-foreground text-lg">
                    Start free. Scale as you grow.
                </p>
            </div>

            {/* Pricing Cards */}
            <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto items-stretch">
                {displayPlans.map((plan) => {
                    const Icon = plan.icon;
                    const isCurrentPlan = currentPlan === plan.type;
                    const isPro = plan.type === 'pro';

                    return (
                        <Card
                            key={plan.id}
                            className={`
                                relative flex flex-col h-full
                                ${isPro ? 'border-primary shadow-2xl scale-105 z-10' : 'border-border'}
                                ${plan.type === 'enterprise' ? 'border-dashed bg-muted/10' : ''}
                            `}
                        >
                            {/* Most Popular Badge */}
                            {plan.popular && (
                                <div className="absolute -top-4 left-0 right-0 flex justify-center">
                                    <span className="bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium px-4 py-1 rounded-full shadow-lg flex items-center gap-1">
                                        <Sparkles className="h-3 w-3" />
                                        Most Popular
                                    </span>
                                </div>
                            )}

                            <CardHeader className="pt-8">
                                <CardTitle className="text-xl font-bold">{plan.name}</CardTitle>
                                <p className="text-sm text-muted-foreground mt-1">
                                    {plan.description}
                                </p>
                                <div className="mt-4 flex items-baseline">
                                    <span className="text-4xl font-bold">{plan.price}</span>
                                    {plan.interval && (
                                        <span className="text-muted-foreground ml-1">/{plan.interval}</span>
                                    )}
                                </div>
                            </CardHeader>

                            <CardContent className="flex-1">
                                <ul className="space-y-3 text-sm">
                                    {plan.features.map((feature, idx) => (
                                        <li key={idx} className="flex items-center">
                                            <Check className={`mr-2 h-4 w-4 flex-shrink-0 ${isPro ? 'text-primary' : 'text-green-500'
                                                }`} />
                                            <span>{feature}</span>
                                        </li>
                                    ))}
                                </ul>
                            </CardContent>

                            <CardFooter className="pt-4">
                                <Button
                                    className={`w-full ${isPro ? 'bg-gradient-to-r from-cyan-500 to-purple-500 hover:opacity-90' : ''}`}
                                    size="lg"
                                    variant={plan.buttonVariant}
                                    onClick={() => handleUpgrade(plan.type)}
                                    disabled={!!isCheckoutLoading || isCurrentPlan}
                                >
                                    {isCheckoutLoading === plan.type && (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    )}
                                    {isCurrentPlan ? 'Current Plan' : plan.buttonText}
                                </Button>
                            </CardFooter>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
}
