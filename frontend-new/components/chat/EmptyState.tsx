"use client";

import { FileText, AlertTriangle, GitCompare, FileBarChart } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { starterQueries } from "@/lib/mockData";
import { AxioLogo } from "@/components/branding/AxioLogo";

interface EmptyStateProps {
  onQuerySelect: (query: string) => void;
}

const iconMap: Record<string, typeof FileText> = {
  "file-text": FileText,
  "alert-triangle": AlertTriangle,
  "git-compare": GitCompare,
  "file-bar-chart": FileBarChart,
};

export function EmptyState({ onQuerySelect }: EmptyStateProps) {
  const { user } = useAuth();
  const greeting = getGreeting();

  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <div className="max-w-2xl space-y-8 text-center animate-fade-in">
        <div className="space-y-4">
          <div className="mx-auto">
            <AxioLogo variant="icon" size="xl" />
          </div>
          <div>
            <h1 className="font-display text-3xl font-bold text-foreground">
              {greeting}, {user?.name?.split(" ")[0]}
            </h1>
            <p className="mt-2 text-lg text-muted-foreground">
              Ready to analyze your data?
            </p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {starterQueries.map((query) => {
            const Icon = iconMap[query.icon] || FileText;
            return (
              <button
                key={query.title}
                onClick={() => onQuerySelect(query.title)}
                className="group flex items-start gap-4 rounded-xl border border-border bg-card p-4 text-left transition-all hover:border-primary/50 hover:bg-accent/5 hover:shadow-md"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground transition-colors group-hover:bg-primary/10 group-hover:text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground">{query.title}</h3>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {query.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}