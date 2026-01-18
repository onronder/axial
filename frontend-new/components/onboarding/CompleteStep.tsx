/**
 * Complete Step - Onboarding
 * 
 * Final step with celebration and completion.
 */

"use client";

import { CheckCircle2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useOnboarding } from '@/hooks/useOnboarding';
import { useEffect, useState } from 'react';
import Confetti from 'react-confetti';

export function CompleteStep() {
    const { closeOnboarding, completeOnboarding } = useOnboarding();
    const [showConfetti, setShowConfetti] = useState(true);
    const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });

    useEffect(() => {
        // Set window size for confetti
        setWindowSize({
            width: window.innerWidth,
            height: window.innerHeight,
        });

        // Stop confetti after 5 seconds
        const timer = setTimeout(() => {
            setShowConfetti(false);
        }, 5000);

        return () => clearTimeout(timer);
    }, []);

    const handleComplete = () => {
        completeOnboarding();
        closeOnboarding();
    };

    return (
        <>
            {showConfetti && (
                <Confetti
                    width={windowSize.width}
                    height={windowSize.height}
                    recycle={false}
                    numberOfPieces={200}
                />
            )}

            <div className="p-12 text-center space-y-8">
                {/* Success Icon */}
                <div className="flex justify-center">
                    <div className="relative">
                        <div className="absolute inset-0 bg-green-500/20 blur-3xl animate-pulse" />
                        <div className="relative rounded-full bg-green-500/10 p-8">
                            <CheckCircle2 className="h-20 w-20 text-green-500" />
                        </div>
                    </div>
                </div>

                {/* Header */}
                <div className="space-y-4">
                    <h2 className="text-4xl font-bold bg-gradient-to-r from-green-500 to-emerald-500 bg-clip-text text-transparent">
                        You're All Set!
                    </h2>
                    <p className="text-lg text-muted-foreground max-w-md mx-auto">
                        Your AI assistant is ready to help you find answers in your documents
                    </p>
                </div>

                {/* Next Steps */}
                <div className="max-w-md mx-auto space-y-3 text-left">
                    <h3 className="font-semibold text-center mb-4">What's Next?</h3>

                    {[
                        {
                            icon: '💬',
                            title: 'Start a conversation',
                            description: 'Ask questions about your documents',
                        },
                        {
                            icon: '📚',
                            title: 'Add more documents',
                            description: 'Build your knowledge base',
                        },
                        {
                            icon: '⚙️',
                            title: 'Customize settings',
                            description: 'Personalize your experience',
                        },
                    ].map((item, index) => (
                        <div
                            key={index}
                            className="flex items-start gap-3 p-3 rounded-lg bg-muted/50"
                        >
                            <span className="text-2xl">{item.icon}</span>
                            <div>
                                <h4 className="font-medium text-sm">{item.title}</h4>
                                <p className="text-xs text-muted-foreground">{item.description}</p>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Progress Indicator */}
                <div className="flex justify-center gap-2">
                    {[0, 1, 2, 3].map((step) => (
                        <div
                            key={step}
                            className={`h-2 rounded-full transition-all ${step === 3 ? 'w-8 bg-green-500' : 'w-2 bg-muted'
                                }`}
                        />
                    ))}
                </div>

                {/* Action */}
                <Button
                    onClick={handleComplete}
                    size="lg"
                    className="w-full gap-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:scale-[1.02] active:scale-[0.98] transition-transform"
                >
                    <Sparkles className="h-4 w-4" />
                    Start Using Axio Hub
                </Button>
            </div>
        </>
    );
}
