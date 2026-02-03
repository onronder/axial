'use client';

import { SecurityLogTable } from '@/components/ghost-protocol';

export default function SecurityLogPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">Security Log</h2>
        <p className="text-sm text-muted-foreground">
          Audit trail of all security operations including document wipes, scope deletions, and data purges.
        </p>
      </div>

      <SecurityLogTable />
    </div>
  );
}
