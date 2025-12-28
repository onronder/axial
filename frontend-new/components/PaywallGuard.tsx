"use client";

/**
 * Paywall Guard Component
 * 
 * Blocks access to dashboard for users without active subscription.
 * Shows pricing page with trial links to Polar checkout.
 */

import { useEffect, useState } from "react";
import { Check, Zap, Building2, Loader2, ArrowRight } from "lucide-react";
import { useUsage } from "@/hooks/useUsage";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AxioLogo } from "@/components/branding/AxioLogo";

interface PaywallGuardProps {
    children: React.ReactNode;
}

// Polar checkout URLs - these would typically come from environment variables
const POLAR_CHECKOUT_URLS = {
    starter: process.env.NEXT_PUBLIC_POLAR_STARTER_CHECKOUT || "https://polar.sh/checkout/starter",
    pro: process.env.NEXT_PUBLIC_POLAR_PRO_CHECKOUT || "https://polar.sh/checkout/pro",
    enterprise: process.env.NEXT_PUBLIC_POLAR_ENTERPRISE_CHECKOUT || "https://polar.sh/checkout/enterprise",
};

const plans = [
    {
        id: "starter",
        name: "Starter",
        price: "$9",
        period: "/month",
        description: "Perfect for individuals getting started",
        features: [
            "20 documents",
            "200 MB storage",
            "Fast AI (Llama-3)",
            "Google Drive integration",
            "Email support",
        ],
        cta: "Start Free Trial",
        popular: false,
        icon: Zap,
    },
    {
        id: "pro",
        name: "Pro",
        price: "$29",
        period: "/month",
        description: "For professionals who need more power",
        features: [
            "500 documents",
            "2 GB storage",
            "Smart Router AI",
            "Web crawling",
            "All integrations",
            "Priority support",
        ],
        cta: "Start Free Trial",
        popular: true,
        icon: Zap,
    },
    {
        id: "enterprise",
        name: "Enterprise",
        price: "$99",
        period: "/month",
        description: "For teams with unlimited needs",
        features: [
            "Unlimited documents",
            "Unlimited storage",
            "Premium AI (GPT-4o)",
            "Team collaboration",
            "Admin controls",
            "Dedicated support",
        ],
        cta: "Start Free Trial",
        popular: false,
        icon: Building2,
    },
];

export function PaywallGuard({ children }: PaywallGuardProps) {
    const { user } = useAuth();
    const { plan, usage, isLoading } = useUsage();
    const [isRedirecting, setIsRedirecting] = useState(false);

    // Get subscription status from usage data
    const subscriptionStatus = usage?.subscription_status || "inactive";

    // Allowed statuses that grant access
    const allowedStatuses = ["active", "trialing"];
    const hasActiveSubscription = allowedStatuses.includes(subscriptionStatus);

    // If plan is 'none' or status is not active/trialing, show paywall
    const showPaywall = !isLoading && (plan === "none" || !hasActiveSubscription);

    // If loading or has valid subscription, show children
    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background">
                <Loader2 className="animate-spin h-8 w-8 text-primary" />
            </div>
        );
    }

    if (!showPaywall) {
        return <>{children}</>;
    }

    const handleCheckout = (planId: string) => {
        setIsRedirecting(true);

        // Build checkout URL with user metadata
        const checkoutUrl = POLAR_CHECKOUT_URLS[planId as keyof typeof POLAR_CHECKOUT_URLS];
        const urlWithMetadata = new URL(checkoutUrl);

        if (user?.id) {
            urlWithMetadata.searchParams.set("metadata[user_id]", user.id);
        }
        if (user?.email) {
            urlWithMetadata.searchParams.set("customer_email", user.email);
        }

        window.location.href = urlWithMetadata.toString();
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
            {/* Header */}
            <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <AxioLogo variant="icon" size="md" />
                        <span className="font-display text-xl font-semibold">Axio Hub</span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                        Signed in as {user?.email}
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto px-4 py-12">
                {/* Hero Section */}
                <div className="text-center max-w-3xl mx-auto mb-12">
                    <Badge variant="secondary" className="mb-4">
                        🎉 3-Day Free Trial on All Plans
                    </Badge>
                    <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
                        Choose Your Plan
                    </h1>
                    <p className="text-lg text-muted-foreground">
                        Start your free trial today. No commitment, cancel anytime.
                        <br />
                        Your AI-powered knowledge assistant awaits.
                    </p>
                </div>

                {/* Pricing Cards */}
                <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
                    {plans.map((pricing) => {
                        const Icon = pricing.icon;

                        return (
                            <Card
                                key={pricing.id}
                                className={`relative flex flex-col ${pricing.popular
                                        ? "border-primary shadow-lg shadow-primary/20 scale-105"
                                        : "border-border"
                                    }`}
                            >
                                {pricing.popular && (
                                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                                        <Badge className="bg-primary text-primary-foreground">
                                            Most Popular
                                        </Badge>
                                    </div>
                                )}

                                <CardHeader className="text-center pb-4">
                                    <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                                        <Icon className="h-6 w-6 text-primary" />
                                    </div>
                                    <CardTitle className="text-xl">{pricing.name}</CardTitle>
                                    <CardDescription>{pricing.description}</CardDescription>
                                </CardHeader>

                                <CardContent className="flex-1">
                                    <div className="text-center mb-6">
                                        <span className="text-4xl font-bold">{pricing.price}</span>
                                        <span className="text-muted-foreground">{pricing.period}</span>
                                    </div>

                                    <ul className="space-y-3">
                                        {pricing.features.map((feature, i) => (
                                            <li key={i} className="flex items-center gap-2 text-sm">
                                                <Check className="h-4 w-4 text-success shrink-0" />
                                                <span>{feature}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </CardContent>

                                <CardFooter>
                                    <Button
                                        className="w-full gap-2"
                                        variant={pricing.popular ? "default" : "outline"}
                                        size="lg"
                                        onClick={() => handleCheckout(pricing.id)}
                                        disabled={isRedirecting}
                                    >
                                        {isRedirecting ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <>
                                                {pricing.cta}
                                                <ArrowRight className="h-4 w-4" />
                                            </>
                                        )}
                                    </Button>
                                </CardFooter>
                            </Card>
                        );
                    })}
                </div>

                {/* Trust Indicators */}
                <div className="text-center mt-12 text-sm text-muted-foreground">
                    <p>🔒 Secure payment via Polar • Cancel anytime • No hidden fees</p>
                </div>
            </main>
        </div>
    );
}
