/**
 * Connect Step - Onboarding
 * 
 * Second step for connecting data sources.
 */

"use client";

import { ArrowRight, ArrowLeft, Cloud } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useOnboarding } from '@/hooks/useOnboarding';

export function ConnectStep() {
    const { nextStep, prevStep, skipOnboarding } = useOnboarding();

    return (
        <div className="p-12 space-y-8">
            {/* Header */}
            <div className="text-center space-y-2">
                <h2 className="text-3xl font-bold">Connect Your Data</h2>
                <p className="text-muted-foreground">
                    Connect Google Drive to automatically sync your documents
                </p>
            </div>

            {/* Connection Card */}
            <div className="max-w-md mx-auto">
                <div className="border-2 border-dashed border-border rounded-xl p-8 text-center space-y-6 hover:border-primary/50 transition-colors">
                    <div className="flex justify-center">
                        <div className="rounded-full bg-primary/10 p-6">
                            <Cloud className="h-12 w-12 text-primary" />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h3 className="font-semibold text-lg">Google Drive</h3>
                        <p className="text-sm text-muted-foreground">
                            Access your documents, spreadsheets, and presentations
                        </p>
                    </div>

                    <Button
                        variant="outline"
                        className="w-full gap-2"
                        onClick={() => {
                            // TODO: Trigger Google Drive connection
                            console.log('Connect Google Drive');
                        }}
                    >
                        <svg className="h-5 w-5" viewBox="0 0 24 24">
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
                        Connect Google Drive
                    </Button>
                </div>
            </div>

            {/* Progress Indicator */}
            <div className="flex justify-center gap-2">
                {[0, 1, 2, 3].map((step) => (
                    <div
                        key={step}
                        className={`h-2 rounded-full transition-all ${step === 1 ? 'w-8 bg-primary' : 'w-2 bg-muted'
                            }`}
                    />
                ))}
            </div>

            {/* Actions */}
            <div className="flex gap-3">
                <Button onClick={prevStep} variant="outline" className="flex-1 gap-2">
                    <ArrowLeft className="h-4 w-4" />
                    Back
                </Button>

                <Button onClick={nextStep} className="flex-1 gap-2">
                    Continue
                    <ArrowRight className="h-4 w-4" />
                </Button>
            </div>

            <div className="text-center">
                <button
                    onClick={skipOnboarding}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                    Skip tutorial
                </button>
            </div>
        </div>
    );
}
