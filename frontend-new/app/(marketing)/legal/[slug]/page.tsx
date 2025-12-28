import { notFound } from "next/navigation";
import path from "path";
import fs from "fs/promises";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LegalPageProps {
    params: Promise<{
        slug: string;
    }>;
}

// Map slug to filename
const validSlugs = ["terms", "privacy"];

async function getDocContent(slug: string) {
    if (!validSlugs.includes(slug)) {
        return null;
    }

    const filePath = path.join(process.cwd(), "content/legal", `${slug}.md`);

    try {
        const fileContent = await fs.readFile(filePath, "utf8");
        return fileContent;
    } catch (error) {
        console.error(`Error reading legal doc ${slug}:`, error);
        return null;
    }
}

export async function generateStaticParams() {
    return validSlugs.map((slug) => ({
        slug,
    }));
}

export default async function LegalPage({ params }: LegalPageProps) {
    const { slug } = await params;
    const content = await getDocContent(slug);

    if (!content) {
        notFound();
    }

    // Determine title based on slug for metadata (simple mapping)
    const title = slug === "terms" ? "Terms of Service" : "Privacy Policy";

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
                <div className="container flex h-14 max-w-screen-md items-center mx-auto px-4">
                    <Button variant="ghost" size="sm" asChild className="gap-2 -ml-2 text-muted-foreground hover:text-foreground">
                        <Link href="/">
                            <ArrowLeft className="h-4 w-4" />
                            Back to Home
                        </Link>
                    </Button>
                </div>
            </header>

            {/* Content */}
            <main className="container max-w-screen-md mx-auto px-4 py-8 md:py-12">
                <article className="prose prose-zinc dark:prose-invert max-w-none prose-headings:scroll-mt-20 prose-headings:font-semibold prose-a:text-primary hover:prose-a:text-primary/80 prose-hr:my-8">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {content}
                    </ReactMarkdown>
                </article>
            </main>

            {/* Footer */}
            <footer className="border-t border-border/40 bg-muted/50 mt-12">
                <div className="container max-w-screen-md mx-auto px-4 py-8">
                    <p className="text-center text-sm text-muted-foreground">
                        &copy; {new Date().getFullYear()} FITTECHS YAZILIM ANONIM ŞİRKETİ. All rights reserved.
                    </p>
                </div>
            </footer>
        </div>
    );
}
