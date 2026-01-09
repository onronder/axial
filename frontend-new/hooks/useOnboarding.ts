/**
 * Onboarding Hook
 * 
 * Manages onboarding state and progress.
 */

"use client";

import { useState, useEffect } from 'react';

export type OnboardingStep = 'welcome' | 'connect' | 'upload' | 'complete';

export function useOnboarding() {
    const [showOnboarding, setShowOnboarding] = useState(false);
    const [currentStep, setCurrentStep] = useState<OnboardingStep>('welcome');
    const [isComplete, setIsComplete] = useState(false);

    // Check if user needs onboarding
    useEffect(() => {
        if (typeof window === 'undefined') return;

        const hasCompletedOnboarding = localStorage.getItem('onboarding_complete');
        const hasSkippedOnboarding = localStorage.getItem('onboarding_skipped');

        if (!hasCompletedOnboarding && !hasSkippedOnboarding) {
            // Show onboarding after a short delay
            setTimeout(() => {
                setShowOnboarding(true);
            }, 1000);
        }
    }, []);

    const nextStep = () => {
        const steps: OnboardingStep[] = ['welcome', 'connect', 'upload', 'complete'];
        const currentIndex = steps.indexOf(currentStep);

        if (currentIndex < steps.length - 1) {
            setCurrentStep(steps[currentIndex + 1]);
        }
    };

    const prevStep = () => {
        const steps: OnboardingStep[] = ['welcome', 'connect', 'upload', 'complete'];
        const currentIndex = steps.indexOf(currentStep);

        if (currentIndex > 0) {
            setCurrentStep(steps[currentIndex - 1]);
        }
    };

    const completeOnboarding = () => {
        localStorage.setItem('onboarding_complete', 'true');
        setIsComplete(true);
        setCurrentStep('complete');
    };

    const skipOnboarding = () => {
        localStorage.setItem('onboarding_skipped', 'true');
        setShowOnboarding(false);
    };

    const closeOnboarding = () => {
        setShowOnboarding(false);
    };

    return {
        showOnboarding,
        currentStep,
        isComplete,
        nextStep,
        prevStep,
        completeOnboarding,
        skipOnboarding,
        closeOnboarding,
    };
}
