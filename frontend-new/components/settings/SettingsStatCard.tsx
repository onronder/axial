"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SettingsStatCardProps {
  icon: React.ElementType;
  iconColorClass?: string;
  iconBgClass?: string;
  label: string;
  value: React.ReactNode;
  description?: string;
  className?: string;
}

export function SettingsStatCard({
  icon: Icon,
  iconColorClass = "text-primary",
  iconBgClass = "bg-primary/10",
  label,
  value,
  description,
  className,
}: SettingsStatCardProps) {
  return (
    <Card className={className}>
      <CardContent className="flex items-center gap-4 p-4">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg shrink-0",
            iconBgClass
          )}
        >
          <Icon className={cn("h-5 w-5", iconColorClass)} />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
