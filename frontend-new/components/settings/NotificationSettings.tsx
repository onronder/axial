"use client";

import { useState } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

interface NotificationSetting {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
}

export function NotificationSettings() {
  const { toast } = useToast();

  const [emailNotifications, setEmailNotifications] = useState<NotificationSetting[]>([
    {
      id: "weekly-digest",
      label: "Weekly Digest",
      description: "Receive a weekly summary of activity",
      enabled: true,
    },
    {
      id: "new-features",
      label: "New Feature Announcements",
      description: "Get notified about new product updates",
      enabled: false,
    },
  ]);

  const [systemAlerts, setSystemAlerts] = useState<NotificationSetting[]>([
    {
      id: "ingestion-completed",
      label: "Ingestion Completed",
      description: "Get notified when a large file finishes processing",
      enabled: true,
    },
    {
      id: "ingestion-failed",
      label: "Ingestion Failed",
      description: "Get notified if a connector fails",
      enabled: true,
    },
  ]);

  const handleToggle = (
    settings: NotificationSetting[],
    setSettings: React.Dispatch<React.SetStateAction<NotificationSetting[]>>,
    id: string
  ) => {
    setSettings((prev) =>
      prev.map((setting) =>
        setting.id === id ? { ...setting, enabled: !setting.enabled } : setting
      )
    );
    toast({
      title: "Preference updated",
      description: "Your notification settings have been saved.",
    });
  };

  const NotificationItem = ({
    setting,
    onToggle,
  }: {
    setting: NotificationSetting;
    onToggle: () => void;
  }) => (
    <div className="flex items-center justify-between py-4">
      <div className="space-y-0.5 pr-4">
        <Label htmlFor={setting.id} className="text-sm font-medium cursor-pointer">
          {setting.label}
        </Label>
        <p className="text-sm text-muted-foreground">{setting.description}</p>
      </div>
      <Switch
        id={setting.id}
        checked={setting.enabled}
        onCheckedChange={onToggle}
      />
    </div>
  );

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
          {emailNotifications.map((setting) => (
            <NotificationItem
              key={setting.id}
              setting={setting}
              onToggle={() => handleToggle(emailNotifications, setEmailNotifications, setting.id)}
            />
          ))}
        </CardContent>
      </Card>

      {/* System Alerts */}
      <Card>
        <CardHeader>
          <CardTitle>System Alerts</CardTitle>
          <CardDescription>Get notified about system events</CardDescription>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {systemAlerts.map((setting) => (
            <NotificationItem
              key={setting.id}
              setting={setting}
              onToggle={() => handleToggle(systemAlerts, setSystemAlerts, setting.id)}
            />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}