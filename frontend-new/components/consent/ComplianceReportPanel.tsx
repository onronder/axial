'use client';

/**
 * ComplianceReportPanel Component
 * 
 * Displays detailed GDPR/CCPA/KVKK compliance information.
 * Shows metrics, compliance status, and actionable recommendations.
 */

import { useState } from 'react';
import { format } from 'date-fns';
import {
  Shield,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Folder,
  Building,
  Download,
  RefreshCw,
  Info,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { useConsent, type ComplianceReport } from '@/hooks/useConsent';

// =============================================================================
// Types
// =============================================================================

interface ComplianceReportPanelProps {
  variant?: 'inline' | 'modal';
}

// =============================================================================
// Helper Functions
// =============================================================================

function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-500';
  if (score >= 70) return 'text-amber-500';
  return 'text-red-500';
}

function getScoreBgColor(score: number): string {
  if (score >= 90) return 'bg-green-500/10 border-green-500/30';
  if (score >= 70) return 'bg-amber-500/10 border-amber-500/30';
  return 'bg-red-500/10 border-red-500/30';
}

function getStatusIcon(status: string): typeof CheckCircle2 {
  switch (status.toLowerCase()) {
    case 'compliant':
      return CheckCircle2;
    case 'warning':
      return AlertTriangle;
    default:
      return AlertTriangle;
  }
}

function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'compliant':
      return 'text-green-500';
    case 'warning':
      return 'text-amber-500';
    default:
      return 'text-red-500';
  }
}

// =============================================================================
// Report Content Component
// =============================================================================

