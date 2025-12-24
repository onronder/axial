"use client";

import { FileUp, Globe, Database, Bot, MessageSquare } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import { useIngestModal } from "@/hooks/useIngestModal";
import { useDocumentCount } from "@/hooks/useDocumentCount";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { DataSourceIcon } from "@/components/data-sources/DataSourceIcon";
import { starterQueries } from "@/lib/mockData";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  onQuerySelect: (query: string) => void;
}

const iconMap: Record<string, typeof MessageSquare> = {
  "file-text": MessageSquare,
  "alert-triangle": MessageSquare,
  "git-compare": MessageSquare,
  "file-bar-chart": MessageSquare,
};

export function EmptyState({ onQuerySelect }: EmptyStateProps) {
  const { user } = useAuth();
  const { profile } = useProfile();
  const { openModal } = useIngestModal();
  const { isEmpty, isLoading } = useDocumentCount();
  const router = useRouter();

  const displayName = profile?.first_name || user?.name?.split(" ")[0] || "there";

  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  const greeting = getGreeting();

  // Show action-oriented empty state when user has no documents
  const showDataSourcePrompt = isEmpty && !isLoading;

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-16 md:py-24">
      {/* Subtle gradient background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 left-1/2 -translate-x-1/2 w-[800px] h-[800px] rounded-full bg-gradient-to-br from-primary/5 via-accent/5 to-transparent blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full bg-gradient-to-tl from-primary/3 via-transparent to-transparent blur-3xl" />
      </div>

      <div className="max-w-2xl w-full space-y-10 text-center animate-fade-in">
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
            {showDataSourcePrompt
              ? "Let's add some data to get started"
              : "What would you like to explore today?"
            }
          </p>
        </div>

        {/* Quick Action Cards - Show when no documents */}
        {showDataSourcePrompt && (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-2 text-muted-foreground">
              <Database className="h-5 w-5" />
              <span className="text-sm font-medium">Add your first data source</span>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <QuickActionCard
                icon={<FileUp className="h-6 w-6" />}
                label="Upload PDF/Docx"
                description="Upload documents"
                onClick={() => openModal("file")}
                color="emerald"
              />
              <QuickActionCard
                icon={<DataSourceIcon sourceId="google-drive" size="lg" />}
                label="Google Drive"
                description="Connect folders"
                onClick={() => router.push("/dashboard/settings/data-sources")}
                color="blue"
              />
              <QuickActionCard
                icon={<Globe className="h-6 w-6" />}
                label="Add Website"
                description="Crawl web pages"
                onClick={() => openModal("url")}
                color="purple"
              />
            </div>
          </div>
        )}

        {/* Starter queries - Show when user has documents */}
        {!showDataSourcePrompt && (
          <div className="grid gap-5 sm:grid-cols-2">
            {starterQueries.map((query, index) => {
              const Icon = iconMap[query.icon] || MessageSquare;
              return (
                <button
                  key={query.title}
                  onClick={() => onQuerySelect(query.title)}
                  className="group relative flex items-start gap-4 rounded-xl border border-border bg-card/80 backdrop-blur-sm p-6 text-left transition-all duration-300 hover:border-primary/40 hover:bg-card hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-1 shine"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
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
                  <div className="absolute right-5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Subtle hint text */}
        <p className="text-base text-muted-foreground/60 pt-4">
          {showDataSourcePrompt
            ? "Select a data source to start chatting with your knowledge"
            : "Or type your own question below"
          }
        </p>
      </div>
    </div>
  );
}

interface QuickActionCardProps {
  icon: React.ReactNode;
  label: string;
  description: string;
  onClick: () => void;
  color: "emerald" | "blue" | "purple";
}

const colorMap = {
  emerald: "from-emerald-500 to-emerald-600 shadow-emerald-500/30",
  blue: "from-blue-500 to-blue-600 shadow-blue-500/30",
  purple: "from-purple-500 to-purple-600 shadow-purple-500/30",
};

function QuickActionCard({ icon, label, description, onClick, color }: QuickActionCardProps) {
  return (
    <button
      onClick={onClick}
      className="group flex flex-col items-center gap-3 p-6 rounded-xl border border-border bg-card/80 backdrop-blur-sm transition-all duration-300 hover:border-primary/40 hover:shadow-xl hover:-translate-y-1"
    >
      <div className={cn(
        "flex h-14 w-14 items-center justify-center rounded-xl text-white bg-gradient-to-br shadow-lg transition-transform group-hover:scale-110",
        colorMap[color]
      )}>
        {icon}
      </div>
      <div className="text-center">
        <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
          {label}
        </h3>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
    </button>
  );
}