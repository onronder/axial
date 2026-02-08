import type { Metadata } from "next";
import { TeamSettings } from "@/components/settings/TeamSettings";

export const metadata: Metadata = { title: "Team | Axio Hub" };

export default function TeamSettingsPage() {
    return <TeamSettings />;
}
