/**
 * Welcome Step - Onboarding
 * 
 * First step introducing the user to Axio Hub.
 */

"use client";

import { Sparkles, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useOnboarding } from '@/hooks/useOnboarding';
import { AxioLogo } from '@/components/branding/AxioLogo';

export function WelcomeStep() {
    const { nextStep, skipOnboarding } = useOnboarding();

    return (
        <div className="p-12 text-center space-y-8">
            {/* Logo and Header */}
            <div className="space-y-4">
                <div className="flex justify-center">
                    <div className="relative">
                        <div className="absolute inset-0 bg-gradient-to-r from-primary to-accent blur-2xl opacity-50 animate-pulse" />
                        <AxioLogo variant="icon" size="lg" className="relative" />
                    </div>
                </div>

                <div className="space-y-2">
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                        Welcome to Axio Hub
                    </h1>
                    <p className="text-lg text-muted-foreground max-w-md mx-auto">
                        Your intelligent document assistant powered by AI
                    </p>
                </div>
            </div>

            {/* Features */}
            <div className="grid gap-4 max-w-lg mx-auto text-left">
                {[
                    {
                        icon: '📄',
                        title: 'Upload Documents',
                        description: 'Connect Google Drive or upload files directly',
                    },
                    {
                        icon: '🤖',
                        title: 'AI-Powered Chat',
                        description: 'Ask questions and get instant answers from your documents',
                    },
                    {
                        icon: '⚡',
                        title: 'Lightning Fast',
                        description: 'Search through thousands of pages in seconds',
                    },
                ].map((feature, index) => (
                    <div
                        key={index}
                        className="flex items-start gap-4 p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                    >
                        <span className="text-3xl">{feature.icon}</span>
                        <div>
                            <h3 className="font-semibold">{feature.title}</h3>
                            <p className="text-sm text-muted-foreground">{feature.description}</p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Progress Indicator */}
            <div className="flex justify-center gap-2">
                {[0, 1, 2, 3].map((step) => (
                    <div
                        key={step}
                        className={`h-2 rounded-full transition-all ${step === 0 ? 'w-8 bg-primary' : 'w-2 bg-muted'
                            }`}
                    />
                ))}
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-3">
                <Button
                    onClick={nextStep}
                    size="lg"
                    className="w-full gap-2 bg-gradient-to-r from-primary to-accent hover:opacity-90"
                >
                    Get Started
                    <ArrowRight className="h-4 w-4" />
                </Button>

                <button
                    onClick={skipOnboarding}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    Skip tutorial
                </button>
            </div>
        </div>
    );
}
