"use client";

import { CreditCard, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useProfile } from "@/hooks/useProfile";
import { AxioLogo } from "@/components/branding/AxioLogo";

const planDetails: Record<string, { name: string; description: string }> = {
  free: {
    name: "Free",
    description: "Basic features with limited queries",
  },
  pro: {
    name: "Pro",
    description: "Unlimited queries, priority support, advanced integrations",
  },
  enterprise: {
    name: "Enterprise",
    description: "Custom limits, dedicated support, SSO, and more",
  },
};

export function BillingSettings() {
  const { profile, isLoading } = useProfile();

  const currentPlan = profile?.plan || "free";
  const planInfo = planDetails[currentPlan] || planDetails.free;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">Billing</h1>
        <p className="mt-1 text-muted-foreground">Manage your subscription and payment methods</p>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Current Plan
            <Badge variant="ai" className="ml-2">
              {planInfo.name}
            </Badge>
          </CardTitle>
          <CardDescription>Your current subscription tier</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-lg border border-border bg-muted/30">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
              <AxioLogo variant="icon" size="lg" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-foreground">{planInfo.name} Plan</h3>
              <p className="text-sm text-muted-foreground">
                {planInfo.description}
              </p>
            </div>
            {currentPlan === "free" && (
              <Button variant="gradient">Upgrade</Button>
            )}
            {currentPlan !== "free" && (
              <Button variant="outline">Manage</Button>
            )}
          </div>
        </CardContent>
      </Card>

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