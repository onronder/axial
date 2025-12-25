"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, ArrowLeft, CheckCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/lib/supabase";

const forgotPasswordSchema = z.object({
  email: z.string().email("Please enter a valid email"),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export function ForgotPasswordForm() {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const form = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setIsLoading(true);
    try {
      const redirectTo = typeof window !== 'undefined'
        ? `${window.location.origin}/auth/reset-password`
        : process.env.NEXT_PUBLIC_SITE_URL
          ? `${process.env.NEXT_PUBLIC_SITE_URL}/auth/reset-password`
          : undefined;

      const { error } = await supabase.auth.resetPasswordForEmail(data.email, {
        redirectTo,
      });

      if (error) {
        throw error;
      }

      setIsSubmitted(true);
      toast({
        title: "Reset link sent!",
        description: "Check your email for the password reset link.",
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Please try again later.";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-card p-8 space-y-8">
      {isSubmitted ? (
        <div className="text-center space-y-6 py-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success/10 animate-scale-in">
            <CheckCircle className="h-10 w-10 text-green-400" />
          </div>
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-white">Check your <span className="gradient-text">email</span></h1>
            <p className="text-white/60">
              We've sent a password reset link to your email address.
            </p>
          </div>
          <button
            className="btn-ghost-glass w-full py-3 h-auto"
            onClick={() => setIsSubmitted(false)}
          >
            Send another link
          </button>
        </div>
      ) : (
        <>
          {/* Header */}
          <div className="text-center">
            <h1 className="text-2xl font-bold text-white">
              Reset <span className="gradient-text">password</span>
            </h1>
            <p className="mt-2 text-sm text-white/60">
              We'll send you a link to reset your password
            </p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-sm font-medium text-white/80">Email</FormLabel>
                    <FormControl>
                      <Input
                        className="input-glass w-full"
                        type="email"
                        placeholder="you@company.com"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-red-400 text-xs" />
                  </FormItem>
                )}
              />

              <button
                type="submit"
                className="btn-primary-gradient w-full py-3 h-auto"
                disabled={isLoading}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin inline" />}
                Send Reset Link
              </button>
            </form>
          </Form>

          {/* Footer Link */}
          <p className="text-center text-sm text-white/60">
            Remember your password?{" "}
            <Link href="/login" className="text-accent-cyan hover:underline transition-colors">
              Sign in
            </Link>
          </p>
        </>
      )}
    </div>
  );
}