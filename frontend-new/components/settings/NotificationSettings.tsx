
"use client";

import { useState } from "react";
import { Bell, Mail, ShieldCheck } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useNotificationSettings, NotificationSetting } from "@/hooks/useNotificationSettings";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export function NotificationSettings() {
  const { emailSettings, systemSettings, isLoading, isResetting, toggleSetting, resetToDefaults } = useNotificationSettings();
  const [confirming, setConfirming] = useState(false);

  const NotificationItem = ({
    setting,
    onToggle,
  }: {
    setting: NotificationSetting;
    onToggle: () => void;
  }) => (
    <div className="flex items-center justify-between py-4">
      <div className="space-y-1 pr-4">
        <Label htmlFor={setting.setting_key} className="text-sm font-medium cursor-pointer text-foreground">
          {setting.setting_label}
        </Label>
        <p className="text-sm text-muted-foreground">{setting.setting_description}</p>
      </div>
      <Switch
        id={setting.setting_key}
        checked={setting.enabled}
        onCheckedChange={onToggle}
        className="data-[state=checked]:bg-primary"
      />
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8 relative">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-10 top-0 h-48 w-48 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute right-0 top-10 h-56 w-56 rounded-full bg-accent/15 blur-3xl" />
      </div>

      <div className="relative">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-glow">
              <Bell className="h-5 w-5" />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold text-foreground">Notifications</h1>
              <p className="mt-1 text-muted-foreground">
                Manage how Axio Hub communicates with you
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="border-white/20 bg-white/5 hover:bg-white/10"
              disabled={isResetting}
              onClick={async () => {
                if (!confirming) {
                  setConfirming(true);
                  return;
                }
                const ok = await resetToDefaults();
                if (ok) {
                  setConfirming(false);
                }
              }}
            >
              {isResetting ? (
                <Spinner className="h-4 w-4 animate-spin" />
              ) : confirming ? (
                "Click again to confirm"
              ) : (
                "Reset to defaults"
              )}
            </Button>
            {confirming && (
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setConfirming(false)}
              >
                Cancel
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Email Notifications */}
      <Card className="relative overflow-hidden glass-card border-white/10 shadow-glow">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background/40 to-accent/5 pointer-events-none" />
        <CardHeader className="relative flex flex-row items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Mail className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-lg">Email Notifications</CardTitle>
            <CardDescription>Configure email-based notifications</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="relative divide-y divide-white/10">
          {emailSettings.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">No email notification settings available.</p>
          ) : (
            emailSettings.map((setting) => (
              <NotificationItem
                key={setting.setting_key}
                setting={setting}
                onToggle={() => toggleSetting(setting.setting_key)}
              />
            ))
          )}
        </CardContent>
      </Card>

      {/* System Alerts */}
      <Card className="relative overflow-hidden glass-card border-white/10 shadow-glow">
        <div className="absolute inset-0 bg-gradient-to-br from-accent/5 via-background/40 to-primary/5 pointer-events-none" />
        <CardHeader className="relative flex flex-row items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent-foreground">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-lg">System Alerts</CardTitle>
            <CardDescription>Get notified about system events</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="relative divide-y divide-white/10">
          {systemSettings.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">No system alert settings available.</p>
          ) : (
            systemSettings.map((setting) => (
              <NotificationItem
                key={setting.setting_key}
                setting={setting}
                onToggle={() => toggleSetting(setting.setting_key)}
              />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}