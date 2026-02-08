/**
 * Connect Step - Onboarding
 *
 * Second step for connecting data sources.
 * Triggers actual Google Drive OAuth flow via useDataSources.
 */

"use client";

import { ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useOnboarding } from '@/hooks/useOnboarding';
import { useDataSources } from '@/hooks/useDataSources';
import { useState } from 'react';

export function ConnectStep() {
    const { nextStep, prevStep, skipOnboarding } = useOnboarding();
    const { connect, isConnected } = useDataSources();
    const [isConnecting, setIsConnecting] = useState(false);

    const driveConnected = isConnected('google_drive');

    const handleConnect = async () => {
        setIsConnecting(true);
        try {
            await connect('google_drive');
            // OAuth will redirect the browser, so we don't need to handle
            // success here — the callback will return the user to the app.
        } catch {
            setIsConnecting(false);
        }
    };

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
                <div className={`border-2 border-dashed rounded-xl p-8 text-center space-y-6 transition-colors ${
                    driveConnected
                        ? 'border-green-500/50 bg-green-500/5'
                        : 'border-border hover:border-primary/50'
                }`}>
                    <div className="flex justify-center">
                        <div className="rounded-full bg-primary/10 p-6">
                            {driveConnected ? (
                                <CheckCircle2 className="h-12 w-12 text-green-500" />
                            ) : (
                                <svg className="h-12 w-12" viewBox="0 0 87.3 78" xmlns="http://www.w3.org/2000/svg">
                                    <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
                                    <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-20.4 35.3c-.8 1.4-1.2 2.95-1.2 4.5h27.5z" fill="#00ac47"/>
                                    <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.5l5.4 9.35z" fill="#ea4335"/>
                                    <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
                                    <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
                                    <path d="m73.4 26.5-10.2-17.65c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 23.8h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
                                </svg>
                            )}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h3 className="font-semibold text-lg">Google Drive</h3>
                        <p className="text-sm text-muted-foreground">
                            {driveConnected
                                ? 'Google Drive is connected'
                                : 'Access your documents, spreadsheets, and presentations'}
                        </p>
                    </div>

                    {!driveConnected && (
                        <Button
                            variant="outline"
                            className="w-full gap-2"
                            onClick={handleConnect}
                            disabled={isConnecting}
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
                            {isConnecting ? 'Connecting...' : 'Connect Google Drive'}
                        </Button>
                    )}
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
