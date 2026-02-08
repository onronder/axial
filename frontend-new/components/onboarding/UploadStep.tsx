/**
 * Upload Step - Onboarding
 *
 * Third step for uploading first document.
 * Uses the same upload API as FileUploadZone but with simplified UX for onboarding.
 */

"use client";

import { ArrowRight, ArrowLeft, Upload, FileText, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useOnboarding } from '@/hooks/useOnboarding';
import { extractErrorMessage } from '@/lib/error-handling';
import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useToast } from '@/hooks/use-toast';
import { useIngestionProgress } from '@/hooks/useIngestionProgress';
import { getUploadUrl, uploadToStorage, ingestFileReference } from '@/lib/api';
import { calculateSHA256 } from '@/lib/hash';
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE, MIN_FILE_SIZE } from '@/lib/file-validation';
import { Spinner } from '@/components/ui/spinner';

export function UploadStep() {
    const { nextStep, prevStep, skipOnboarding } = useOnboarding();
    const { toast } = useToast();
    const { registerJob } = useIngestionProgress();
    const [hasUploaded, setHasUploaded] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadStage, setUploadStage] = useState('');

    const handleUpload = useCallback(async (acceptedFiles: File[]) => {
        if (acceptedFiles.length === 0) return;

        const file = acceptedFiles[0];
        setIsUploading(true);

        try {
            // Step 1: Calculate content hash
            setUploadStage('Calculating checksum...');
            const hash = await calculateSHA256(file);

            // Step 2: Get presigned upload URL
            setUploadStage('Preparing upload...');
            const urlResponse = await getUploadUrl(
                file.name,
                file.type || 'application/octet-stream',
                file.size,
                hash,
                false
            );

            // Step 3: Upload directly to storage
            setUploadStage('Uploading...');
            const success = await uploadToStorage(urlResponse.upload_url, file);
            if (!success) throw new Error('Upload failed');

            // Step 4: Trigger ingestion
            setUploadStage('Processing...');
            const ingestionResponse = await ingestFileReference(
                urlResponse.storage_path,
                file.name,
                file.size,
                {
                    filename: file.name,
                    size: file.size,
                    type: file.type,
                    content_hash: hash,
                    force_overwrite: false,
                }
            );

            if (ingestionResponse?.job_id) {
                registerJob(ingestionResponse.job_id);
            }

            setHasUploaded(true);
            toast({
                title: 'Document uploaded',
                description: `${file.name} is being processed.`,
            });
        } catch (error) {
            toast({
                title: 'Upload failed',
                description: extractErrorMessage(error, 'Upload failed'),
                variant: 'destructive',
            });
        } finally {
            setIsUploading(false);
            setUploadStage('');
        }
    }, [toast, registerJob]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop: handleUpload,
        accept: ACCEPTED_FILE_TYPES,
        maxSize: MAX_FILE_SIZE,
        minSize: MIN_FILE_SIZE,
        disabled: isUploading || hasUploaded,
        multiple: false,
    });

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
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-xl p-12 text-center space-y-6 transition-colors ${
                        hasUploaded
                            ? 'border-green-500/50 bg-green-500/5'
                            : isDragActive
                                ? 'border-primary bg-primary/5'
                                : isUploading
                                    ? 'border-border cursor-wait'
                                    : 'border-border hover:border-primary/50 cursor-pointer'
                    }`}
                >
                    <input {...getInputProps()} />
                    <div className="flex justify-center">
                        <div className="rounded-full bg-primary/10 p-6">
                            {hasUploaded ? (
                                <CheckCircle2 className="h-12 w-12 text-green-500" />
                            ) : isUploading ? (
                                <Spinner className="h-12 w-12 text-primary" />
                            ) : (
                                <Upload className="h-12 w-12 text-muted-foreground" />
                            )}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h3 className="font-semibold text-lg">
                            {hasUploaded
                                ? 'Document Uploaded!'
                                : isUploading
                                    ? uploadStage
                                    : isDragActive
                                        ? 'Drop your file here'
                                        : 'Drop files here'}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                            {hasUploaded
                                ? 'Your document is being processed'
                                : isUploading
                                    ? 'Please wait...'
                                    : 'or click to browse'}
                        </p>
                    </div>

                    {!hasUploaded && !isUploading && (
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
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                    Skip tutorial
                </button>
            </div>
        </div>
    );
}
