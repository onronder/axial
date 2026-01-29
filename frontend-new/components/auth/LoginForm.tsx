
"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Eye, EyeOff, AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { safeLocalStorage } from "@/lib/storage";
import { Spinner } from "@/components/ui/spinner";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Error messages for different session/auth errors.
 * These map to the `error` query parameter set by middleware.
 */
const ERROR_MESSAGES: Record<string, { title: string; description: string }> = {
  session_expired: {
    title: "Session Expired",
    description: "Your session has expired. Please log in again to continue.",
  },
  session_not_found: {
    title: "Session Invalid",
    description: "Your session is no longer valid. Please log in again.",
  },
  auth_required: {
    title: "Authentication Required",
    description: "Please log in to access this page.",
  },
};

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, signInWithOAuth } = useAuth();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  // Support both 'redirect' (legacy) and 'redirectTo' (middleware) params
  const redirectUrl = searchParams.get("redirectTo") || searchParams.get("redirect");
  const errorParam = searchParams.get("error");

  // Handle error display and cleanup
  useEffect(() => {
    if (errorParam && ERROR_MESSAGES[errorParam]) {
      setSessionError(errorParam);
      
      // Clean up URL after showing error (prevents showing on refresh)
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.delete("error");
      window.history.replaceState({}, "", newUrl.toString());
    }
  }, [errorParam]);

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    try {
      await login(data.email, data.password);

      // Handle remember me
      if (rememberMe) {
        safeLocalStorage.setItem('remember_me', 'true');
        safeLocalStorage.setItem('user_email', data.email);
      } else {
        safeLocalStorage.removeItem('remember_me');
        safeLocalStorage.removeItem('user_email');
      }

      toast({
        title: "Welcome back!",
        description: "You've successfully logged in.",
      });
      router.push(redirectUrl || "/dashboard");
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Please check your credentials and try again.";
      toast({
        title: "Login failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle Google OAuth sign-in
   * Redirects to Google for authentication, then back to /auth/callback
   */
  const handleGoogleLogin = async () => {
    setIsOAuthLoading(true);
    try {
      await signInWithOAuth('google', {
        redirectTo: redirectUrl 
          ? `${window.location.origin}/auth/callback?next=${encodeURIComponent(redirectUrl)}`
          : undefined,
      });
      // Note: This won't return normally - user is redirected to Google
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Failed to connect with Google.";
      toast({
        title: "Google Sign-in Failed",
        description: errorMessage,
        variant: "destructive",
      });
      setIsOAuthLoading(false);
    }
  };

  const isAnyLoading = isLoading || isOAuthLoading;

  return (
    <div className="glass-card p-8 space-y-8">
      {/* Session Error Alert */}
      {sessionError && ERROR_MESSAGES[sessionError] && (
        <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
          <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
              {ERROR_MESSAGES[sessionError].title}
            </p>
            <p className="text-sm text-amber-700 dark:text-amber-300 mt-0.5">
              {ERROR_MESSAGES[sessionError].description}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setSessionError(null)}
            className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 transition-colors"
            aria-label="Dismiss"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-foreground">
          Welcome <span className="text-gradient">back</span>
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Sign in to your Axio Hub account
        </p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem className="space-y-2">
                <FormLabel className="text-sm font-medium text-foreground/80">Email</FormLabel>
                <FormControl>
                  <Input
                    className="input-glass w-full"
                    type="email"
                    placeholder="you@company.com"
                    autoComplete="email"
                    disabled={isAnyLoading}
                    {...field}
                  />
                </FormControl>
                <FormMessage className="text-destructive text-xs" />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem className="space-y-2">
                <FormLabel className="text-sm font-medium text-foreground/80">Password</FormLabel>
                <FormControl>
                  <div className="relative">
                    <Input
                      className="input-glass w-full pr-10"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      autoComplete="current-password"
                      disabled={isAnyLoading}
                      {...field}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      disabled={isAnyLoading}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </FormControl>
                <FormMessage className="text-destructive text-xs" />
              </FormItem>
            )}
          />

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={isAnyLoading}
                className="h-4 w-4 rounded border-border bg-muted text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              <span className="text-sm text-foreground/80">Remember me</span>
            </label>

            <Link
              href="/forgot-password"
              className="text-sm text-primary hover:text-primary/80 transition-colors"
            >
              Forgot password?
            </Link>
          </div>

          <Button
            type="submit"
            variant="gradient"
            className="w-full py-3 h-auto"
            disabled={isAnyLoading}
          >
            {isLoading && <Spinner className="mr-2 h-4 w-4 animate-spin" />}
            Sign In
          </Button>
        </form>
      </Form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or continue with
          </span>
        </div>
      </div>

      <Button
        type="button"
        variant="outline"
        className="w-full flex items-center justify-center gap-3 py-3 h-auto"
        disabled={isAnyLoading}
        onClick={handleGoogleLogin}
      >
        {isOAuthLoading ? (
          <Spinner className="h-4 w-4 animate-spin" />
        ) : (
          <svg className="h-4 w-4" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
        )}
        Continue with Google
      </Button>

      {/* Footer Link */}
      <p className="text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-primary hover:underline">
          Sign up
        </Link>
      </p>
    </div>
  );
}
