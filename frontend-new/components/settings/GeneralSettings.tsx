
"use client";

import { useState, useEffect, useRef } from "react";
import { Moon, Sun, Monitor, User, Palette, Check, AlertTriangle, Trash2, Shield, UserX } from "lucide-react";
import { SettingsPageHeader } from "@/components/settings/SettingsPageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useProfile } from "@/hooks/useProfile";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/spinner";

interface AnonymizeResponse {
  message: string;
  request_id: string;
  anonymized_at: string;
  details: {
    profile: string;
    team_members: string;
    integrations: string;
    feedback: string;
    auth: string;
  };
}

export function GeneralSettings() {
  const { profile, isLoading, updateProfile } = useProfile();
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  
  // GDPR Anonymization state
  const [anonymizeDialogOpen, setAnonymizeDialogOpen] = useState(false);
  const [anonymizeConfirmation, setAnonymizeConfirmation] = useState("");
  const [anonymizeReason, setAnonymizeReason] = useState("user_request");
  const [isAnonymizing, setIsAnonymizing] = useState(false);
  const [anonymizeResult, setAnonymizeResult] = useState<AnonymizeResponse | null>(null);

  // Local state for form fields
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [errors, setErrors] = useState<{ firstName?: string; lastName?: string }>({});

  // Populate form when profile loads
  useEffect(() => {
    if (profile) {
      setFirstName(profile.first_name || "");
      setLastName(profile.last_name || "");
    }
  }, [profile]);

  // Form validation
  const validateForm = (): boolean => {
    const newErrors: typeof errors = {};
    
    if (!firstName.trim()) {
      newErrors.firstName = 'First name is required';
    } else if (firstName.trim().length < 2) {
      newErrors.firstName = 'First name must be at least 2 characters';
    }
    
    if (!lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    } else if (lastName.trim().length < 2) {
      newErrors.lastName = 'Last name must be at least 2 characters';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSaveProfile = async () => {
    if (!validateForm()) return;
    
    setIsSaving(true);
    try {
      await updateProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
    } finally {
      setIsSaving(false);
    }
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
          <Spinner className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading your settings...</p>
        </div>
      </div>
    );
  }

  const isDirty =
    (profile?.first_name || "") !== firstName ||
    (profile?.last_name || "") !== lastName;

  return (
    <div className="space-y-6 animate-fade-in">
      <SettingsPageHeader
        icon={User}
        title="General"
        description="Manage your profile, appearance, and data privacy"
      />

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
                onChange={(e) => {
                  setFirstName(e.target.value);
                  if (errors.firstName) setErrors(prev => ({ ...prev, firstName: undefined }));
                }}
                placeholder="John"
                className={cn(
                  "transition-all focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  errors.firstName && "border-destructive focus-visible:ring-destructive"
                )}
              />
              {errors.firstName && (
                <p className="text-xs text-destructive">{errors.firstName}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName" className="text-sm font-medium">Last Name</Label>
              <Input
                id="lastName"
                value={lastName}
                onChange={(e) => {
                  setLastName(e.target.value);
                  if (errors.lastName) setErrors(prev => ({ ...prev, lastName: undefined }));
                }}
                placeholder="Doe"
                className={cn(
                  "transition-all focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  errors.lastName && "border-destructive focus-visible:ring-destructive"
                )}
              />
              {errors.lastName && (
                <p className="text-xs text-destructive">{errors.lastName}</p>
              )}
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
              disabled={isSaving || !isDirty}
              className="w-full sm:w-auto"
            >
              {isSaving ? (
                <>
                  <Spinner className="mr-2 h-4 w-4 animate-spin" />
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

      {/* Data Privacy & GDPR */}
      <Card className="overflow-hidden border-amber-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-amber-500/5">
        <CardHeader className="border-b border-amber-500/30 bg-amber-500/5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg text-amber-700 dark:text-amber-400">Data Privacy (GDPR)</CardTitle>
              <CardDescription>Manage your personal data under GDPR Article 17</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <h4 className="font-semibold text-foreground">Anonymize Personal Data</h4>
              <p className="text-sm text-muted-foreground">
                Remove personally identifiable information while keeping your account active. 
                Your documents and AI capabilities remain intact.
              </p>
            </div>
            <Dialog open={anonymizeDialogOpen} onOpenChange={(open) => {
              setAnonymizeDialogOpen(open);
              if (!open) {
                setAnonymizeConfirmation("");
                setAnonymizeResult(null);
              }
            }}>
              <DialogTrigger asChild>
                <Button variant="outline" className="w-full sm:w-auto gap-2 border-amber-500/50 text-amber-700 hover:bg-amber-500/10 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-300">
                  <UserX className="h-4 w-4" />
                  Anonymize Data
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                    <Shield className="h-5 w-5" />
                    GDPR Data Anonymization
                  </DialogTitle>
                  <DialogDescription className="text-base">
                    Exercise your GDPR &quot;Right to Erasure&quot; (Article 17) by anonymizing your personal data.
                  </DialogDescription>
                </DialogHeader>
                
                {anonymizeResult ? (
                  // Success state
                  <div className="space-y-4 py-4">
                    <div className="rounded-lg border border-green-500/30 bg-green-500/5 p-4">
                      <div className="flex items-center gap-2 text-green-700 dark:text-green-400 mb-2">
                        <Check className="h-5 w-5" />
                        <span className="font-semibold">Anonymization Complete</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{anonymizeResult.message}</p>
                      <p className="text-xs text-muted-foreground mt-2">
                        Request ID: <span className="font-mono">{anonymizeResult.request_id}</span>
                      </p>
                    </div>
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium">Anonymization Results:</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        <li className="flex items-center gap-2">
                          <span className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            anonymizeResult.details.profile === "success" ? "bg-green-500" : "bg-amber-500"
                          )} />
                          Profile: {anonymizeResult.details.profile}
                        </li>
                        <li className="flex items-center gap-2">
                          <span className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            anonymizeResult.details.team_members === "success" ? "bg-green-500" : "bg-amber-500"
                          )} />
                          Team Records: {anonymizeResult.details.team_members}
                        </li>
                        <li className="flex items-center gap-2">
                          <span className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            anonymizeResult.details.integrations?.includes("deleted") ? "bg-green-500" : "bg-amber-500"
                          )} />
                          Integrations: {anonymizeResult.details.integrations}
                        </li>
                        <li className="flex items-center gap-2">
                          <span className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            anonymizeResult.details.auth === "success" ? "bg-green-500" : "bg-amber-500"
                          )} />
                          Auth Account: {anonymizeResult.details.auth}
                        </li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  // Request form
                  <div className="space-y-4 py-4">
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium">What will be anonymized:</h4>
                      <ul className="text-sm text-muted-foreground space-y-2">
                        <li className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                          Your name → &quot;Deleted User&quot;
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                          Your email → anonymized identifier
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                          Profile picture → removed
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                          OAuth connections → deleted
                        </li>
                      </ul>
                    </div>
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium">What will be preserved:</h4>
                      <ul className="text-sm text-muted-foreground space-y-2">
                        <li className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                          Your documents & AI knowledge
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                          Chat history (anonymized)
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                          Account access
                        </li>
                      </ul>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="anonymize-reason" className="text-sm font-medium">
                        Reason for Request
                      </Label>
                      <Select value={anonymizeReason} onValueChange={setAnonymizeReason}>
                        <SelectTrigger id="anonymize-reason">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="user_request">Personal preference</SelectItem>
                          <SelectItem value="privacy_concern">Privacy concern</SelectItem>
                          <SelectItem value="leaving_organization">Leaving organization</SelectItem>
                          <SelectItem value="legal_request">Legal/Regulatory request</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
                      <Label htmlFor="anonymize-confirm" className="text-sm font-medium">
                        Type <span className="font-mono font-bold text-amber-600 dark:text-amber-400">ANONYMIZE</span> to confirm
                      </Label>
                      <Input
                        id="anonymize-confirm"
                        value={anonymizeConfirmation}
                        onChange={(e) => setAnonymizeConfirmation(e.target.value.toUpperCase())}
                        placeholder="Type ANONYMIZE here"
                        className="mt-2"
                        autoComplete="off"
                      />
                    </div>
                  </div>
                )}
                
                <DialogFooter className="gap-2 sm:gap-0">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setAnonymizeDialogOpen(false);
                      setAnonymizeConfirmation("");
                      setAnonymizeResult(null);
                    }}
                  >
                    {anonymizeResult ? "Close" : "Cancel"}
                  </Button>
                  {!anonymizeResult && (
                    <Button
                      variant="default"
                      className="bg-amber-600 hover:bg-amber-700 text-white"
                      disabled={anonymizeConfirmation !== "ANONYMIZE" || isAnonymizing}
                      onClick={async () => {
                        setIsAnonymizing(true);
                        try {
                          const response = await api.post<AnonymizeResponse>("/settings/profile/me/anonymize", {
                            reason: anonymizeReason,
                            confirmation: "ANONYMIZE",
                          });
                          setAnonymizeResult(response.data);
                          toast({
                            title: "Data Anonymized",
                            description: "Your personal information has been successfully anonymized.",
                          });
                        } catch (error: unknown) {
                          const message = error instanceof Error ? error.message : "Failed to anonymize data. Please try again.";
                          toast({
                            title: "Anonymization failed",
                            description: message,
                            variant: "destructive",
                          });
                        } finally {
                          setIsAnonymizing(false);
                        }
                      }}
                    >
                      {isAnonymizing ? (
                        <>
                          <Spinner className="mr-2 h-4 w-4 animate-spin" />
                          Anonymizing...
                        </>
                      ) : (
                        "Anonymize My Data"
                      )}
                    </Button>
                  )}
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="overflow-hidden border-destructive/50 transition-all duration-300">
        <CardHeader className="border-b border-destructive/30 bg-destructive/5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg text-destructive">Danger Zone</CardTitle>
              <CardDescription>Irreversible actions that affect your account</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <h4 className="font-semibold text-foreground">Delete Account</h4>
              <p className="text-sm text-muted-foreground">
                Permanently remove your account and all of your content. This action is not reversible.
                <br />
                <span className="text-xs">Consider &quot;Anonymize Data&quot; above if you want to keep your account.</span>
              </p>
            </div>
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="destructive" className="w-full sm:w-auto gap-2">
                  <Trash2 className="h-4 w-4" />
                  Delete Account
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-destructive">
                    <AlertTriangle className="h-5 w-5" />
                    Delete Account
                  </DialogTitle>
                  <DialogDescription className="text-base">
                    This will permanently delete your account, including:
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <ul className="text-sm text-muted-foreground space-y-2">
                    <li className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                      All uploaded documents
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                      Chat history and conversations
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                      Connected data sources
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                      AI memory of your documents
                    </li>
                  </ul>
                  <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
                    <Label htmlFor="delete-confirm" className="text-sm font-medium">
                      Type <span className="font-mono font-bold text-destructive">DELETE</span> to confirm
                    </Label>
                    <Input
                      id="delete-confirm"
                      value={deleteConfirmation}
                      onChange={(e) => setDeleteConfirmation(e.target.value)}
                      placeholder="Type DELETE here"
                      className="mt-2"
                      autoComplete="off"
                    />
                  </div>
                </div>
                <DialogFooter className="gap-2 sm:gap-0">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setDeleteDialogOpen(false);
                      setDeleteConfirmation("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={deleteConfirmation !== "DELETE" || isDeleting}
                    onClick={async () => {
                      setIsDeleting(true);
                      try {
                        await api.delete("/settings/profile/me");
                        toast({
                          title: "Account deleted",
                          description: "Your account has been permanently deleted.",
                        });
                        // Sign out and redirect
                        await logout();
                      } catch (error: unknown) {
                        const message = error instanceof Error ? error.message : "Failed to delete account. Please try again.";
                        toast({
                          title: "Deletion failed",
                          description: message,
                          variant: "destructive",
                        });
                        setIsDeleting(false);
                      }
                    }}
                  >
                    {isDeleting ? (
                      <>
                        <Spinner className="mr-2 h-4 w-4 animate-spin" />
                        Deleting...
                      </>
                    ) : (
                      "Permanently Delete"
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}