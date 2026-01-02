"use client";

import { useState } from "react";
import { Loader2, Building2, Send } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useProfile } from "@/hooks/useProfile";

interface EnterpriseContactModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function EnterpriseContactModal({ open, onOpenChange }: EnterpriseContactModalProps) {
    const { profile } = useProfile();

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [formData, setFormData] = useState({
        name: profile?.first_name ? `${profile.first_name} ${profile.last_name || ""}`.trim() : "",
        email: "",
        company: "",
        team_size: "",
        message: "",
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.name || !formData.email || !formData.company) {
            toast.error("Please fill in all required fields");
            return;
        }

        try {
            setIsSubmitting(true);

            const response = await api.post("/billing/enterprise-inquiry", formData);

            if (response.data?.message) {
                toast.success(response.data.message);
            } else {
                toast.success("Thank you! We'll be in touch soon.");
            }

            onOpenChange(false);

            // Reset form
            setFormData({
                name: profile?.first_name ? `${profile.first_name} ${profile.last_name || ""}`.trim() : "",
                email: "",
                company: "",
                team_size: "",
                message: "",
            });

        } catch (error) {
            console.error("[EnterpriseContact] Submit error:", error);
            toast.error("Failed to submit inquiry. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Building2 className="h-5 w-5 text-primary" />
                        Contact Enterprise Sales
                    </DialogTitle>
                    <DialogDescription>
                        Tell us about your organization and we'll get back to you with custom pricing.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Name *</Label>
                            <Input
                                id="name"
                                placeholder="John Doe"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="email">Work Email *</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="john@company.com"
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="company">Company *</Label>
                            <Input
                                id="company"
                                placeholder="Acme Inc"
                                value={formData.company}
                                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="team_size">Team Size</Label>
                            <Select
                                value={formData.team_size}
                                onValueChange={(value) => setFormData({ ...formData, team_size: value })}
                            >
                                <SelectTrigger id="team_size">
                                    <SelectValue placeholder="Select size" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="1-10">1-10 people</SelectItem>
                                    <SelectItem value="11-50">11-50 people</SelectItem>
                                    <SelectItem value="51-200">51-200 people</SelectItem>
                                    <SelectItem value="201-500">201-500 people</SelectItem>
                                    <SelectItem value="500+">500+ people</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="message">How can we help?</Label>
                        <Textarea
                            id="message"
                            placeholder="Tell us about your use case, requirements, or any questions..."
                            value={formData.message}
                            onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                            rows={4}
                        />
                    </div>

                    <div className="flex justify-end gap-3 pt-4">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={isSubmitting}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting ? (
                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            ) : (
                                <Send className="h-4 w-4 mr-2" />
                            )}
                            Send Inquiry
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
