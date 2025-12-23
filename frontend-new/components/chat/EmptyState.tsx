"use client";

import { FileText, AlertTriangle, GitCompare, FileBarChart } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
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
  const { profile } = useProfile();

  // Use profile name if available, otherwise fall back to auth name
  const displayName = profile?.first_name || user?.name?.split(" ")[0] || "there";
  const greeting = getGreeting();

  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-16 md:py-24">
      {/* Subtle gradient background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 left-1/2 -translate-x-1/2 w-[800px] h-[800px] rounded-full bg-gradient-to-br from-primary/5 via-accent/5 to-transparent blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full bg-gradient-to-tl from-primary/3 via-transparent to-transparent blur-3xl" />
      </div>

      <div className="max-w-2xl w-full space-y-12 text-center animate-fade-in">
        {/* Greeting with inline logo */}
        <div className="space-y-4">
          <div className="flex items-center justify-center gap-4">
            <div className="animate-float">
              <AxioLogo variant="icon" size="xl" />
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-bold text-foreground">
              {greeting}, <span className="gradient-text">{displayName}</span>
            </h1>
          </div>
          <p className="text-xl text-muted-foreground">
            What would you like to explore today?
          </p>
        </div>

        {/* Starter query cards with premium styling */}
        <div className="grid gap-5 sm:grid-cols-2">
          {starterQueries.map((query, index) => {
            const Icon = iconMap[query.icon] || FileText;
            return (
              <button
                key={query.title}
                onClick={() => onQuerySelect(query.title)}
                className="group relative flex items-start gap-4 rounded-xl border border-border bg-card/80 backdrop-blur-sm p-6 text-left transition-all duration-300 hover:border-primary/40 hover:bg-card hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-1 shine"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {/* Icon with gradient background on hover */}
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground transition-all duration-300 group-hover:bg-gradient-to-br group-hover:from-primary group-hover:to-accent group-hover:text-white group-hover:shadow-lg group-hover:shadow-primary/30">
                  <Icon className="h-6 w-6" />
                </div>
                <div className="space-y-1.5">
                  <h3 className="font-semibold text-lg text-foreground group-hover:text-primary transition-colors">
                    {query.title}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {query.description}
                  </p>
                </div>
                {/* Hover arrow indicator */}
                <div className="absolute right-5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </button>
            );
          })}
        </div>

        {/* Subtle hint text */}
        <p className="text-base text-muted-foreground/60 pt-4">
          Or type your own question below
        </p>
      </div>
    </div>
  );
}