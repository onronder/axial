'use client';

import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ConsentToggleProps {
  label: string;
  description?: string;
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  consentedAt?: string | null;
  compact?: boolean;
  disabled?: boolean;
}

function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export function ConsentToggle({
  label,
  description,
  enabled,
  onChange,
  consentedAt,
  compact = false,
  disabled = false,
}: ConsentToggleProps) {
  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <Switch
          checked={enabled}
          onCheckedChange={onChange}
          disabled={disabled}
          className="scale-75"
        />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
    );
  }

  return (
    <div className={cn(
      'p-4 rounded-lg border transition-colors duration-200',
      enabled ? 'border-primary/30 bg-primary/5' : 'border-border bg-muted/5'
    )}>
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <div className="flex items-center gap-2">
            <Label
              htmlFor={`consent-${label}`}
              className={cn(
                'font-medium cursor-pointer',
                enabled ? 'text-primary' : 'text-foreground'
              )}
            >
              {label}
            </Label>
            {enabled && (
              <Badge
                variant="outline"
                className="text-[10px] text-green-400 border-green-500/30"
              >
                ENABLED
              </Badge>
            )}
          </div>
          {description && (
            <p className="text-sm text-muted-foreground">
              {description}
            </p>
          )}
          {consentedAt && enabled && (
            <p className="text-[10px] text-muted-foreground">
              Consent recorded: {formatDate(consentedAt)}
            </p>
          )}
        </div>

        <Switch
          id={`consent-${label}`}
          checked={enabled}
          onCheckedChange={onChange}
          disabled={disabled}
        />
      </div>
    </div>
  );
}

export default ConsentToggle;
