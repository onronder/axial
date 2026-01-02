"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Check,
  CreditCard,
  Loader2,
  Sparkles,
  Users,
  Zap,
  Building2,
  ExternalLink,
  Receipt,
  Calendar,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useProfile } from "@/hooks/useProfile";
import { useUsage } from "@/hooks/useUsage";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { toast } from "sonner";

// ============================================================
// TYPES
// ============================================================

interface PolarPlan {
  id: string;
  name: string;
  description: string;
  price_amount: number; // in cents
  price_currency: string;
  interval: string;
  type: string; // 'starter', 'pro', 'enterprise'
}

interface Invoice {
  id: string;
  order_id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  product_name: string;
  invoice_url?: string;
}

// ============================================================
// STATIC PLAN FEATURES (Features are not in Polar API)
// ============================================================

const planFeatures: Record<
  string,
  { features: string[]; notIncluded: string[]; icon: typeof Zap; popular?: boolean }
> = {
  starter: {
    icon: Zap,
    features: [
      "50 documents",
      "500 MB storage",
      "GPT-4o Mini",
      "Email support",
    ],
    notIncluded: ["Team access", "Priority support", "Custom integrations"],
  },
  pro: {
    icon: Sparkles,
    popular: true,
    features: [
      "500 documents",
      "5 GB storage",
      "GPT-4o (full)",
      "Web crawling",
      "Priority email support",
    ],
    notIncluded: ["Team access", "Custom integrations"],
  },
  enterprise: {
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
};

const planDetails: Record<string, { name: string; description: string }> = {
  free: { name: "Free", description: "Basic features with limited usage" },
  starter: { name: "Starter", description: "For individuals getting started" },
  pro: { name: "Pro", description: "For professionals and power users" },
  enterprise: { name: "Enterprise", description: "For teams and organizations" },
};

// ============================================================
// HELPER FUNCTIONS
// ============================================================

function formatPrice(amountCents: number, currency: string): string {
  const amount = amountCents / 100;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}

function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateString;
  }
}

// ============================================================
// MAIN COMPONENT
// ============================================================

