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
// STATIC PLANS - Always show 3 plans (Starter, Pro, Enterprise)
// ============================================================

const STATIC_PLANS = [
  {
    id: "starter",
    type: "starter",
    name: "Starter",
    description: "Perfect for trying out Axio Hub",
    price: "$4.99",
    priceAmount: 499,
    interval: "month",
    icon: Zap,
    features: [
      "100 queries/month",
      "2 connected sources",
      "Basic RAG search",
      "Community support",
    ],
    buttonText: "Get Started",
  },
  {
    id: "pro",
    type: "pro",
    name: "Pro",
    description: "For professionals who need more",
    price: "$29",
    priceAmount: 2900,
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
    buttonText: "Upgrade to Pro",
  },
  {
    id: "enterprise",
    type: "enterprise",
    name: "Enterprise",
    description: "For organizations at scale",
    price: "Contact Us",
    priceAmount: 0,
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
  },
];

interface Invoice {
  id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  product_name: string;
  invoice_url?: string;
}

const planDetails: Record<string, { name: string; description: string }> = {
  free: { name: "Free", description: "Basic features with limited usage" },
  starter: { name: "Starter", description: "For individuals getting started" },
  pro: { name: "Pro", description: "For professionals and power users" },
  enterprise: { name: "Enterprise", description: "For teams and organizations" },
};

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

export function BillingSettings() {
  const { profile, isLoading: profileLoading } = useProfile();
  const { plan: effectivePlan, isPlanInherited } = useUsage();

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isLoadingInvoices, setIsLoadingInvoices] = useState(true);
  const [isPortalLoading, setIsPortalLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  const currentPlan = effectivePlan || profile?.plan || "free";
  const planInfo = planDetails[currentPlan] || planDetails.free;

  // Fetch billing history
  const fetchInvoices = useCallback(async () => {
    try {
      setIsLoadingInvoices(true);
      const response = await api.get("/billing/invoices");
      setInvoices(response.data || []);
    } catch (error) {
      console.error("[Billing] Failed to fetch invoices:", error);
    } finally {
      setIsLoadingInvoices(false);
    }
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  const handleUpgrade = async (planType: string) => {
    // Enterprise: open email directly without loading state
    if (planType === "enterprise") {
      window.open("mailto:sales@axiohub.io?subject=Enterprise%20Plan%20Inquiry&body=Hi%2C%20I'm%20interested%20in%20the%20Enterprise%20plan.%0A%0APlease%20contact%20me%20to%20discuss%20pricing%20and%20features.", "_self");
      return;
    }

    try {
      setCheckoutLoading(planType);

      const response = await api.post("/billing/checkout", { plan: planType });
      if (response.data?.url) {
        window.location.href = response.data.url;
      } else {
        throw new Error("No checkout URL");
      }
    } catch (error) {
      console.error("[Billing] Checkout failed:", error);
      toast.error("Failed to start checkout. Please try again.");
    } finally {
      setCheckoutLoading(null);
    }
  };

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

      {/* Available Plans - Always 3 cards */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {STATIC_PLANS.map((plan) => {
            const isCurrentPlan = currentPlan === plan.type;
            const Icon = plan.icon;
            const isPopular = plan.popular;
            const isEnterprise = plan.type === "enterprise";

            return (
              <Card
                key={plan.id}
                className={cn(
                  "relative overflow-hidden transition-all flex flex-col",
                  isPopular && "border-primary shadow-lg",
                  isCurrentPlan && "ring-2 ring-primary/50",
                  isEnterprise && "border-dashed"
                )}
              >
                {isPopular && (
                  <div className="absolute top-0 right-0 bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-xs font-medium px-3 py-1 rounded-bl-lg">
                    Most Popular
                  </div>
                )}
                <CardHeader className="flex-none">
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
                        {plan.description}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="mt-4">
                    <span className="text-3xl font-bold">{plan.price}</span>
                    {plan.interval && (
                      <span className="text-muted-foreground">/{plan.interval}</span>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  <ul className="space-y-2 flex-1">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-2 text-sm">
                        <Check className={cn(
                          "h-4 w-4 shrink-0",
                          isPopular ? "text-primary" : "text-green-500"
                        )} />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className={cn(
                      "w-full mt-4",
                      isPopular && "bg-gradient-to-r from-cyan-500 to-purple-500 hover:opacity-90"
                    )}
                    variant={isCurrentPlan ? "outline" : isEnterprise ? "ghost" : isPopular ? "default" : "outline"}
                    disabled={isCurrentPlan || checkoutLoading === plan.type}
                    onClick={() => handleUpgrade(plan.type)}
                  >
                    {checkoutLoading === plan.type && (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    )}
                    {isCurrentPlan ? "Current Plan" : plan.buttonText}
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