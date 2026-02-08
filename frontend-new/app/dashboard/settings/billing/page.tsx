import type { Metadata } from "next";
import { BillingSettings } from "@/components/settings/BillingSettings";

export const metadata: Metadata = { title: "Billing | Axio Hub" };

export default function BillingSettingsPage() {
    return <BillingSettings />;
}
