"use client";

import { useState, useCallback, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import {
  Loader2,
  Shield,
  AlertTriangle,
  Info,
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

// =============================================================================
// Constants
// =============================================================================

/**
 * Common AWS regions for S3 buckets.
 * Listed in order of popularity/usage.
 */
const AWS_REGIONS = [
  { value: "us-east-1", label: "US East (N. Virginia)" },
  { value: "us-east-2", label: "US East (Ohio)" },
  { value: "us-west-1", label: "US West (N. California)" },
  { value: "us-west-2", label: "US West (Oregon)" },
  { value: "eu-west-1", label: "Europe (Ireland)" },
  { value: "eu-west-2", label: "Europe (London)" },
  { value: "eu-west-3", label: "Europe (Paris)" },
  { value: "eu-central-1", label: "Europe (Frankfurt)" },
  { value: "eu-north-1", label: "Europe (Stockholm)" },
  { value: "ap-northeast-1", label: "Asia Pacific (Tokyo)" },
  { value: "ap-northeast-2", label: "Asia Pacific (Seoul)" },
  { value: "ap-southeast-1", label: "Asia Pacific (Singapore)" },
  { value: "ap-southeast-2", label: "Asia Pacific (Sydney)" },
  { value: "ap-south-1", label: "Asia Pacific (Mumbai)" },
  { value: "sa-east-1", label: "South America (São Paulo)" },
  { value: "ca-central-1", label: "Canada (Central)" },
  { value: "me-south-1", label: "Middle East (Bahrain)" },
  { value: "af-south-1", label: "Africa (Cape Town)" },
] as const;

/**
 * Recommended IAM policy for S3 connector.
 * Users should apply this policy to their IAM user/role.
 */
const IAM_POLICY_TEMPLATE = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AxialS3ReadAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:HeadObject",
        "s3:HeadBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET_NAME",
        "arn:aws:s3:::YOUR_BUCKET_NAME/*"
      ]
    }
  ]
}`;

// =============================================================================
// Types
// =============================================================================

interface S3ConnectModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback to change open state */
  onOpenChange: (open: boolean) => void;
  /** Callback after successful connection */
  onConnected?: () => void;
}

interface FormState {
  accessKeyId: string;
  secretAccessKey: string;
  region: string;
  bucketName: string;
  prefix: string;
}

interface FormErrors {
  accessKeyId?: string;
  secretAccessKey?: string;
  region?: string;
  bucketName?: string;
  prefix?: string;
}

type ApiErrorDetail = {
  error?: string;
  message?: string;
  current_plan?: string;
};

// =============================================================================
// Component
// =============================================================================

export function S3ConnectModal({
  open,
  onOpenChange,
  onConnected,
}: S3ConnectModalProps) {
  const { toast } = useToast();

  // Form state
  const [formState, setFormState] = useState<FormState>({
    accessKeyId: "",
    secretAccessKey: "",
    region: "us-east-1",
    bucketName: "",
    prefix: "",
  });

  // UI state
  const [errors, setErrors] = useState<FormErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSecretKey, setShowSecretKey] = useState(false);
  const [copiedPolicy, setCopiedPolicy] = useState(false);

  // Memoized IAM policy with bucket name substitution
  const iamPolicy = useMemo(() => {
    const bucketName = formState.bucketName.trim() || "YOUR_BUCKET_NAME";
    return IAM_POLICY_TEMPLATE.replace(/YOUR_BUCKET_NAME/g, bucketName);
  }, [formState.bucketName]);

  // ==========================================================================
  // Form Handlers
  // ==========================================================================

  const updateField = useCallback(
    <K extends keyof FormState>(field: K, value: FormState[K]) => {
      setFormState((prev) => ({ ...prev, [field]: value }));
      // Clear field error on change
      setErrors((prev) => ({ ...prev, [field]: undefined }));
      setApiError(null);
    },
    []
  );

  const resetForm = useCallback(() => {
    setFormState({
      accessKeyId: "",
      secretAccessKey: "",
      region: "us-east-1",
      bucketName: "",
      prefix: "",
    });
    setErrors({});
    setApiError(null);
    setShowSecretKey(false);
    setCopiedPolicy(false);
  }, []);

  const handleClose = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        resetForm();
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange, resetForm]
  );

  // ==========================================================================
  // Validation
  // ==========================================================================

  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {};
    const { accessKeyId, secretAccessKey, region, bucketName, prefix } = formState;

    // Access Key ID validation
    const trimmedAccessKey = accessKeyId.trim();
    if (!trimmedAccessKey) {
      newErrors.accessKeyId = "Access Key ID is required";
    } else if (trimmedAccessKey.length < 16) {
      newErrors.accessKeyId = "Access Key ID must be at least 16 characters";
    } else if (!/^[A-Z0-9]+$/.test(trimmedAccessKey)) {
      newErrors.accessKeyId = "Access Key ID should contain only uppercase letters and numbers";
    }

    // Secret Access Key validation
    const trimmedSecretKey = secretAccessKey.trim();
    if (!trimmedSecretKey) {
      newErrors.secretAccessKey = "Secret Access Key is required";
    } else if (trimmedSecretKey.length < 20) {
      newErrors.secretAccessKey = "Secret Access Key must be at least 20 characters";
    }

    // Region validation
    if (!region) {
      newErrors.region = "Region is required";
    }

    // Bucket name validation (AWS S3 bucket naming rules)
    const trimmedBucket = bucketName.trim();
    if (!trimmedBucket) {
      newErrors.bucketName = "Bucket name is required";
    } else if (trimmedBucket.length < 3 || trimmedBucket.length > 63) {
      newErrors.bucketName = "Bucket name must be 3-63 characters";
    } else if (!/^[a-z0-9][a-z0-9.-]*[a-z0-9]$/.test(trimmedBucket)) {
      newErrors.bucketName =
        "Bucket name must start/end with letter or number, and contain only lowercase letters, numbers, hyphens, and periods";
    }

    // Prefix validation (REQUIRED for cost protection)
    const trimmedPrefix = prefix.trim();
    if (!trimmedPrefix) {
      newErrors.prefix = "Prefix is required to prevent full bucket scans (cost protection)";
    } else if (trimmedPrefix.startsWith("/")) {
      newErrors.prefix = "Prefix should not start with a forward slash";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formState]);

  // ==========================================================================
  // Submit Handler
  // ==========================================================================

  const handleSubmit = useCallback(async () => {
    setApiError(null);

    if (!validateForm()) {
      return;
    }

    setSubmitting(true);

    try {
      await api.post("/integrations/s3/connect", {
        access_key_id: formState.accessKeyId.trim(),
        secret_access_key: formState.secretAccessKey.trim(),
        region: formState.region,
        bucket_name: formState.bucketName.trim(),
        prefix: formState.prefix.trim(),
      });

      toast({
        title: "S3 Connected",
        description: `Successfully connected to bucket "${formState.bucketName.trim()}"`,
      });

      onConnected?.();
      handleClose(false);
    } catch (err) {
      // Extract error details from API response
      const axiosError = err as {
        response?: {
          status?: number;
          data?: { detail?: string | ApiErrorDetail };
        };
      };

      const status = axiosError.response?.status;
      const detail = axiosError.response?.data?.detail;

      // Handle specific error cases
      if (status === 403) {
        // Enterprise gate
        if (typeof detail === "object" && detail?.error === "ENTERPRISE_REQUIRED") {
          setApiError(
            `S3 connector requires an Enterprise plan. Your current plan is "${detail.current_plan || "unknown"}". ` +
              "Please upgrade to Enterprise to connect S3 buckets."
          );
        } else {
          setApiError(
            "Access denied. S3 connector is available only on Enterprise plans."
          );
        }
      } else if (status === 400) {
        // Validation error from backend
        const message =
          typeof detail === "string" ? detail : detail?.message || "Invalid request";
        setApiError(message);
      } else if (status === 401) {
        setApiError(
          "Invalid AWS credentials. Please verify your Access Key ID and Secret Access Key."
        );
      } else {
        // Generic error
        const message =
          typeof detail === "string"
            ? detail
            : detail?.message || "Failed to connect to S3. Please verify your credentials and bucket settings.";
        setApiError(message);
      }
    } finally {
      setSubmitting(false);
    }
  }, [formState, validateForm, toast, onConnected, handleClose]);

  // ==========================================================================
  // Helper Actions
  // ==========================================================================

  const copyPolicyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(iamPolicy);
      setCopiedPolicy(true);
      toast({
        title: "Copied to clipboard",
        description: "IAM policy copied. Paste it in the AWS IAM console.",
      });
      // Reset copied state after 3 seconds
      setTimeout(() => setCopiedPolicy(false), 3000);
    } catch {
      toast({
        title: "Copy failed",
        description: "Please select and copy the policy manually.",
        variant: "destructive",
      });
    }
  }, [iamPolicy, toast]);

  // ==========================================================================
  // Render
  // ==========================================================================

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[560px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Connect Amazon S3
          </DialogTitle>
          <DialogDescription>
            Enter your AWS IAM credentials to connect an S3 bucket. Credentials
            are encrypted at rest and used only for read operations.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }} className="grid gap-5 py-2">
          {/* Enterprise Notice */}
          <Alert className="border-violet-500/50 bg-violet-500/5">
            <Info className="h-4 w-4 text-violet-500" />
            <AlertTitle className="text-violet-600 dark:text-violet-400">
              Enterprise Feature
            </AlertTitle>
            <AlertDescription className="text-sm text-muted-foreground">
              S3 connector is available exclusively on Enterprise plans.
              Contact sales if you need to upgrade.
            </AlertDescription>
          </Alert>

          {/* API Error Display */}
          {apiError && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Connection Failed</AlertTitle>
              <AlertDescription>{apiError}</AlertDescription>
            </Alert>
          )}

          {/* Access Key ID */}
          <div className="grid gap-2">
            <Label htmlFor="s3-access-key-id" className="text-sm font-medium">
              Access Key ID <span className="text-destructive">*</span>
            </Label>
            <Input
              id="s3-access-key-id"
              type="text"
              value={formState.accessKeyId}
              onChange={(e) => updateField("accessKeyId", e.target.value.toUpperCase())}
              placeholder="AKIAIOSFODNN7EXAMPLE"
              autoComplete="off"
              spellCheck={false}
              className={cn(errors.accessKeyId && "border-destructive")}
              aria-invalid={!!errors.accessKeyId}
              aria-describedby={errors.accessKeyId ? "access-key-error" : undefined}
            />
            {errors.accessKeyId && (
              <p id="access-key-error" className="text-xs text-destructive">
                {errors.accessKeyId}
              </p>
            )}
          </div>

          {/* Secret Access Key */}
          <div className="grid gap-2">
            <Label htmlFor="s3-secret-key" className="text-sm font-medium">
              Secret Access Key <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="s3-secret-key"
                type={showSecretKey ? "text" : "password"}
                value={formState.secretAccessKey}
                onChange={(e) => updateField("secretAccessKey", e.target.value)}
                placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                autoComplete="off"
                spellCheck={false}
                className={cn("pr-10", errors.secretAccessKey && "border-destructive")}
                aria-invalid={!!errors.secretAccessKey}
                aria-describedby={
                  errors.secretAccessKey ? "secret-key-error" : undefined
                }
              />
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                      onClick={() => setShowSecretKey(!showSecretKey)}
                      tabIndex={-1}
                    >
                      {showSecretKey ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {showSecretKey ? "Hide secret" : "Show secret"}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            {errors.secretAccessKey && (
              <p id="secret-key-error" className="text-xs text-destructive">
                {errors.secretAccessKey}
              </p>
            )}
          </div>

          {/* Region and Bucket Row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Region */}
            <div className="grid gap-2">
              <Label htmlFor="s3-region" className="text-sm font-medium">
                Region <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formState.region}
                onValueChange={(value) => updateField("region", value)}
              >
                <SelectTrigger
                  id="s3-region"
                  className={cn(errors.region && "border-destructive")}
                  aria-invalid={!!errors.region}
                >
                  <SelectValue placeholder="Select region" />
                </SelectTrigger>
                <SelectContent>
                  {AWS_REGIONS.map((region) => (
                    <SelectItem key={region.value} value={region.value}>
                      {region.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.region && (
                <p className="text-xs text-destructive">{errors.region}</p>
              )}
            </div>

            {/* Bucket Name */}
            <div className="grid gap-2">
              <Label htmlFor="s3-bucket-name" className="text-sm font-medium">
                Bucket Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="s3-bucket-name"
                type="text"
                value={formState.bucketName}
                onChange={(e) =>
                  updateField("bucketName", e.target.value.toLowerCase())
                }
                placeholder="my-documents-bucket"
                autoComplete="off"
                spellCheck={false}
                className={cn(errors.bucketName && "border-destructive")}
                aria-invalid={!!errors.bucketName}
                aria-describedby={errors.bucketName ? "bucket-error" : undefined}
              />
              {errors.bucketName && (
                <p id="bucket-error" className="text-xs text-destructive">
                  {errors.bucketName}
                </p>
              )}
            </div>
          </div>

          {/* Prefix (Required) */}
          <div className="grid gap-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="s3-prefix" className="text-sm font-medium">
                Folder Prefix <span className="text-destructive">*</span>
              </Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[250px]">
                    <p>
                      Required for cost protection. We only scan objects within
                      this prefix to prevent expensive full-bucket scans.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Input
              id="s3-prefix"
              type="text"
              value={formState.prefix}
              onChange={(e) => updateField("prefix", e.target.value)}
              placeholder="documents/knowledge-base/"
              autoComplete="off"
              spellCheck={false}
              className={cn(errors.prefix && "border-destructive")}
              aria-invalid={!!errors.prefix}
              aria-describedby={errors.prefix ? "prefix-error" : "prefix-help"}
            />
            {errors.prefix ? (
              <p id="prefix-error" className="text-xs text-destructive">
                {errors.prefix}
              </p>
            ) : (
              <p id="prefix-help" className="text-xs text-muted-foreground">
                Example: <code>documents/</code> or{" "}
                <code>knowledge-base/2024/</code>
              </p>
            )}
          </div>

          {/* IAM Policy Section */}
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="iam-policy" className="border rounded-lg px-3">
              <AccordionTrigger className="text-sm font-medium hover:no-underline">
                <span className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Recommended IAM Policy (Read-Only)
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    For security, create a dedicated IAM user with this
                    minimal read-only policy:
                  </p>
                  <div className="relative">
                    <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-48">
                      {iamPolicy}
                    </pre>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2 h-7 gap-1.5"
                      onClick={copyPolicyToClipboard}
                    >
                      {copiedPolicy ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <a
                    href="https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Learn how to create IAM policies
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          {/* Security Note */}
          <div className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/50 p-3 rounded-lg">
            <Shield className="h-4 w-4 mt-0.5 shrink-0 text-green-600" />
            <p>
              Your credentials are encrypted using AES-256 (Fernet) before
              storage. We never store plaintext secrets and only perform
              read-only operations on your bucket.
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => handleClose(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              className="min-w-[100px]"
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                "Connect"
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
