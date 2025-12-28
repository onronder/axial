"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { CloudUpload, Globe, CheckCircle, ArrowRight, Sparkles } from "lucide-react";
import { DataSourceIcon } from "@/components/data-sources/DataSourceIcon";
import { useIngestModal } from "@/hooks/useIngestModal";
import { cn } from "@/lib/utils";

interface OnboardingModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

type Step = "welcome" | "connect" | "success";

export function OnboardingModal({ open, onOpenChange }: OnboardingModalProps) {
    const [step, setStep] = useState<Step>("welcome");
    const { openModal } = useIngestModal();
    const router = useRouter();

    const handleConnectDrive = () => {
        onOpenChange(false);
        // Navigate to data sources page with OAuth flow instead of legacy modal
        router.push("/dashboard/settings/data-sources");
    };

    const handleUploadFiles = () => {
        onOpenChange(false);
        openModal("file");
    };

    const handleAddWebsite = () => {
        onOpenChange(false);
        openModal("url");
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-xl p-0 overflow-hidden">
                <DialogTitle className="sr-only">Welcome to Axio Hub</DialogTitle>
                {step === "welcome" && (
                    <div className="p-8 space-y-6 text-center">
                        {/* Logo animation */}
                        <div className="flex justify-center">
                            <div className="relative">
                                <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-accent/20 blur-2xl rounded-full animate-pulse" />
                                <AxioLogo variant="icon" size="xl" className="relative" />
                            </div>
                        </div>

                        {/* Welcome text */}
                        <div className="space-y-3">
                            <h2 className="text-2xl font-bold text-foreground font-display">
                                Welcome to <span className="gradient-text">Axio Hub</span>
                            </h2>
                            <p className="text-muted-foreground max-w-sm mx-auto">
                                Your AI-powered knowledge assistant. Let's get started by connecting your first data source.
                            </p>
                        </div>

                        {/* CTA Button */}
                        <Button
                            size="lg"
                            onClick={() => setStep("connect")}
                            className="gap-2 px-8"
                        >
                            Get Started
                            <ArrowRight className="h-4 w-4" />
                        </Button>
                    </div>
                )}

                {step === "connect" && (
                    <div className="p-8 space-y-6">
                        <div className="text-center space-y-2">
                            <h2 className="text-xl font-bold text-foreground">
                                Connect Your Data
                            </h2>
                            <p className="text-sm text-muted-foreground">
                                Choose how you'd like to add your first documents
                            </p>
                        </div>

                        {/* Data source cards */}
                        <div className="grid gap-4">
                            <DataSourceCard
                                icon={<DataSourceIcon sourceId="google-drive" size="lg" />}
                                title="Google Drive"
                                description="Connect folders and files from your Drive"
                                onClick={handleConnectDrive}
                                gradient="from-blue-500 to-blue-600"
                            />
                            <DataSourceCard
                                icon={<CloudUpload className="h-6 w-6" />}
                                title="Upload Files"
                                description="Upload PDFs, Word docs, and text files"
                                onClick={handleUploadFiles}
                                gradient="from-emerald-500 to-emerald-600"
                            />
                            <DataSourceCard
                                icon={<Globe className="h-6 w-6" />}
                                title="Web Crawler"
                                description="Add content from any website"
                                onClick={handleAddWebsite}
                                gradient="from-purple-500 to-purple-600"
                            />
                        </div>

                        {/* Skip option */}
                        <div className="text-center">
                            <button
                                onClick={() => onOpenChange(false)}
                                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                            >
                                I'll do this later
                            </button>
                        </div>
                    </div>
                )}

                {step === "success" && (
                    <div className="p-8 space-y-6 text-center">
                        <div className="flex justify-center">
                            <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
                                <CheckCircle className="h-8 w-8 text-green-600" />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <h2 className="text-xl font-bold text-foreground">You're All Set!</h2>
                            <p className="text-muted-foreground">
                                Your documents are being processed. Start chatting with your knowledge base!
                            </p>
                        </div>
                        <Button onClick={() => onOpenChange(false)}>
                            Start Chatting
                        </Button>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}

interface DataSourceCardProps {
    icon: React.ReactNode;
    title: string;
    description: string;
    onClick: () => void;
    gradient: string;
}

function DataSourceCard({ icon, title, description, onClick, gradient }: DataSourceCardProps) {
    return (
        <button
            onClick={onClick}
            className="group relative flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:border-primary/40 hover:shadow-lg transition-all duration-200 text-left w-full"
        >
            <div className={cn(
                "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white bg-gradient-to-br shadow-lg transition-transform group-hover:scale-105",
                gradient
            )}>
                {icon}
            </div>
            <div className="flex-1">
                <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                    {title}
                </h3>
                <p className="text-sm text-muted-foreground">{description}</p>
            </div>
            <ArrowRight className="h-5 w-5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
    );
}
