
"use client";

import { useEffect, useState, useCallback } from "react";
import { Check, CreditCard, Sparkles, Users, Zap, Building2, ExternalLink, Receipt, Calendar, AlertTriangle, RefreshCw, Download } from "lucide-react";
import { SettingsPageHeader } from "@/components/settings/SettingsPageHeader";
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
import { isValidCheckoutUrl } from "@/lib/url-validation";
import { toast } from "sonner";
import { EnterpriseContactModal } from "@/components/billing/EnterpriseContactModal";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Spinner } from "@/components/ui/spinner";

// ============================================================
// STATIC PLANS - Always show 3 plans (Starter, Pro, Enterprise)
// ============================================================

const STATIC_PLANS = [
  {
    id: "starter",
    type: "starter",
    name: "Starter",
    description: "Perfect for individuals and small projects",
    price: "$4.99",
    priceAmount: 499,
    interval: "month",
    icon: Zap,
    features: [
      "50 files, 100 MB storage",
      "5 connected data sources",
      "1 million AI tokens/month",
      "All 12 connectors (except S3)",
      "Ghost Protocol security",
      "Hybrid AI search",
      "Source citations",
      "Community support",
    ],
    buttonText: "Get Started",
  },
  {
    id: "pro",
    type: "pro",
    name: "Pro",
    description: "For professionals and growing teams",
    price: "$29",
    priceAmount: 2900,
    interval: "month",
    icon: Sparkles,
    popular: true,
    features: [
      "2,000 files, 10 GB storage",
      "100 connected data sources",
      "10 million AI tokens/month",
      "Axio Pro 🧠 smart AI",
      "Team collaboration (5 members)",
      "Priority support",
      "Everything in Starter",
    ],
    buttonText: "Upgrade to Pro",
  },
  {
    id: "enterprise",
    type: "enterprise",
    name: "Enterprise",
    description: "For organizations at scale",
    price: "Custom",
    priceAmount: 0,
    interval: "",
    icon: Building2,
    features: [
      "100,000 files, 1 TB storage",
      "1,000 data sources",
      "100 million AI tokens/month",
      "100 team members",
      "Amazon S3 connector",
      "DoD 5220.22-M secure wipe",
      "Dedicated support",
      "SLA guarantee",
      "Custom retention policies",
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

interface SubscriptionDetail {
  id: string;
  status: string;
  plan_name: string;
  price_amount: number;
  price_currency: string;
  interval: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

const planDetails: Record<string, { name: string; description: string }> = {
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
  const { plan: effectivePlan, isPlanInherited, usage } = useUsage();

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isLoadingInvoices, setIsLoadingInvoices] = useState(true);
  const [invoiceError, setInvoiceError] = useState<string | null>(null);
  const [isPortalLoading, setIsPortalLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [isEnterpriseModalOpen, setIsEnterpriseModalOpen] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [subscriptionDetail, setSubscriptionDetail] = useState<SubscriptionDetail | null>(null);
  const [isLoadingSubscription, setIsLoadingSubscription] = useState(true);

  const currentPlan = effectivePlan || profile?.plan || "free";
  // Check for both 'free' (post-cancellation) and 'none' (new user without plan)
  const isFreePlan = currentPlan === "free" || currentPlan === "none";
  const planKey = currentPlan?.startsWith("enterprise") ? "enterprise" : currentPlan;
  const planInfo = planDetails[planKey] || planDetails.starter;
  const planTitle = isFreePlan ? "No Active Plan" : `${planInfo.name} Plan`;
  const planDescription = isFreePlan
    ? "Choose a plan to unlock access."
    : planInfo.description;
  const subscriptionStatus = usage?.subscription_status || "inactive";
  const hasActiveSubscription = !isFreePlan && !["inactive", "canceled", "cancelled", "none"].includes(subscriptionStatus);

  // Fetch subscription details
  const fetchSubscriptionDetail = useCallback(async () => {
    try {
      setIsLoadingSubscription(true);
      const response = await api.get("/billing/subscription");
      if (response.data) {
        setSubscriptionDetail(response.data);
      }
    } catch (error) {
      // 404 is expected for users without subscription
      if (process.env.NODE_ENV !== 'production') {
        console.debug("[Billing] No subscription found:", error);
      }
      setSubscriptionDetail(null);
    } finally {
      setIsLoadingSubscription(false);
    }
  }, []);

  // Fetch billing history
  const fetchInvoices = useCallback(async () => {
    try {
      setIsLoadingInvoices(true);
      setInvoiceError(null);
      const response = await api.get("/billing/invoices");
      setInvoices(response.data || []);
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.error("[Billing] Failed to fetch invoices:", error);
      }
      setInvoiceError("Failed to load billing history");
    } finally {
      setIsLoadingInvoices(false);
    }
  }, []);

  useEffect(() => {
    fetchSubscriptionDetail();
    fetchInvoices();
  }, [fetchSubscriptionDetail, fetchInvoices]);

  const handleUpgrade = async (planType: string) => {
    // Enterprise: open contact form modal
    if (planType === "enterprise") {
      setIsEnterpriseModalOpen(true);
      return;
    }

    if (hasActiveSubscription) {
      await handleManageSubscription();
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
      if (process.env.NODE_ENV !== 'production') {
        console.error("[Billing] Checkout failed:", error);
      }
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
        window.open(response.data.url, "_blank", "noopener,noreferrer");
      } else {
        throw new Error("No portal URL returned");
      }
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.error("[Billing] Portal redirect failed:", error);
      }
      toast.error("Failed to open subscription portal");
    } finally {
      setIsPortalLoading(false);
    }
  };

  const handleDownloadInvoice = async (orderId: string) => {
    try {
      setDownloadingId(orderId);
      const response = await api.get(`/billing/invoices/${orderId}/download`);

      if (response.data?.url) {
        // Validate URL before opening
        if (isValidCheckoutUrl(response.data.url)) {
          window.open(response.data.url, "_blank", "noopener,noreferrer");
          toast.success("Opening invoice...");
        } else {
          throw new Error("Invalid invoice URL");
        }
      } else if (response.data?.status === "generating") {
        toast.info("Invoice is being generated. Please try again in a few seconds.");
      } else {
        throw new Error("No invoice URL returned");
      }
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.error("[Billing] Invoice download failed:", error);
      }
      toast.error("Failed to download invoice");
    } finally {
      setDownloadingId(null);
    }
  };

  const [isCancelling, setIsCancelling] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const handleCancelSubscription = async () => {
    try {
      setIsCancelling(true);
      const response = await api.delete("/billing/subscription");

      if (response.data?.success) {
        toast.success("Subscription cancelled. You'll have access until the end of your billing period.");
        setShowCancelConfirm(false);
      } else {
        throw new Error(response.data?.message || "Failed to cancel");
      }
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.error("[Billing] Cancel failed:", error);
      }
      toast.error("Failed to cancel subscription. Please try again.");
    } finally {
      setIsCancelling(false);
    }
  };

  if (profileLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <SettingsPageHeader
        icon={CreditCard}
        title="Billing"
        description="Manage your subscription and billing"
      />

      {/* Current Plan Card */}
      <Card className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-accent/5" />
        <CardHeader className="relative">
          <CardTitle className="flex items-center gap-2">
            Current Plan
            <Badge variant="ai" className="ml-2">
              {isFreePlan ? "No Active Plan" : planInfo.name}
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
              <h3 className="font-medium text-foreground">{planTitle}</h3>
              <p className="text-sm text-muted-foreground">{planDescription}</p>
            </div>
            {hasActiveSubscription && (
              <Button
                variant="outline"
                onClick={handleManageSubscription}
                disabled={isPortalLoading}
              >
                {isPortalLoading ? (
                  <Spinner className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <ExternalLink className="h-4 w-4 mr-2" />
                )}
                Manage Subscription
              </Button>
            )}
          </div>

          {/* Subscription Details */}
          {subscriptionDetail && hasActiveSubscription && (
            <div className="grid gap-4 md:grid-cols-3 mt-4">
              <div className="p-4 rounded-lg border border-border/50 bg-muted/20">
                <div className="flex items-center gap-2 text-muted-foreground mb-1">
                  <CreditCard className="h-4 w-4" />
                  <span className="text-xs font-medium uppercase tracking-wide">Billing Amount</span>
                </div>
                <p className="text-lg font-semibold">
                  {formatPrice(subscriptionDetail.price_amount, subscriptionDetail.price_currency)}
                  <span className="text-sm font-normal text-muted-foreground">
                    /{subscriptionDetail.interval}
                  </span>
                </p>
              </div>

              <div className="p-4 rounded-lg border border-border/50 bg-muted/20">
                <div className="flex items-center gap-2 text-muted-foreground mb-1">
                  <Calendar className="h-4 w-4" />
                  <span className="text-xs font-medium uppercase tracking-wide">Current Period</span>
                </div>
                <p className="text-sm">
                  {subscriptionDetail.current_period_start && subscriptionDetail.current_period_end ? (
                    <>
                      {formatDate(subscriptionDetail.current_period_start)} - {formatDate(subscriptionDetail.current_period_end)}
                    </>
                  ) : (
                    "Active"
                  )}
                </p>
              </div>

              <div className="p-4 rounded-lg border border-border/50 bg-muted/20">
                <div className="flex items-center gap-2 text-muted-foreground mb-1">
                  <RefreshCw className="h-4 w-4" />
                  <span className="text-xs font-medium uppercase tracking-wide">Renewal Status</span>
                </div>
                {subscriptionDetail.cancel_at_period_end ? (
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20">
                      Cancels at period end
                    </Badge>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20">
                      Auto-renews
                    </Badge>
                    {subscriptionDetail.current_period_end && (
                      <span className="text-xs text-muted-foreground">
                        on {formatDate(subscriptionDetail.current_period_end)}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {isLoadingSubscription && hasActiveSubscription && (
            <div className="flex items-center justify-center py-4">
              <Spinner className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}
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
            const isManageAction = hasActiveSubscription && !isEnterprise;
            const buttonLabel = isCurrentPlan && isManageAction
              ? "Manage Subscription"
              : isCurrentPlan
                ? "Current Plan"
                : isManageAction
                  ? "Manage Subscription"
                  : plan.buttonText;
            const isLoadingAction = checkoutLoading === plan.type || (isManageAction && isPortalLoading);
            const isDisabled = isLoadingAction || (!isManageAction && isCurrentPlan);

            const onPlanAction = () => {
              if (isEnterprise) {
                handleUpgrade(plan.type);
                return;
              }
              if (isManageAction) {
                handleManageSubscription();
                return;
              }
              handleUpgrade(plan.type);
            };

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
                      isPopular && "bg-gradient-to-r from-cyan-500 to-purple-500 text-white hover:scale-[1.02] active:scale-[0.98] transition-transform"
                    )}
                    variant={isCurrentPlan ? "outline" : isEnterprise ? "ghost" : isPopular ? "default" : "outline"}
                    disabled={isDisabled}
                    onClick={onPlanAction}
                  >
                    {isLoadingAction && (
                      <Spinner className="h-4 w-4 animate-spin mr-2" />
                    )}
                    {buttonLabel}
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
                <Spinner className="h-4 w-4 animate-spin" />
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
              <Spinner className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : invoiceError ? (
            <div className="text-center py-8">
              <AlertTriangle className="h-8 w-8 mx-auto text-destructive mb-2" />
              <p className="text-sm text-destructive mb-4">{invoiceError}</p>
              <Button variant="outline" size="sm" onClick={fetchInvoices}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownloadInvoice(invoice.id)}
                      disabled={downloadingId === invoice.id}
                      className="gap-2"
                    >
                      {downloadingId === invoice.id ? (
                        <Spinner className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Download className="h-4 w-4" />
                          <span className="sr-only sm:not-sr-only">Download</span>
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enterprise Contact Modal */}
      <EnterpriseContactModal
        open={isEnterpriseModalOpen}
        onOpenChange={setIsEnterpriseModalOpen}
      />

      {/* Danger Zone - Cancel Subscription */}
      {hasActiveSubscription && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription>
              Irreversible actions that affect your subscription
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 rounded-lg border border-destructive/30 bg-destructive/5">
              <div>
                <p className="font-medium">Cancel Subscription</p>
                <p className="text-sm text-muted-foreground">
                  You&apos;ll lose access to {planInfo.name} features at the end of your billing period
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={() => setShowCancelConfirm(true)}
              >
                Cancel Subscription
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cancel Confirmation Dialog */}
      <AlertDialog open={showCancelConfirm} onOpenChange={setShowCancelConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel your subscription?</AlertDialogTitle>
            <AlertDialogDescription>
              Your {planInfo.name} plan will remain active until the end of your current billing period.
              After that, access ends until you choose a plan.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isCancelling}>Keep Subscription</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancelSubscription}
              disabled={isCancelling}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isCancelling ? (
                <>
                  <Spinner className="h-4 w-4 animate-spin mr-2" />
                  Cancelling...
                </>
              ) : (
                "Yes, Cancel Subscription"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}