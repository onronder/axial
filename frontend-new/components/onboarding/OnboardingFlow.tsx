/**
 * Onboarding Flow Component
 * 
 * Multi-step wizard for new user onboarding.
 */

"use client";

import { Dialog, DialogContent } from '@/components/ui/dialog';
import { useOnboarding } from '@/hooks/useOnboarding';
import { WelcomeStep } from './WelcomeStep';
import { ConnectStep } from './ConnectStep';
import { UploadStep } from './UploadStep';
import { CompleteStep } from './CompleteStep';

export function OnboardingFlow() {
    const { showOnboarding, currentStep, closeOnboarding } = useOnboarding();

    const renderStep = () => {
        switch (currentStep) {
            case 'welcome':
                return <WelcomeStep />;
            case 'connect':
                return <ConnectStep />;
            case 'upload':
                return <UploadStep />;
            case 'complete':
                return <CompleteStep />;
            default:
                return <WelcomeStep />;
        }
    };

    return (
        <Dialog open={showOnboarding} onOpenChange={closeOnboarding}>
            <DialogContent className="max-w-2xl p-0 overflow-hidden">
                {renderStep()}
            </DialogContent>
        </Dialog>
    );
}
