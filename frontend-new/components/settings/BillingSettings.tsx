"use client";

import { Check, CreditCard, Loader2, Sparkles, Users, Zap, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useProfile } from "@/hooks/useProfile";
import { useUsage } from "@/hooks/useUsage";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { cn } from "@/lib/utils";

/**
 * Polar checkout URLs (placeholders - replace with actual URLs)
 */
const CHECKOUT_URLS = {
  starter: "https://buy.polar.sh/axio-starter",
  pro: "https://buy.polar.sh/axio-pro",
  enterprise: "https://buy.polar.sh/axio-enterprise",
};

/**
 * Plan configurations with features
 */
const plans = [
  {
    id: "starter",
    name: "Starter",
    price: "$9",
    period: "/month",
    description: "For individuals getting started",
    icon: Zap,
    features: [
      "50 documents",
      "500 MB storage",
      "GPT-4o Mini",
      "Email support",
    ],
    notIncluded: [
      "Team access",
      "Priority support",
      "Custom integrations",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "For professionals and power users",
    icon: Sparkles,
    popular: true,
    features: [
      "500 documents",
      "5 GB storage",
      "GPT-4o (full)",
      "Web crawling",
      "Priority email support",
    ],
    notIncluded: [
      "Team access",
      "Custom integrations",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "$99",
    period: "/month",
    description: "For teams and organizations",
    icon: Building2,
    features: [
      "Unlimited documents",
      "Unlimited storage",
      "GPT-4o + Claude",
      "Team access (20 seats)",
      "Dedicated support",
      "Custom integrations",
      "SSO (coming soon)",
    ],
    notIncluded: [],
  },
];

const planDetails: Record<string, { name: string; description: string }> = {
  free: {
    name: "Free",
    description: "Basic features with limited usage",
  },
  starter: {
    name: "Starter",
    description: "For individuals getting started",
  },
  pro: {
    name: "Pro",
    description: "For professionals and power users",
  },
  enterprise: {
    name: "Enterprise",
    description: "For teams and organizations",
  },
};

export function BillingSettings() {
  const { profile, isLoading } = useProfile();
  const { plan: effectivePlan, isPlanInherited } = useUsage();

  const currentPlan = effectivePlan || profile?.plan || "free";
  const planInfo = planDetails[currentPlan] || planDetails.free;

  const handleUpgrade = (planId: string) => {
    const url = CHECKOUT_URLS[planId as keyof typeof CHECKOUT_URLS];
    if (url) {
      window.open(url, "_blank");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">Billing & Plans</h1>
        <p className="mt-1 text-muted-foreground">Manage your subscription and upgrade your plan</p>
      </div>

      {/* Current Plan Card */}
      <Card className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-accent/5" />
        <CardHeader className="relative">
          <CardTitle className="flex items-center gap-2">
            Current Plan
            <Badge variant="ai" className="ml-2">
              {planInfo.name}
            </Badge>
            {isPlanInherited && (
              <Badge variant="outline" className="ml-1 text-xs">
                <Users className="h-3 w-3 mr-1" />
                Team
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            {isPlanInherited
              ? "You're using your team owner's plan"
              : "Your current subscription tier"}
          </CardDescription>
        </CardHeader>
        <CardContent className="relative space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-lg border border-border bg-background/50">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
              <AxioLogo variant="icon" size="lg" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-foreground">{planInfo.name} Plan</h3>
              <p className="text-sm text-muted-foreground">
                {planInfo.description}
              </p>
            </div>
            {currentPlan !== "free" && (
              <Button variant="outline">Manage Subscription</Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pricing Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((plan) => {
            const isCurrentPlan = currentPlan === plan.id;
            const Icon = plan.icon;

            return (
              <Card
                key={plan.id}
                className={cn(
                  "relative overflow-hidden transition-all",
                  plan.popular && "border-primary shadow-lg",
                  isCurrentPlan && "ring-2 ring-primary/50"
                )}
              >
                {plan.popular && (
                  <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-xs font-medium px-3 py-1 rounded-bl-lg">
                    Most Popular
                  </div>
                )}
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg",
                      plan.popular ? "bg-primary/10" : "bg-muted"
                    )}>
                      <Icon className={cn(
                        "h-5 w-5",
                        plan.popular ? "text-primary" : "text-muted-foreground"
                      )} />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{plan.name}</CardTitle>
                      <CardDescription className="text-xs">{plan.description}</CardDescription>
                    </div>
                  </div>
                  <div className="mt-4">
                    <span className="text-3xl font-bold">{plan.price}</span>
                    <span className="text-muted-foreground">{plan.period}</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 text-success shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                    {plan.notIncluded.map((feature) => (
                      <li key={feature} className="flex items-center gap-2 text-sm text-muted-foreground/50">
                        <span className="h-4 w-4 shrink-0" />
                        <span className="line-through">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    variant={isCurrentPlan ? "outline" : (plan.popular ? "gradient" : "default")}
                    disabled={isCurrentPlan}
                    onClick={() => handleUpgrade(plan.id)}
                  >
                    {isCurrentPlan ? "Current Plan" : "Upgrade"}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Payment Methods */}
      <Card>
        <CardHeader>
          <CardTitle>Payment Methods</CardTitle>
          <CardDescription>Manage your payment information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-lg border border-border">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <CreditCard className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-muted-foreground">No payment method on file</p>
            </div>
            <Button variant="outline" size="sm">
              Add Payment Method
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Billing History */}
      <Card>
        <CardHeader>
          <CardTitle>Billing History</CardTitle>
          <CardDescription>View your past invoices and payments</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-sm text-muted-foreground">No billing history available</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}