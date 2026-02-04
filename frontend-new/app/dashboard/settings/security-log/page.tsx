'use client';

import { Lock } from 'lucide-react';
import { SecurityLogTable } from '@/components/ghost-protocol';
import { SettingsPageHeader } from '@/components/settings/SettingsPageHeader';

export default function SecurityLogPage() {
  return (
    <div className="space-y-6">
      <SettingsPageHeader
        icon={Lock}
        title="Security Log"
        description="Security operations audit trail"
      />

      <SecurityLogTable />
    </div>
  );
}
