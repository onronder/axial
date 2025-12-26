"use client";

import {
    Diamond,
    Table2,
    ListChecks,
    LayoutGrid,
    Cloud,
    Box,
    Package,
    Server,
    Hash,
    Users,
    Clock,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";

interface ComingSoonIntegration {
    id: string;
    name: string;
    description: string;
    icon: React.ReactNode;
    category: "Project & Ops" | "Enterprise Storage" | "Communication";
    badge: "Coming Soon" | "Waitlist" | "Enterprise";
}

const COMING_SOON_INTEGRATIONS: ComingSoonIntegration[] = [
    // Project & Ops
    {
        id: "jira",
        name: "Jira",
        description: "Issue tracking & project management",
        icon: <Diamond className="h-6 w-6" />,
        category: "Project & Ops",
        badge: "Coming Soon",
    },
    {
        id: "monday",
        name: "Monday.com",
        description: "Work OS & project boards",
        icon: <Table2 className="h-6 w-6" />,
        category: "Project & Ops",
        badge: "Coming Soon",
    },
    {
        id: "asana",
        name: "Asana",
        description: "Task & project management",
        icon: <ListChecks className="h-6 w-6" />,
        category: "Project & Ops",
        badge: "Coming Soon",
    },
    {
        id: "trello",
        name: "Trello",
        description: "Kanban boards & workflows",
        icon: <LayoutGrid className="h-6 w-6" />,
        category: "Project & Ops",
        badge: "Coming Soon",
    },
    // Enterprise Storage
    {
        id: "onedrive",
        name: "Microsoft OneDrive",
        description: "Microsoft cloud storage",
        icon: <Cloud className="h-6 w-6" />,
        category: "Enterprise Storage",
        badge: "Coming Soon",
    },
    {
        id: "box",
        name: "Box",
        description: "Enterprise content management",
        icon: <Box className="h-6 w-6" />,
        category: "Enterprise Storage",
        badge: "Enterprise",
    },
    {
        id: "dropbox",
        name: "Dropbox",
        description: "Cloud file storage & sharing",
        icon: <Package className="h-6 w-6" />,
        category: "Enterprise Storage",
        badge: "Coming Soon",
    },
    {
        id: "sftp",
        name: "Industrial Sync (SFTP)",
        description: "Legacy systems & maintenance logs",
        icon: <Server className="h-6 w-6" />,
        category: "Enterprise Storage",
        badge: "Enterprise",
    },
    // Communication
    {
        id: "slack",
        name: "Slack",
        description: "Channels, threads & DMs",
        icon: <Hash className="h-6 w-6" />,
        category: "Communication",
        badge: "Coming Soon",
    },
    {
        id: "teams",
        name: "Microsoft Teams",
        description: "Team chat & collaboration",
        icon: <Users className="h-6 w-6" />,
        category: "Communication",
        badge: "Enterprise",
    },
];

const CATEGORY_ORDER = ["Project & Ops", "Enterprise Storage", "Communication"] as const;

export function ComingSoonIntegrations() {
    const { toast } = useToast();

    const handleClick = (integration: ComingSoonIntegration) => {
        toast({
            title: `${integration.name} coming soon!`,
            description: "We've noted your interest. You'll be notified when it's available.",
        });
    };

    // Group by category
    const groupedIntegrations = COMING_SOON_INTEGRATIONS.reduce((acc, integration) => {
        if (!acc[integration.category]) {
            acc[integration.category] = [];
        }
        acc[integration.category].push(integration);
        return acc;
    }, {} as Record<string, ComingSoonIntegration[]>);

    return (
        <div className="space-y-6 mt-12">
            {/* Section Header */}
            <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 text-muted-foreground" />
                <h2 className="font-display text-xl font-semibold text-foreground">
                    Coming Soon — Enterprise Connectors
                </h2>
                <Badge variant="outline" className="text-xs">
                    50+ Platforms
                </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
                Connect to your entire tech stack. These integrations are in development.
            </p>

            {/* Grid by Category */}
            <div className="space-y-8">
                {CATEGORY_ORDER.map((category) => {
                    const integrations = groupedIntegrations[category];
                    if (!integrations) return null;

                    return (
                        <div key={category} className="space-y-4">
                            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                                {category}
                            </h3>
                            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                                {integrations.map((integration) => (
                                    <Card
                                        key={integration.id}
                                        className="relative cursor-pointer opacity-60 grayscale hover:opacity-100 hover:grayscale-0 transition-all duration-300 border-dashed"
                                        onClick={() => handleClick(integration)}
                                    >
                                        {/* Badge */}
                                        <Badge
                                            variant={integration.badge === "Enterprise" ? "default" : "secondary"}
                                            className="absolute top-3 right-3 text-xs"
                                        >
                                            {integration.badge}
                                        </Badge>

                                        <CardContent className="p-4">
                                            <div className="flex items-start gap-3">
                                                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                                                    {integration.icon}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <h4 className="font-medium text-foreground truncate">
                                                        {integration.name}
                                                    </h4>
                                                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                                        {integration.description}
                                                    </p>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
