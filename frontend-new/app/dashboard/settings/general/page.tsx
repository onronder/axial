import type { Metadata } from "next";
import { GeneralSettings } from "@/components/settings/GeneralSettings";

export const metadata: Metadata = { title: "General Settings | Axio Hub" };

export default function GeneralSettingsPage() {
    return <GeneralSettings />;
}
