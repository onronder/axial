"use client";

import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { HelpSidebar } from "@/components/help/HelpSidebar";
import type { HelpArticleMeta } from "@/lib/help";

function MobileHeaderSkeleton() {
    return (
        <div className="lg:hidden border-b border-white/10 bg-background/70 backdrop-blur-xl">
            <div className="flex items-center gap-3 p-4">
                <div className="h-10 w-10 rounded-lg bg-muted/50 animate-pulse" />
                <div className="h-6 w-32 rounded bg-muted/50 animate-pulse" />
            </div>
        </div>
    );
}

const MobileHelpSheet = dynamic(
    () => import("./MobileHelpSheet"),
    {
        ssr: false,
        loading: () => <MobileHeaderSkeleton />,
    }
);

interface HelpLayoutClientProps {
    articles: HelpArticleMeta[];
    categories: Record<string, HelpArticleMeta[]>;
    children: React.ReactNode;
}

export function HelpLayoutClient({ articles, categories, children }: HelpLayoutClientProps) {
    const pathname = usePathname();
    const currentSlug = pathname.startsWith("/dashboard/help/")
        ? pathname.replace("/dashboard/help/", "")
        : undefined;

    return (
        <div className="relative min-h-full w-full overflow-hidden bg-background">
            {/* Background decorations */}
            <div className="pointer-events-none absolute inset-0">
                <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
                <div className="absolute right-0 top-0 h-80 w-80 rounded-full bg-accent/10 blur-3xl" />
                <div className="absolute inset-x-0 bottom-[-10%] h-64 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.08),transparent_45%)]" />
            </div>

            <div className="relative flex min-h-full w-full">
                {/* Desktop Sidebar */}
                <HelpSidebar
                    articles={articles}
                    categories={categories}
                    currentSlug={currentSlug}
                />

                {/* Mobile Header + Content */}
                <div className="flex flex-1 flex-col min-h-full">
                    {/* Mobile Header - Lazy loaded */}
                    <MobileHelpSheet
                        articles={articles}
                        categories={categories}
                        currentSlug={currentSlug}
                    />

                    {/* Main Content */}
                    <main className="flex-1 overflow-y-auto p-4 lg:p-8">
                        <div className="mx-auto max-w-5xl">
                            {children}
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
}
