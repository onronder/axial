"use client";

import { useState, useEffect } from "react";
import { Moon, Sun, Monitor, Loader2, User, Palette, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useProfile } from "@/hooks/useProfile";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

export function GeneralSettings() {
  const { profile, isLoading, updateProfile } = useProfile();
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const [isSaving, setIsSaving] = useState(false);

  // Local state for form fields
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  // Populate form when profile loads
  useEffect(() => {
    if (profile) {
      setFirstName(profile.first_name || "");
      setLastName(profile.last_name || "");
    }
  }, [profile]);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    await updateProfile({
      first_name: firstName,
      last_name: lastName,
    });
    setIsSaving(false);
  };

  const themeOptions = [
    { value: "light", label: "Light", icon: Sun, description: "Bright and clean" },
    { value: "dark", label: "Dark", icon: Moon, description: "Easy on the eyes" },
    { value: "system", label: "System", icon: Monitor, description: "Match your device" },
  ] as const;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading your settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Personal Information Card */}
      <Card className="overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
        <CardHeader className="border-b border-border/50 bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/20">
              <User className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Personal Information</CardTitle>
              <CardDescription>Update your profile details</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6 p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="firstName" className="text-sm font-medium">First Name</Label>
              <Input
                id="firstName"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="John"
                className="transition-all focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName" className="text-sm font-medium">Last Name</Label>
              <Input
                id="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Doe"
                className="transition-all focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">Email</Label>
            <Input
              id="email"
              type="email"
              value={user?.email || ""}
              disabled
              className="bg-muted/50 cursor-not-allowed"
            />
            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary/60" />
              Managed through your authentication provider
            </p>
          </div>
          <div className="pt-2">
            <Button
              variant="gradient"
              onClick={handleSaveProfile}
              disabled={isSaving}
              className="w-full sm:w-auto"
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Appearance Card */}
      <Card className="overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
        <CardHeader className="border-b border-border/50 bg-muted/30">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-primary text-white shadow-lg shadow-accent/20">
              <Palette className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Appearance</CardTitle>
              <CardDescription>Choose how Axio Hub looks for you</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {themeOptions.map((option) => {
              const Icon = option.icon;
              const isActive = theme === option.value;
              return (
                <button
                  key={option.value}
                  onClick={() => setTheme(option.value)}
                  className={cn(
                    "relative flex flex-col items-center gap-3 rounded-xl border-2 p-6 transition-all duration-300",
                    isActive
                      ? "border-primary bg-gradient-to-br from-primary/10 to-accent/5 shadow-lg shadow-primary/10"
                      : "border-border hover:border-primary/50 hover:bg-muted/30 hover:shadow-md"
                  )}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <div className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-white shadow-lg">
                      <Check className="h-3 w-3" />
                    </div>
                  )}
                  <div className={cn(
                    "flex h-12 w-12 items-center justify-center rounded-xl transition-all",
                    isActive
                      ? "bg-gradient-to-br from-primary to-accent text-white shadow-lg"
                      : "bg-muted text-muted-foreground"
                  )}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div className="text-center">
                    <span className={cn(
                      "block font-semibold transition-colors",
                      isActive ? "text-primary" : "text-foreground"
                    )}>
                      {option.label}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {option.description}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}