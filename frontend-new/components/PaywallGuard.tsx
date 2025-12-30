"use client";

import { Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useUsage } from "@/hooks/useUsage";
import { usePlans } from "@/hooks/usePlans";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { useState } from "react";

export function PaywallGuard({ children }: { children: React.ReactNode }) {
    const { isPro, isLoading: isUsageLoading } = useUsage();
    const { plans, isLoading: isPlansLoading } = usePlans();
    const { toast } = useToast();
    const [isCheckoutLoading, setIsCheckoutLoading] = useState<string | null>(null);

    // Global loading state
    const isLoading = isUsageLoading || isPlansLoading;

    if (isLoading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    // If user has access (isPro), render the content
    if (isPro) {
        return <>{children}</>;
    }

    // --- PAYWALL UI LOGIC ---

    const handleUpgrade = async (planType: string) => {
        try {
            setIsCheckoutLoading(planType);

            // Enterprise: Email link
            if (planType === 'enterprise') {
                window.location.href = "mailto:sales@axiohub.io?subject=Enterprise%20Inquiry";
                return;
            }

            // Starter/Pro: Create Checkout Session
            const response = await api.post('/billing/checkout', { plan: planType });
            if (response.data && response.data.url) {
                window.location.href = response.data.url;
            } else if (response.data && response.data.error) {
                throw new Error(response.data.error);
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
        <div className="space-y-8 p-8 min-h-screen bg-background/50">
            <div className="text-center space-y-4 pt-8">
                <h2 className="text-4xl font-extrabold tracking-tight">Unlock Full Power</h2>
                <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
                    You've reached the limits of the free tier. Upgrade to Pro to process more files, use advanced AI models, and collaborate with your team.
                </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto items-start">
                {/* Dynamic Plans from Polar */}
                {plans.map((plan) => (
                    <Card key={plan.id} className={`relative flex flex-col h-full ${plan.type === 'pro' ? 'border-primary shadow-2xl scale-105 z-10' : 'border-border'}`}>
                        {plan.type === 'pro' && (
                            <div className="absolute -top-4 left-0 right-0 flex justify-center">
                                <span className="bg-primary text-primary-foreground text-sm font-medium px-4 py-1 rounded-full shadow-sm">
                                    Most Popular
                                </span>
                            </div>
                        )}
                        <CardHeader>
                            <CardTitle className="text-2xl">{plan.name}</CardTitle>
                            <div className="mt-2 flex items-baseline">
                                <span className="text-4xl font-bold">
                                    {plan.price_amount > 0
                                        ? new Intl.NumberFormat('en-US', { style: 'currency', currency: plan.price_currency }).format(plan.price_amount / 100)
                                        : '$0'}
                                </span>
                                <span className="text-muted-foreground ml-1">/{plan.interval}</span>
                            </div>
                            <p className="text-sm text-muted-foreground mt-2 min-h-[40px]">{plan.description}</p>
                        </CardHeader>
                        <CardContent className="flex-1">
                            <ul className="space-y-3 text-sm">
                                {plan.type === 'starter' && (
                                    <>
                                        <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-green-500 flex-shrink-0" /> 50 Files Storage</li>
                                        <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-green-500 flex-shrink-0" /> Standard AI Chat</li>
                                        <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-green-500 flex-shrink-0" /> Basic Support</li>
                                    </>
                                )}
                                {plan.type === 'pro' && (
                                    <>
                                        <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-primary flex-shrink-0" /> <strong>2,000 Files</strong> Storage</li>
                                        <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-primary flex-shrink-0" /> <strong>Deep Research</strong> Agent</li>
                                        <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-primary flex-shrink-0" /> Advanced Reasoning Models</li>
                                        <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-primary flex-shrink-0" /> Priority Support</li>
                                    </>
                                )}
                            </ul>
                        </CardContent>
                        <CardFooter>
                            <Button
                                className="w-full"
                                size="lg"
                                variant={plan.type === 'pro' ? 'default' : 'outline'}
                                onClick={() => handleUpgrade(plan.type)}
                                disabled={!!isCheckoutLoading || plan.type === 'starter'}
                            >
                                {isCheckoutLoading === plan.type && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {plan.type === 'starter' ? 'Current Plan' : 'Upgrade to Pro'}
                            </Button>
                        </CardFooter>
                    </Card>
                ))}

                {/* Static Enterprise Card */}
                <Card className="flex flex-col h-full border-dashed bg-muted/20">
                    <CardHeader>
                        <CardTitle className="text-2xl">Enterprise</CardTitle>
                        <div className="mt-2 flex items-baseline">
                            <span className="text-4xl font-bold">Custom</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-2 min-h-[40px]">For large organizations with strict security needs.</p>
                    </CardHeader>
                    <CardContent className="flex-1">
                        <ul className="space-y-3 text-sm">
                            <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-muted-foreground flex-shrink-0" /> Unlimited Files</li>
                            <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-muted-foreground flex-shrink-0" /> SSO & SAML</li>
                            <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-muted-foreground flex-shrink-0" /> Dedicated Account Manager</li>
                            <li className="flex items-center"><Check className="mr-2 h-4 w-4 text-muted-foreground flex-shrink-0" /> Custom SLAs</li>
                        </ul>
                    </CardContent>
                    <CardFooter>
                        <Button className="w-full" size="lg" variant="ghost" onClick={() => handleUpgrade('enterprise')}>
                            Contact Sales
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
}
