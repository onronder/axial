'use client';

import { useEffect, useState, useCallback } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

interface TeamAccessDeniedDetail {
  reason?: string;
  message?: string;
}

export function TeamAccessDeniedBanner() {
  const [info, setInfo] = useState<TeamAccessDeniedDetail | null>(null);

  const dismiss = useCallback(() => setInfo(null), []);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<TeamAccessDeniedDetail>).detail;
      setInfo(detail || { message: 'Your team access has been revoked.' });
    };

    window.addEventListener('team-access-denied', handler);
    return () => window.removeEventListener('team-access-denied', handler);
  }, []);

  // Auto-dismiss after 30 seconds
  useEffect(() => {
    if (!info) return;
    const timer = setTimeout(dismiss, 30_000);
    return () => clearTimeout(timer);
  }, [info, dismiss]);

  if (!info) return null;

  return (
    <Alert variant="destructive" className="mx-4 mt-2 relative">
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>Team Access Revoked</AlertTitle>
      <AlertDescription className="pr-8">
        {info.message || 'Your team access has been suspended or revoked. Please contact your team admin.'}
        <a href="/login" className="underline ml-1 font-medium">Sign in with a different account</a>
      </AlertDescription>
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 h-6 w-6"
        onClick={dismiss}
      >
        <X className="h-3 w-3" />
      </Button>
    </Alert>
  );
}

export default TeamAccessDeniedBanner;
