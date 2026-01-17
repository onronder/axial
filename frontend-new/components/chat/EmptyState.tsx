"use client";

import { useState } from "react";
import { 
  FileUp, 
  Globe, 
  Database, 
  MessageSquare, 
  Plus,
  Sparkles,
  ArrowRight,
  Cloud,
  Code2,
  FileText,
  Layers,
  Play,
  Server,
  Lock
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import { useIngestModal } from "@/hooks/useIngestModal";
import { useDocumentCount } from "@/hooks/useDocumentCount";
import { useDataSources } from "@/hooks/useDataSources";
import { AxioLogo } from "@/components/branding/AxioLogo";
import { DataSourceIcon } from "@/components/data-sources/DataSourceIcon";
import { starterQueries } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface EmptyStateProps {
  onQuerySelect: (query: string) => void;
}

const iconMap: Record<string, typeof MessageSquare> = {
  "file-text": MessageSquare,
  "alert-triangle": MessageSquare,
  "git-compare": MessageSquare,
  "file-bar-chart": MessageSquare,
};

// Connector showcase data - what we support
const CONNECTOR_SHOWCASE = [
  {
    category: "Cloud Storage",
    icon: Cloud,
    color: "from-blue-500 to-cyan-500",
    connectors: [
      { id: "google-drive", name: "Google Drive", description: "Docs, Sheets, PDFs" },
      { id: "onedrive", name: "OneDrive", description: "Microsoft cloud files" },
      { id: "sharepoint", name: "SharePoint", description: "Team documents" },
      { id: "dropbox", name: "Dropbox", description: "Cloud storage" },
      { id: "box", name: "Box", description: "Enterprise storage" },
      { id: "s3", name: "Amazon S3", description: "Object storage" },
    ]
  },
  {
    category: "Development",
    icon: Code2,
    color: "from-violet-500 to-purple-500",
    connectors: [
      { id: "github", name: "GitHub", description: "Repos & code" },
      { id: "sftp", name: "SFTP", description: "Secure file transfer" },
    ]
  },
  {
    category: "Productivity",
    icon: Layers,
    color: "from-amber-500 to-orange-500",
    connectors: [
      { id: "notion", name: "Notion", description: "Wikis & docs" },
    ]
  },
  {
    category: "Web & Media",
    icon: Globe,
    color: "from-emerald-500 to-green-500",
    connectors: [
      { id: "web", name: "Web Crawler", description: "Any website" },
      { id: "youtube", name: "YouTube", description: "Video transcripts" },
    ]
  },
  {
    category: "Files",
    icon: FileText,
    color: "from-rose-500 to-pink-500",
    connectors: [
      { id: "file-upload", name: "File Upload", description: "PDF, DOCX, TXT" },
    ]
  },
];

// Quick start connectors (most common)
const QUICK_START = [
  { id: "file", icon: FileUp, name: "Upload Files", description: "PDF, DOCX, TXT", color: "emerald", action: "file" as const },
  { id: "google-drive", icon: null, name: "Google Drive", description: "Connect & browse", color: "blue", action: "google-drive" as const },
  { id: "github", icon: null, name: "GitHub", description: "Repos & code", color: "violet", action: "github" as const },
  { id: "web", icon: Globe, name: "Website", description: "Crawl pages", color: "purple", action: "url" as const },
];

export function EmptyState({ onQuerySelect }: EmptyStateProps) {
  const { user } = useAuth();
  const { profile } = useProfile();
  const { openModal } = useIngestModal();
  const { isEmpty, isLoading } = useDocumentCount();
  const { connect } = useDataSources();
  const router = useRouter();
  const [showAllConnectors, setShowAllConnectors] = useState(false);

  const displayName = profile?.first_name || user?.name?.split(" ")[0] || "there";

  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  const greeting = getGreeting();
  const showDataSourcePrompt = isEmpty && !isLoading;

  const handleQuickAction = (action: "file" | "url" | "google-drive" | "github") => {
    if (action === "file" || action === "url") {
      openModal(action);
    } else if (action === "google-drive") {
      connect("google_drive");
    } else if (action === "github") {
      connect("github");
    }
  };

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-12 md:py-16">
      {/* Enhanced gradient background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-primary/10 via-violet-500/5 to-transparent blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] rounded-full bg-gradient-to-tl from-cyan-500/8 via-primary/5 to-transparent blur-3xl" />
        <div className="absolute top-1/3 right-0 w-[400px] h-[400px] rounded-full bg-gradient-to-bl from-amber-500/5 via-transparent to-transparent blur-3xl" />
      </div>

      <div className="max-w-4xl w-full space-y-8 text-center animate-fade-in">
        {/* Greeting with inline logo */}
        <div className="space-y-3">
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
              ? "Connect your data to start chatting with AI"
              : "What would you like to explore today?"
            }
          </p>
        </div>

        {/* Data Source Prompt - Show when no documents */}
        {showDataSourcePrompt && (
          <div className="space-y-8">
            {/* Quick Start Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-center gap-2">
                <Sparkles className="h-5 w-5 text-primary animate-pulse" />
                <span className="text-sm font-semibold text-foreground">Quick Start</span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {QUICK_START.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleQuickAction(item.action)}
                    className="group relative flex flex-col items-center gap-3 p-5 rounded-2xl border border-border/50 bg-gradient-to-b from-card/80 to-card/40 backdrop-blur-sm transition-all duration-300 hover:border-primary/50 hover:shadow-xl hover:shadow-primary/10 hover:-translate-y-1 overflow-hidden"
                  >
                    {/* Subtle shine effect */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                    
                    <div className={cn(
                      "flex h-14 w-14 items-center justify-center rounded-xl text-white shadow-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-xl",
                      item.color === "emerald" && "bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-emerald-500/30 group-hover:shadow-emerald-500/50",
                      item.color === "blue" && "bg-gradient-to-br from-blue-500 to-blue-600 shadow-blue-500/30 group-hover:shadow-blue-500/50",
                      item.color === "violet" && "bg-gradient-to-br from-violet-500 to-violet-600 shadow-violet-500/30 group-hover:shadow-violet-500/50",
                      item.color === "purple" && "bg-gradient-to-br from-purple-500 to-purple-600 shadow-purple-500/30 group-hover:shadow-purple-500/50",
                    )}>
                      {item.icon ? (
                        <item.icon className="h-6 w-6" />
                      ) : (
                        <DataSourceIcon sourceId={item.id} size="lg" />
                      )}
                    </div>
                    <div className="text-center">
                      <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                        {item.name}
                      </h3>
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Connector Showcase */}
            <div className="space-y-4 pt-4">
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <Database className="h-4 w-4" />
                <span className="text-sm">Connect to 12+ data sources</span>
              </div>

              {/* Connector Icons Row */}
              <div className="flex flex-wrap items-center justify-center gap-3">
                {CONNECTOR_SHOWCASE.flatMap(cat => cat.connectors).slice(0, 8).map((connector) => (
                  <div
                    key={connector.id}
                    className="group relative flex items-center justify-center h-12 w-12 rounded-xl bg-muted/50 border border-border/50 transition-all duration-300 hover:bg-muted hover:border-border hover:scale-110"
                    title={connector.name}
                  >
                    <DataSourceIcon sourceId={connector.id} size="md" />
                  </div>
                ))}
                <button
                  onClick={() => setShowAllConnectors(true)}
                  className="flex items-center justify-center h-12 w-12 rounded-xl bg-primary/10 border border-primary/20 text-primary transition-all duration-300 hover:bg-primary/20 hover:scale-110"
                  title="View all connectors"
                >
                  <Plus className="h-5 w-5" />
                </button>
              </div>

              {/* View All Button */}
              <Button
                variant="outline"
                onClick={() => setShowAllConnectors(true)}
                className="mt-4 group"
              >
                <span>View All Data Sources</span>
                <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Button>
            </div>

            {/* Features highlight */}
            <div className="grid grid-cols-3 gap-4 pt-4 max-w-xl mx-auto">
              <div className="flex flex-col items-center gap-2 p-3 rounded-lg bg-muted/30">
                <Lock className="h-5 w-5 text-primary" />
                <span className="text-xs text-muted-foreground text-center">Secure & Private</span>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 rounded-lg bg-muted/30">
                <Server className="h-5 w-5 text-primary" />
                <span className="text-xs text-muted-foreground text-center">Auto-Sync</span>
              </div>
              <div className="flex flex-col items-center gap-2 p-3 rounded-lg bg-muted/30">
                <Play className="h-5 w-5 text-primary" />
                <span className="text-xs text-muted-foreground text-center">Instant Search</span>
              </div>
            </div>
          </div>
        )}

        {/* Starter queries - Show when user has documents */}
        {!showDataSourcePrompt && (
          <>
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

            {/* Add data source button when documents exist */}
            <Button
              variant="outline"
              onClick={() => router.push("/dashboard/settings/data-sources")}
              className="mt-4 group"
            >
              <Plus className="mr-2 h-4 w-4" />
              <span>Add New Data Source</span>
            </Button>
          </>
        )}

        {/* Hint text */}
        <p className="text-sm text-muted-foreground/60 pt-2">
          {showDataSourcePrompt
            ? "Your data stays secure and private — only you can access it"
            : "Or type your own question below"
          }
        </p>
      </div>

      {/* All Connectors Modal */}
      <Dialog open={showAllConnectors} onOpenChange={setShowAllConnectors}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <Database className="h-5 w-5 text-primary" />
              Available Data Sources
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {CONNECTOR_SHOWCASE.map((category) => (
              <div key={category.category} className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg text-white bg-gradient-to-br",
                    category.color
                  )}>
                    <category.icon className="h-4 w-4" />
                  </div>
                  <h3 className="font-semibold text-foreground">{category.category}</h3>
                </div>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {category.connectors.map((connector) => (
                    <button
                      key={connector.id}
                      onClick={() => {
                        setShowAllConnectors(false);
                        if (connector.id === "file-upload") {
                          openModal("file");
                        } else if (connector.id === "web") {
                          openModal("url");
                        } else if (connector.id === "youtube") {
                          router.push("/dashboard/settings/data-sources");
                        } else {
                          router.push("/dashboard/settings/data-sources");
                        }
                      }}
                      className="group flex items-center gap-3 p-3 rounded-lg border border-border/50 bg-card/50 transition-all hover:border-primary/50 hover:bg-card text-left"
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted/50 group-hover:bg-muted transition-colors">
                        <DataSourceIcon sourceId={connector.id} size="md" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-sm text-foreground group-hover:text-primary transition-colors truncate">
                          {connector.name}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          {connector.description}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
            
            {/* Go to Settings */}
            <div className="pt-4 border-t border-border">
              <Button
                onClick={() => {
                  setShowAllConnectors(false);
                  router.push("/dashboard/settings/data-sources");
                }}
                className="w-full"
              >
                <span>Manage All Data Sources</span>
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
