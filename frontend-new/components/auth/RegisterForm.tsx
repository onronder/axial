
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Eye, EyeOff } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
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
import { Spinner } from "@/components/ui/spinner";

const registerSchema = z.object({
  firstName: z.string().min(1, "First name is required").max(50, "First name is too long"),
  lastName: z.string().min(1, "Last name is required").max(50, "Last name is too long"),
  email: z.string().email("Please enter a valid email"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one number"),
  termsAccepted: z.boolean().refine((val) => val === true, {
    message: "You must accept the Terms and Privacy Policy",
  }),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export function RegisterForm() {
  const router = useRouter();
  const { register, signInWithOAuth } = useAuth();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const form = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      termsAccepted: false,
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    try {
      await register(data.firstName, data.lastName, data.email, data.password);
      toast({
        title: "Account created!",
        description: "Welcome to Axio Hub.",
      });
      router.push("/dashboard");
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Please try again later.";
      toast({
        title: "Registration failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle Google OAuth sign-up
   * Redirects to Google for authentication, then back to /auth/callback
   * Google will provide name and email automatically
   */
  const handleGoogleSignup = async () => {
    setIsOAuthLoading(true);
    try {
      await signInWithOAuth('google');
      // Note: This won't return normally - user is redirected to Google
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Failed to connect with Google.";
      toast({
        title: "Google Sign-up Failed",
        description: errorMessage,
        variant: "destructive",
      });
      setIsOAuthLoading(false);
    }
  };

  const isAnyLoading = isLoading || isOAuthLoading;

  return (
    <div className="glass-card p-8 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-foreground">
          Create an <span className="text-gradient">account</span>
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Start your journey with Axio Hub
        </p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="firstName"
              render={({ field }) => (
                <FormItem className="space-y-2">
                  <FormLabel className="text-sm font-medium text-foreground/80">First Name</FormLabel>
                  <FormControl>
                    <Input
                      className="input-glass w-full"
                      placeholder="John"
                      autoComplete="given-name"
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
              name="lastName"
              render={({ field }) => (
                <FormItem className="space-y-2">
                  <FormLabel className="text-sm font-medium text-foreground/80">Last Name</FormLabel>
                  <FormControl>
                    <Input
                      className="input-glass w-full"
                      placeholder="Doe"
                      autoComplete="family-name"
                      disabled={isAnyLoading}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-destructive text-xs" />
                </FormItem>
              )}
            />
          </div>

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
                      autoComplete="new-password"
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
                <p className="text-xs text-muted-foreground">
                  Must be 8+ characters with uppercase, lowercase, and number
                </p>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="termsAccepted"
            render={({ field }) => (
              <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md p-2">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    disabled={isAnyLoading}
                    className="border-border data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
                  />
                </FormControl>
                <div className="space-y-1 leading-none">
                  <FormLabel className="text-sm font-normal text-foreground/80">
                    I agree to the{" "}
                    <Link
                      href="/legal/terms"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline hover:text-primary/80"
                    >
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link
                      href="/legal/privacy"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline hover:text-primary/80"
                    >
                      Privacy Policy
                    </Link>
                  </FormLabel>
                  <FormMessage className="text-destructive text-xs" />
                </div>
              </FormItem>
            )}
          />

          <Button
            type="submit"
            variant="gradient"
            className="w-full py-3 h-auto mt-2"
            disabled={isAnyLoading}
          >
            {isLoading && <Spinner className="mr-2 h-4 w-4 animate-spin" />}
            Create Account
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
        onClick={handleGoogleSignup}
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

      <p className="text-center text-xs text-muted-foreground">
        By signing up with Google, you agree to our{" "}
        <Link href="/legal/terms" className="text-primary hover:underline">
          Terms
        </Link>{" "}
        and{" "}
        <Link href="/legal/privacy" className="text-primary hover:underline">
          Privacy Policy
        </Link>
      </p>

      {/* Footer Link */}
      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="text-primary hover:underline transition-colors">
          Sign in
        </Link>
      </p>
    </div>
  );
}