export function BillingSettings() {
  const { profile, isLoading: profileLoading } = useProfile();
  const { plan: effectivePlan, isPlanInherited } = useUsage();

  // State for API data
  const [plans, setPlans] = useState<PolarPlan[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isLoadingPlans, setIsLoadingPlans] = useState(true);
  const [isLoadingInvoices, setIsLoadingInvoices] = useState(true);
  const [isPortalLoading, setIsPortalLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  const currentPlan = effectivePlan || profile?.plan || "free";
  const planInfo = planDetails[currentPlan] || planDetails.free;

  // Fetch plans from Polar API
  const fetchPlans = useCallback(async () => {
    try {
      setIsLoadingPlans(true);
      const response = await api.get("/billing/plans");
      setPlans(response.data);
    } catch (error) {
      console.error("[Billing] Failed to fetch plans:", error);
      toast.error("Failed to load pricing information");
    } finally {
      setIsLoadingPlans(false);
    }
  }, []);

  // Fetch billing history
  const fetchInvoices = useCallback(async () => {
    try {
      setIsLoadingInvoices(true);
      const response = await api.get("/billing/invoices");
      setInvoices(response.data);
    } catch (error) {
      console.error("[Billing] Failed to fetch invoices:", error);
    } finally {
      setIsLoadingInvoices(false);
    }
  }, []);

  // Load data on mount
  useEffect(() => {
    fetchPlans();
    fetchInvoices();
  }, [fetchPlans, fetchInvoices]);

  // Handle upgrade button click
  const handleUpgrade = async (planType: string) => {
    try {
      setCheckoutLoading(planType);
      const response = await api.post("/billing/checkout", { plan: planType });

      if (response.data?.url) {
        window.location.href = response.data.url;
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (error) {
      console.error("[Billing] Checkout failed:", error);
      toast.error("Failed to start checkout. Please try again.");
    } finally {
      setCheckoutLoading(null);
    }
  };

  // Handle manage subscription click
  const handleManageSubscription = async () => {
    try {
      setIsPortalLoading(true);
      const response = await api.post("/billing/portal");

      if (response.data?.url) {
        window.open(response.data.url, "_blank");
      } else {
        throw new Error("No portal URL returned");
      }
    } catch (error) {
      console.error("[Billing] Portal redirect failed:", error);
      toast.error("Failed to open subscription portal");
    } finally {
      setIsPortalLoading(false);
    }
  };

  if (profileLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">
          Billing & Plans
        </h1>
        <p className="mt-1 text-muted-foreground">
          Manage your subscription and upgrade your plan
        </p>
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
              <p className="text-sm text-muted-foreground">{planInfo.description}</p>
            </div>
            {currentPlan !== "free" && (
              <Button
                variant="outline"
                onClick={handleManageSubscription}
                disabled={isPortalLoading}
              >
                {isPortalLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <ExternalLink className="h-4 w-4 mr-2" />
                )}
                Manage Subscription
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pricing Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
        {isLoadingPlans ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : plans.length === 0 ? (
          <Card className="p-8 text-center">
            <AlertCircle className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-muted-foreground">Unable to load pricing. Please refresh.</p>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {plans.map((plan) => {
              const isCurrentPlan = currentPlan === plan.type;
              const features = planFeatures[plan.type] || planFeatures.starter;
              const Icon = features.icon;
              const isPopular = features.popular;

              return (
                <Card
                  key={plan.id}
                  className={cn(
                    "relative overflow-hidden transition-all",
                    isPopular && "border-primary shadow-lg",
                    isCurrentPlan && "ring-2 ring-primary/50"
                  )}
                >
                  {isPopular && (
                    <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-xs font-medium px-3 py-1 rounded-bl-lg">
                      Most Popular
                    </div>
                  )}
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "flex h-10 w-10 items-center justify-center rounded-lg",
                          isPopular ? "bg-primary/10" : "bg-muted"
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-5 w-5",
                            isPopular ? "text-primary" : "text-muted-foreground"
                          )}
                        />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{plan.name}</CardTitle>
                        <CardDescription className="text-xs">
                          {plan.description || planDetails[plan.type]?.description}
                        </CardDescription>
                      </div>
                    </div>
                    <div className="mt-4">
                      <span className="text-3xl font-bold">
                        {formatPrice(plan.price_amount, plan.price_currency)}
                      </span>
                      <span className="text-muted-foreground">/{plan.interval}</span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <ul className="space-y-2">
                      {features.features.map((feature) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-success shrink-0" />
                          <span>{feature}</span>
                        </li>
                      ))}
                      {features.notIncluded.map((feature) => (
                        <li
                          key={feature}
                          className="flex items-center gap-2 text-sm text-muted-foreground/50"
                        >
                          <span className="h-4 w-4 shrink-0" />
                          <span className="line-through">{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button
                      className="w-full"
                      variant={
                        isCurrentPlan ? "outline" : isPopular ? "gradient" : "default"
                      }
                      disabled={isCurrentPlan || checkoutLoading === plan.type}
                      onClick={() => handleUpgrade(plan.type)}
                    >
                      {checkoutLoading === plan.type ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : null}
                      {isCurrentPlan ? "Current Plan" : "Upgrade"}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
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
              <p className="text-sm font-medium">Managed by Polar</p>
              <p className="text-xs text-muted-foreground">
                Your payment methods are securely managed through Polar
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleManageSubscription}
              disabled={isPortalLoading}
            >
              {isPortalLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Manage
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Billing History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            Billing History
          </CardTitle>
          <CardDescription>View your past invoices and payments</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingInvoices ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : invoices.length === 0 ? (
            <div className="text-center py-8">
              <Calendar className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">No billing history available</p>
            </div>
          ) : (
            <div className="space-y-3">
              {invoices.map((invoice) => (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                      <Receipt className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium">{invoice.product_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDate(invoice.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="font-medium">
                        {formatPrice(invoice.amount, invoice.currency)}
                      </p>
                      <Badge
                        variant={invoice.status === "paid" ? "default" : "outline"}
                        className="text-xs"
                      >
                        {invoice.status}
                      </Badge>
                    </div>
                    {invoice.invoice_url && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(invoice.invoice_url, "_blank")}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}