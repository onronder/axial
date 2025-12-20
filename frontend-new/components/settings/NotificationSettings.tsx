"use client";

import { Loader2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useNotificationSettings, NotificationSetting } from "@/hooks/useNotificationSettings";

export function NotificationSettings() {
  const { emailSettings, systemSettings, isLoading, toggleSetting } = useNotificationSettings();

  const NotificationItem = ({
    setting,
    onToggle,
  }: {
    setting: NotificationSetting;
    onToggle: () => void;
  }) => (
    <div className="flex items-center justify-between py-4">
      <div className="space-y-0.5 pr-4">
        <Label htmlFor={setting.setting_key} className="text-sm font-medium cursor-pointer">
          {setting.setting_label}
        </Label>
        <p className="text-sm text-muted-foreground">{setting.setting_description}</p>
      </div>
      <Switch
        id={setting.setting_key}
        checked={setting.enabled}
        onCheckedChange={onToggle}
      />
    </div>
  );

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
        <h1 className="font-display text-2xl font-bold text-foreground">Notifications</h1>
        <p className="mt-1 text-muted-foreground">
          Manage how Axio Hub communicates with you
        </p>
      </div>

      {/* Email Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Email Notifications</CardTitle>
          <CardDescription>Configure email-based notifications</CardDescription>
        </CardHeader>
        <CardContent className="divide-y divide-border">
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
      <Card>
        <CardHeader>
          <CardTitle>System Alerts</CardTitle>
          <CardDescription>Get notified about system events</CardDescription>
        </CardHeader>
        <CardContent className="divide-y divide-border">
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