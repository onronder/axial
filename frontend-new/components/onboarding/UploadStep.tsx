/**
 * Upload Step - Onboarding
 * 
 * Third step for uploading first document.
 */

"use client";

import { ArrowRight, ArrowLeft, Upload, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useOnboarding } from '@/hooks/useOnboarding';
import { useState } from 'react';

export function UploadStep() {
    const { nextStep, prevStep, skipOnboarding } = useOnboarding();
    const [hasUploaded, setHasUploaded] = useState(false);

    const handleFileUpload = () => {
        // TODO: Trigger file upload
        setHasUploaded(true);
        console.log('Upload file');
    };

    return (
        <div className="p-12 space-y-8">
            {/* Header */}
            <div className="text-center space-y-2">
                <h2 className="text-3xl font-bold">Upload Your First Document</h2>
                <p className="text-muted-foreground">
                    Add a document to start chatting with your AI assistant
                </p>
            </div>

            {/* Upload Area */}
            <div className="max-w-md mx-auto">
                <div
                    className="border-2 border-dashed border-border rounded-xl p-12 text-center space-y-6 hover:border-primary/50 transition-colors cursor-pointer"
                    onClick={handleFileUpload}
                >
                    <div className="flex justify-center">
                        <div className="rounded-full bg-primary/10 p-6">
                            {hasUploaded ? (
                                <FileText className="h-12 w-12 text-primary" />
                            ) : (
                                <Upload className="h-12 w-12 text-muted-foreground" />
                            )}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h3 className="font-semibold text-lg">
                            {hasUploaded ? 'Document Uploaded!' : 'Drop files here'}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                            {hasUploaded
                                ? 'Your document is being processed'
                                : 'or click to browse'}
                        </p>
                    </div>

                    {!hasUploaded && (
                        <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                            <span className="px-2 py-1 rounded-full bg-muted">PDF</span>
                            <span className="px-2 py-1 rounded-full bg-muted">DOCX</span>
                            <span className="px-2 py-1 rounded-full bg-muted">TXT</span>
                            <span className="px-2 py-1 rounded-full bg-muted">MD</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Progress Indicator */}
            <div className="flex justify-center gap-2">
                {[0, 1, 2, 3].map((step) => (
                    <div
                        key={step}
                        className={`h-2 rounded-full transition-all ${step === 2 ? 'w-8 bg-primary' : 'w-2 bg-muted'
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
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                    Skip tutorial
                </button>
            </div>
        </div>
    );
}
