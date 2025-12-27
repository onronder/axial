"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, CheckCircle, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
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

const resetPasswordSchema = z.object({
    password: z
        .string()
        .min(8, "Password must be at least 8 characters")
        .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
        .regex(/[a-z]/, "Password must contain at least one lowercase letter")
        .regex(/[0-9]/, "Password must contain at least one number"),
    confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
});

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
    const router = useRouter();
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [isValidSession, setIsValidSession] = useState(false);
    const [isCheckingSession, setIsCheckingSession] = useState(true);

    const form = useForm<ResetPasswordFormData>({
        resolver: zodResolver(resetPasswordSchema),
        defaultValues: {
            password: "",
            confirmPassword: "",
        },
    });

    // Check if user has a valid recovery session
    useEffect(() => {
        const checkSession = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession();

                // User should have a session from the recovery link
                if (session) {
                    setIsValidSession(true);
                } else {
                    toast({
                        title: "Invalid or expired link",
                        description: "Please request a new password reset link.",
                        variant: "destructive",
                    });
                    router.push("/forgot-password");
                }
            } catch (error) {
                console.error("Error checking session:", error);
                router.push("/forgot-password");
            } finally {
                setIsCheckingSession(false);
            }
        };

        checkSession();
    }, [router, toast]);

    const onSubmit = async (data: ResetPasswordFormData) => {
        setIsLoading(true);
        try {
            const { error } = await supabase.auth.updateUser({
                password: data.password,
            });

            if (error) {
                throw error;
            }

            setIsSuccess(true);
            toast({
                title: "Password updated!",
                description: "Your password has been successfully changed.",
            });

            // Redirect to login after a short delay
            setTimeout(() => {
                router.push("/auth/login");
            }, 2000);
        } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : "Please try again.";
            toast({
                title: "Error",
                description: errorMessage,
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    };

    if (isCheckingSession) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!isValidSession) {
        return null; // Will redirect
    }

    return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="w-full max-w-md space-y-6">
                {/* Logo */}
                <div className="flex justify-center">
                    <div className="flex items-center space-x-2">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent">
                            <Lock className="h-5 w-5 text-white" />
                        </div>
                        <span className="font-display text-xl font-bold">Axio Hub</span>
                    </div>
                </div>

                {/* Header */}
                <div className="text-center">
                    <h1 className="font-display text-2xl font-bold text-foreground">
                        Set new password
                    </h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Choose a strong password for your account
                    </p>
                </div>

                {/* Form Card */}
                <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
                    {isSuccess ? (
                        <div className="text-center space-y-4">
                            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-success/10">
                                <CheckCircle className="h-6 w-6 text-success" />
                            </div>
                            <div>
                                <h3 className="font-medium text-foreground">Password updated!</h3>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    Redirecting you to login...
                                </p>
                            </div>
                        </div>
                    ) : (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="password"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>New Password</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="password"
                                                    placeholder="••••••••"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="confirmPassword"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Confirm Password</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="password"
                                                    placeholder="••••••••"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="text-xs text-muted-foreground space-y-1">
                                    <p>Password must contain:</p>
                                    <ul className="list-disc list-inside">
                                        <li>At least 8 characters</li>
                                        <li>One uppercase letter</li>
                                        <li>One lowercase letter</li>
                                        <li>One number</li>
                                    </ul>
                                </div>

                                <Button type="submit" variant="gradient" className="w-full" disabled={isLoading}>
                                    {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Update password
                                </Button>
                            </form>
                        </Form>
                    )}
                </div>
            </div>
        </div>
    );
}