function ReportContent({ report, onRefetch }: { report: ComplianceReport | null; onRefetch: () => void }) {
  if (!report) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>No compliance report available</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={onRefetch}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Generate Report
        </Button>
      </div>
    );
  }

  const scoreColor = getScoreColor(report.complianceScore);
  const scoreBgColor = getScoreBgColor(report.complianceScore);
  const StatusIcon = getStatusIcon(report.complianceStatus);
  const statusColor = getStatusColor(report.complianceStatus);

  // Calculate override percentage
  const overridePercentage = report.totalDocuments > 0
    ? Math.round((report.documentOverrides / report.totalDocuments) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Score Overview */}
      <div className={cn('p-6 rounded-lg border', scoreBgColor)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={cn('text-5xl font-bold font-mono', scoreColor)}>
              {report.complianceScore}%
            </div>
            <div>
              <div className="flex items-center gap-2">
                <StatusIcon className={cn('h-5 w-5', statusColor)} />
                <span className={cn('font-medium capitalize', statusColor)}>
                  {report.complianceStatus}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                KVKK 2026 Compliance Score
              </p>
            </div>
          </div>
          <Badge variant="outline" className="text-xs">
            Updated {format(new Date(report.reportGeneratedAt), 'MMM d, HH:mm')}
          </Badge>
        </div>
        <Progress value={report.complianceScore} className="mt-4 h-2" />
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<FileText className="h-5 w-5 text-blue-500" />}
          label="Total Documents"
          value={report.totalDocuments}
        />
        <MetricCard
          icon={<Folder className="h-5 w-5 text-amber-500" />}
          label="Scope Overrides"
          value={report.scopeOverrides}
          highlight={report.scopeOverrides > 0}
        />
        <MetricCard
          icon={<FileText className="h-5 w-5 text-green-500" />}
          label="Document Overrides"
          value={report.documentOverrides}
          highlight={report.documentOverrides > 0}
        />
        <MetricCard
          icon={<Building className="h-5 w-5 text-purple-500" />}
          label="Override Rate"
          value={`${overridePercentage}%`}
          highlight={overridePercentage > 25}
        />
      </div>

      {/* Compliance Checklist */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Info className="h-4 w-4" />
            Compliance Checklist
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <ChecklistItem
              label="Organization consent defaults set"
              checked={report.aiLearningConfigured && report.externalAgentsConfigured}
            />
            <ChecklistItem
              label="Scope-level consent management enabled"
              checked={report.scopeOverrides > 0}
            />
            <ChecklistItem
              label="Document-level granular controls available"
              checked={report.documentOverrides > 0}
            />
            <ChecklistItem
              label="Audit logging active"
              checked={true}
            />
            <ChecklistItem
              label="External agent access controlled"
              checked={report.externalAgentsConfigured}
            />
            <ChecklistItem
              label="Full KVKK 2026 compliance"
              checked={report.complianceScore >= 90}
            />
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      {report.complianceScore < 90 && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {report.complianceScore < 90 && (
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">•</span>
                  <span>Review and configure organization-level consent defaults</span>
                </li>
              )}
              {report.scopeOverrides > 5 && (
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">•</span>
                  <span>Consider consolidating scope overrides for easier management</span>
                </li>
              )}
              {overridePercentage > 25 && (
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">•</span>
                  <span>High override rate detected - review organization defaults</span>
                </li>
              )}
              <li className="flex items-start gap-2">
                <span className="text-amber-500 mt-0.5">•</span>
                <span>Regularly audit consent changes using the Audit Log tab</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  highlight?: boolean;
}

function MetricCard({ icon, label, value, highlight }: MetricCardProps) {
  return (
    <Card className={cn(highlight && 'border-amber-500/30')}>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center gap-3">
          {icon}
          <div>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-xs text-muted-foreground">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface ChecklistItemProps {
  label: string;
  checked: boolean;
}

function ChecklistItem({ label, checked }: ChecklistItemProps) {
  return (
    <div className="flex items-center gap-3">
      <div className={cn(
        'h-5 w-5 rounded-full flex items-center justify-center',
        checked ? 'bg-green-500/20' : 'bg-muted'
      )}>
        {checked && <CheckCircle2 className="h-3 w-3 text-green-500" />}
      </div>
      <span className={cn(
        'text-sm',
        checked ? 'text-foreground' : 'text-muted-foreground'
      )}>
        {label}
      </span>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ComplianceReportPanel({ variant = 'inline' }: ComplianceReportPanelProps) {
  const { complianceReport, refetch } = useConsent();
  const [isOpen, setIsOpen] = useState(false);

  const handleExport = () => {
    if (!complianceReport) return;

    const reportText = `
KVKK 2026 Compliance Report
===========================

Generated: ${format(new Date(complianceReport.reportGeneratedAt), 'PPpp')}
Organization: ${complianceReport.organizationId}

Compliance Score: ${complianceReport.complianceScore}%
Status: ${complianceReport.complianceStatus}

Metrics:
- Total Documents: ${complianceReport.totalDocuments}
- Scope Overrides: ${complianceReport.scopeOverrides}
- Document Overrides: ${complianceReport.documentOverrides}

This report was generated by Axiohub's Consent Management System.
    `.trim();

    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `compliance-report-${format(new Date(), 'yyyy-MM-dd')}.txt`;
    link.click();
  };

  if (variant === 'modal') {
    return (
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            <Shield className="h-4 w-4" />
            View Full Report
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-cyan-400" />
              Compliance Report
            </DialogTitle>
            <DialogDescription>
              GDPR/CCPA/KVKK 2026 compliance status and recommendations
            </DialogDescription>
          </DialogHeader>
          <ReportContent report={complianceReport} onRefetch={refetch} />
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4 mr-2" />
              Export Report
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Inline variant
  return (
    <Card className="border-cyan-500/20">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10">
              <Shield className="h-5 w-5 text-cyan-400" />
            </div>
            <div>
              <CardTitle className="text-lg">Compliance Report</CardTitle>
              <CardDescription>GDPR/CCPA/KVKK 2026 Status</CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ReportContent report={complianceReport} onRefetch={refetch} />
      </CardContent>
    </Card>
  );
}

export default ComplianceReportPanel;
