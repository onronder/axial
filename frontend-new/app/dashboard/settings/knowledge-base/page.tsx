import type { Metadata } from "next";
import { KnowledgeBaseBrowser } from "@/components/knowledge-base/KnowledgeBaseBrowser";

export const metadata: Metadata = { title: "Knowledge Base | Axio Hub" };

export default function KnowledgeBasePage() {
    return <KnowledgeBaseBrowser />;
}
