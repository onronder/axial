# Axiohub 2026 Ghost OS UX/UI Implementation Guide
## Frontend Development Specification

**Document Version:** 1.0
**Date:** 2026-02-03
**Scope:** Frontend UI components to visualize Ghost OS backend features
**Tech Stack:** Next.js 16 + React 19 + shadcn/ui + Tailwind CSS v4 + Framer Motion
**Design Philosophy:** "Hacker Noir meets Enterprise Clean" - Dramatic & High-Tech

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Ghost Protocol: Visual Destruction Experience](#3-ghost-protocol-visual-destruction-experience)
4. [Scope Guard: HITL Modals](#4-scope-guard-hitl-modals)
5. [Visual Ghost: Vision LLM UI](#5-visual-ghost-vision-llm-ui)
6. [KVKK Consent Panel](#6-kvkk-consent-panel)
7. [API Hooks Implementation](#7-api-hooks-implementation)
8. [Design System Extensions](#8-design-system-extensions)
9. [Integration Points](#9-integration-points)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. Executive Summary

### 1.1 Objective

Transform the Ghost OS backend features into visible, trustworthy UI experiences that make users "feel secure" and "hold the power" through visual proof of security operations.

### 1.2 Component Summary

| Category | Components | New Files | Est. Lines |
|----------|------------|-----------|------------|
| Ghost Protocol (Wipe UI) | 4 | 5 | ~600 |
| Scope Guard (HITL) | 4 | 5 | ~800 |
| Visual Ghost (Vision) | 4 | 5 | ~400 |
| KVKK Consent Panel | 5 | 6 | ~700 |
| API Hooks | 4 | 4 | ~300 |
| **Total** | **21** | **25** | **~2,800** |

### 1.3 User Perception Goals

| UI Component | Backend Connection | User Perception |
|--------------|-------------------|-----------------|
| Wipe Progress Card | DoD 5220.22-M | "This system really wipes the data, I'm safe." |
| Mandate Approval Modal | Scope Guard API | "I'm in control; the agent can't act without my permission." |
| Consent Toggles | KVKK 2026 Panel | "We are fully legally compliant; we won't get fined." |
| Vision Analysis Badge | Vision LLM Layer | "This isn't just a chatbot; it even reads my engineering documents." |

---

## 2. Architecture Overview

### 2.1 Frontend Tech Stack (Existing)

```
Framework:       Next.js 16.1.5 + React 19.2.1
UI Library:      shadcn/ui + Radix UI primitives
Styling:         Tailwind CSS v4 + CSS Variables
State:           Zustand 5.0.9 + React Query 5.90.12
Animations:      Framer Motion 12.23.26 + tailwindcss-animate
Backend:         Supabase SSR + Axios API client
Testing:         Vitest + Playwright
```

### 2.2 New File Structure

```
frontend-new/
├── components/
│   ├── ghost-protocol/           # NEW: Wipe visualization
│   │   ├── WipeProgressCard.tsx
│   │   ├── ShredderAnimation.tsx
│   │   ├── WipeVerificationBadge.tsx
│   │   ├── SecurityLogTable.tsx
│   │   └── index.ts
│   │
│   ├── scope-guard/              # NEW: HITL approval UI
│   │   ├── MandateApprovalModal.tsx
│   │   ├── SignatureAnimation.tsx
│   │   ├── IntentExplanationCard.tsx
│   │   ├── PendingApprovalsWidget.tsx
│   │   └── index.ts
│   │
│   ├── vision/                   # NEW: Vision LLM UI
│   │   ├── VisionVerifiedBadge.tsx
│   │   ├── DiagramPreviewModal.tsx
│   │   ├── SemanticOverlay.tsx
│   │   ├── SmartLink.tsx
│   │   └── index.ts
│   │
│   └── consent/                  # NEW: KVKK consent UI
│       ├── ConsentDashboard.tsx
│       ├── InheritanceTree.tsx
│       ├── AgentAccessPanel.tsx
│       ├── ComplianceScoreWidget.tsx
│       ├── ConsentToggle.tsx
│       └── index.ts
│
├── hooks/                        # NEW: API integration hooks
│   ├── useApprovals.ts
│   ├── useConsent.ts
│   ├── useSecurityLog.ts
│   └── useWipeProgress.ts
│
└── app/dashboard/settings/       # NEW: Settings pages
    ├── security-log/
    │   └── page.tsx
    └── consent/
        └── page.tsx
```

### 2.3 Backend API Endpoints (Already Implemented)

| Feature | Endpoint | Method | Purpose |
|---------|----------|--------|---------|
| Approvals | `/api/v1/approvals/pending` | GET | List pending approvals |
| Approvals | `/api/v1/approvals/{id}/approve` | POST | Approve action |
| Approvals | `/api/v1/approvals/{id}/reject` | POST | Reject action |
| Approvals | `/api/v1/approvals/{id}/execute` | POST | Execute approved action |
| Consent | `/api/v1/consent/organization` | GET/PATCH | Org consent settings |
| Consent | `/api/v1/consent/scope/{id}` | GET/PATCH | Scope consent |
| Consent | `/api/v1/consent/document/{id}` | GET/PATCH | Document consent |
| Consent | `/api/v1/consent/audit` | GET | Consent change log |
| Consent | `/api/v1/consent/report` | GET | Compliance report |

---

## 3. Ghost Protocol: Visual Destruction Experience

### 3.1 WipeProgressCard Component

**File:** `frontend-new/components/ghost-protocol/WipeProgressCard.tsx`

**Purpose:** Show real-time DoD 5220.22-M 3-pass wipe progress during file deletion

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  🔐 SECURE DELETION IN PROGRESS                             │
│                                                             │
│  Document: quarterly-report-2025.pdf                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Pass 1: Zero Fill (0x00)                                ││
│  │ ████████████████████████████████████████░░░░░░ 85%      ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Pass 2: One Fill (0xFF)              ⏳ Pending          ││
│  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ --       ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Pass 3: Random Data                   ⏳ Pending         ││
│  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ --       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ⏱️ Estimated: 3 seconds remaining                          │
│                                                             │
│  DoD 5220.22-M Compliant                                    │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
// frontend-new/components/ghost-protocol/WipeProgressCard.tsx

'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Clock, CheckCircle2, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface WipePass {
  name: string;
  description: string;
  status: 'pending' | 'active' | 'completed';
  progress: number;
  color: string;
  glowColor: string;
}

interface WipeProgressCardProps {
  documentName: string;
  currentPass: 1 | 2 | 3;
  passProgress: number;
  isComplete: boolean;
  onComplete?: () => void;
  className?: string;
}

const WIPE_PASSES: WipePass[] = [
  {
    name: 'Pass 1: Zero Fill',
    description: '0x00 - Writing zeros to entire file',
    status: 'pending',
    progress: 0,
    color: 'from-cyan-500 to-cyan-400',
    glowColor: 'shadow-cyan-500/50',
  },
  {
    name: 'Pass 2: One Fill',
    description: '0xFF - Writing ones to entire file',
    status: 'pending',
    progress: 0,
    color: 'from-orange-500 to-amber-400',
    glowColor: 'shadow-orange-500/50',
  },
  {
    name: 'Pass 3: Random Data',
    description: 'Cryptographically random bytes',
    status: 'pending',
    progress: 0,
    color: 'from-green-500 to-emerald-400',
    glowColor: 'shadow-green-500/50',
  },
];

export function WipeProgressCard({
  documentName,
  currentPass,
  passProgress,
  isComplete,
  onComplete,
  className,
}: WipeProgressCardProps) {
  const [passes, setPasses] = useState<WipePass[]>(WIPE_PASSES);

  useEffect(() => {
    setPasses(prev =>
      prev.map((pass, index) => {
        const passNum = index + 1;
        if (passNum < currentPass) {
          return { ...pass, status: 'completed', progress: 100 };
        } else if (passNum === currentPass) {
          return { ...pass, status: 'active', progress: passProgress };
        }
        return { ...pass, status: 'pending', progress: 0 };
      })
    );
  }, [currentPass, passProgress]);

  useEffect(() => {
    if (isComplete && onComplete) {
      const timer = setTimeout(onComplete, 1500);
      return () => clearTimeout(timer);
    }
  }, [isComplete, onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn('w-full max-w-md', className)}
    >
      <Card className="border-2 border-cyan-500/30 bg-black/80 backdrop-blur-xl">
        {/* Animated border glow */}
        <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-cyan-500/20 via-transparent to-green-500/20 animate-pulse" />

        <CardHeader className="relative pb-2">
          <CardTitle className="flex items-center gap-2 text-cyan-400">
            <Shield className="h-5 w-5 animate-pulse" />
            <span className="font-mono text-sm tracking-wider">
              SECURE DELETION IN PROGRESS
            </span>
          </CardTitle>
          <p className="text-sm text-muted-foreground truncate font-mono">
            {documentName}
          </p>
        </CardHeader>

        <CardContent className="relative space-y-4">
          {passes.map((pass, index) => (
            <WipePassProgress
              key={index}
              pass={pass}
              isActive={pass.status === 'active'}
            />
          ))}

          {/* Estimated time */}
          {!isComplete && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>Estimated: {Math.ceil((3 - currentPass + 1) * (100 - passProgress) / 100)} seconds remaining</span>
            </div>
          )}

          {/* Completion state */}
          <AnimatePresence>
            {isComplete && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-green-400 font-mono text-sm"
              >
                <CheckCircle2 className="h-5 w-5" />
                <span>DoD 5220.22-M Compliant - Forensic Wipe Complete</span>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function WipePassProgress({ pass, isActive }: { pass: WipePass; isActive: boolean }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className={cn(
          'font-mono',
          pass.status === 'completed' && 'text-green-400',
          pass.status === 'active' && 'text-cyan-400',
          pass.status === 'pending' && 'text-muted-foreground'
        )}>
          {pass.name}
        </span>
        <span className="text-muted-foreground">
          {pass.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-400" />}
          {pass.status === 'active' && <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />}
          {pass.status === 'pending' && '⏳ Pending'}
        </span>
      </div>

      <div className="relative h-2 overflow-hidden rounded-full bg-black/50">
        {/* Background pattern for active pass */}
        {isActive && (
          <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_25%,rgba(6,182,212,0.1)_50%,transparent_75%)] animate-[shimmer_1s_linear_infinite] bg-[length:200%_100%]" />
        )}

        <motion.div
          className={cn(
            'h-full rounded-full bg-gradient-to-r',
            pass.color,
            isActive && `shadow-lg ${pass.glowColor}`
          )}
          initial={{ width: 0 }}
          animate={{ width: `${pass.progress}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        />
      </div>

      <p className="text-[10px] text-muted-foreground font-mono">
        {pass.description}
      </p>
    </div>
  );
}

export default WipeProgressCard;
```

### 3.2 ShredderAnimation Component

**File:** `frontend-new/components/ghost-protocol/ShredderAnimation.tsx`

**Purpose:** Visual "paper shredder" effect showing document being destroyed

**Implementation:**

```typescript
// frontend-new/components/ghost-protocol/ShredderAnimation.tsx

'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText } from 'lucide-react';

interface ShredderAnimationProps {
  documentName: string;
  documentId: string;
  onComplete: () => void;
}

export function ShredderAnimation({
  documentName,
  documentId,
  onComplete,
}: ShredderAnimationProps) {
  const [phase, setPhase] = useState<'document' | 'shredding' | 'ghost'>('document');
  const stripCount = 12;

  useEffect(() => {
    const timer1 = setTimeout(() => setPhase('shredding'), 500);
    const timer2 = setTimeout(() => setPhase('ghost'), 2000);
    const timer3 = setTimeout(onComplete, 3500);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [onComplete]);

  return (
    <div className="relative w-64 h-80 flex items-center justify-center">
      <AnimatePresence mode="wait">
        {/* Phase 1: Document */}
        {phase === 'document' && (
          <motion.div
            key="document"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center"
          >
            <div className="relative">
              <div className="w-32 h-40 bg-white/10 rounded-lg border border-white/20 flex flex-col items-center justify-center gap-2 backdrop-blur-sm">
                <FileText className="h-12 w-12 text-cyan-400" />
                <span className="text-xs text-muted-foreground px-2 text-center truncate w-full">
                  {documentName}
                </span>
              </div>

              {/* Glow effect */}
              <div className="absolute inset-0 bg-cyan-500/20 rounded-lg blur-xl animate-pulse" />
            </div>
          </motion.div>
        )}

        {/* Phase 2: Shredding */}
        {phase === 'shredding' && (
          <motion.div
            key="shredding"
            className="absolute inset-0 flex items-center justify-center"
          >
            <div className="relative w-32 h-40 overflow-hidden">
              {Array.from({ length: stripCount }).map((_, i) => (
                <motion.div
                  key={i}
                  initial={{ y: 0, opacity: 1, rotateZ: 0 }}
                  animate={{
                    y: [0, 20, 200],
                    opacity: [1, 1, 0],
                    rotateZ: [0, (i % 2 ? 5 : -5), (i % 2 ? 15 : -15)],
                    x: [0, (i - stripCount / 2) * 2, (i - stripCount / 2) * 8],
                  }}
                  transition={{
                    duration: 1.5,
                    delay: i * 0.05,
                    ease: 'easeIn',
                  }}
                  className="absolute bg-gradient-to-b from-white/20 to-white/5 border-x border-white/10"
                  style={{
                    left: `${(i / stripCount) * 100}%`,
                    width: `${100 / stripCount}%`,
                    height: '100%',
                  }}
                />
              ))}
            </div>

            {/* Shredder visualization */}
            <div className="absolute bottom-0 w-40 h-8 bg-zinc-800 rounded-t-lg border-t-2 border-red-500/50 flex items-center justify-center">
              <div className="flex gap-0.5">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div
                    key={i}
                    className="w-0.5 h-4 bg-zinc-600 animate-pulse"
                    style={{ animationDelay: `${i * 50}ms` }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Phase 3: Ghost (Vector ID remains) */}
        {phase === 'ghost' && (
          <motion.div
            key="ghost"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-4"
          >
            {/* Ghost outline */}
            <div className="relative">
              <div className="w-32 h-40 border-2 border-dashed border-cyan-500/30 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <div className="text-cyan-500/50 text-xs font-mono mb-2">
                    SECURELY WIPED
                  </div>
                  <div className="text-[10px] text-muted-foreground font-mono">
                    ID: {documentId.slice(0, 8)}...
                  </div>
                </div>
              </div>

              {/* Fading ghost effect */}
              <motion.div
                initial={{ opacity: 0.3 }}
                animate={{ opacity: 0 }}
                transition={{ duration: 2 }}
                className="absolute inset-0 bg-gradient-to-b from-cyan-500/10 to-transparent rounded-lg"
              />
            </div>

            {/* Success badge */}
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="flex items-center gap-2 text-green-400 text-sm font-mono"
            >
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              DoD 5220.22-M Verified
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ShredderAnimation;
```

### 3.3 WipeVerificationBadge Component

**File:** `frontend-new/components/ghost-protocol/WipeVerificationBadge.tsx`

**Purpose:** Display DoD compliance status badge with timestamp tooltip

**Implementation:**

```typescript
// frontend-new/components/ghost-protocol/WipeVerificationBadge.tsx

'use client';

import { CheckCircle2, Info, Shield } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';

interface WipeVerificationBadgeProps {
  wipedAt: string;
  pattern: 'dod_5220_22_m' | 'random';
  verified: boolean;
  variant?: 'default' | 'compact' | 'inline';
  className?: string;
}

export function WipeVerificationBadge({
  wipedAt,
  pattern,
  verified,
  variant = 'default',
  className,
}: WipeVerificationBadgeProps) {
  const formattedDate = format(new Date(wipedAt), 'yyyy-MM-dd HH:mm:ss.SSS');
  const patternLabel = pattern === 'dod_5220_22_m' ? 'DoD 5220.22-M' : 'Random';

  if (variant === 'compact') {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('inline-flex items-center gap-1', className)}>
            <Shield className="h-3 w-3 text-green-400" />
            <span className="text-[10px] text-green-400 font-mono">FW</span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top" className="font-mono text-xs">
          <p>Forensic Wiped ({patternLabel})</p>
          <p className="text-muted-foreground">{formattedDate}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  if (variant === 'inline') {
    return (
      <span className={cn(
        'inline-flex items-center gap-1 text-xs text-green-400',
        className
      )}>
        <CheckCircle2 className="h-3 w-3" />
        <span className="font-mono">Wiped</span>
      </span>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={cn(
            'gap-1.5 border-green-500/30 bg-green-500/10 text-green-400',
            'hover:bg-green-500/20 hover:border-green-500/50',
            'transition-all duration-200 cursor-help',
            className
          )}
        >
          {verified ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <Shield className="h-3 w-3" />
          )}
          <span className="font-mono text-[10px]">
            Forensic Wiped
          </span>
          <Info className="h-3 w-3 opacity-50" />
        </Badge>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="max-w-xs bg-black/95 border-green-500/30"
      >
        <div className="space-y-2 font-mono text-xs">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-400" />
            <span className="font-semibold text-green-400">
              {patternLabel} Compliant
            </span>
          </div>

          <div className="space-y-1 text-muted-foreground">
            <p>3-pass secure wipe completed:</p>
            <ul className="list-disc list-inside text-[10px] space-y-0.5">
              <li>Pass 1: Zero fill (0x00)</li>
              <li>Pass 2: One fill (0xFF)</li>
              <li>Pass 3: Random data</li>
            </ul>
          </div>

          <div className="pt-1 border-t border-green-500/20">
            <span className="text-muted-foreground">Wiped at: </span>
            <span className="text-green-400">{formattedDate}</span>
          </div>

          {verified && (
            <div className="flex items-center gap-1 text-green-400">
              <CheckCircle2 className="h-3 w-3" />
              <span>Post-wipe verification passed</span>
            </div>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

export default WipeVerificationBadge;
```

### 3.4 SecurityLogTable Component

**File:** `frontend-new/components/ghost-protocol/SecurityLogTable.tsx`

**Purpose:** Audit trail showing security events (what was wiped, when)

**Implementation:**

```typescript
// frontend-new/components/ghost-protocol/SecurityLogTable.tsx

'use client';

import { useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Shield,
  FileText,
  Folder,
  Database,
  Download,
  Search,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { WipeVerificationBadge } from './WipeVerificationBadge';
import { useSecurityLog } from '@/hooks/useSecurityLog';

interface SecurityEvent {
  id: string;
  event_type: 'document_wiped' | 'scope_deleted' | 'chunk_purged' | 'organization_purged';
  resource_type: string;
  resource_name: string;
  resource_id: string;
  wipe_pattern: 'dod_5220_22_m' | 'random';
  wipe_verified: boolean;
  performed_by: string;
  performed_at: string;
  duration_ms: number;
}

const EVENT_ICONS = {
  document_wiped: FileText,
  scope_deleted: Folder,
  chunk_purged: Database,
  organization_purged: Shield,
};

const EVENT_LABELS = {
  document_wiped: 'Document Wiped',
  scope_deleted: 'Scope Deleted',
  chunk_purged: 'Chunk Purged',
  organization_purged: 'Organization Purged',
};

export function SecurityLogTable() {
  const [search, setSearch] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');

  const { data: events, isLoading } = useSecurityLog({
    search,
    eventType: eventTypeFilter !== 'all' ? eventTypeFilter : undefined,
  });

  const handleExport = () => {
    // Export to CSV
    const csv = [
      ['Timestamp', 'Event Type', 'Resource', 'Pattern', 'Verified', 'Duration (ms)'],
      ...(events || []).map(e => [
        e.performed_at,
        e.event_type,
        e.resource_name,
        e.wipe_pattern,
        e.wipe_verified ? 'Yes' : 'No',
        e.duration_ms,
      ]),
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security-log-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-cyan-400" />
          <h2 className="text-lg font-semibold">Security Log</h2>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          className="gap-2"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by resource name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Event type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Events</SelectItem>
            <SelectItem value="document_wiped">Document Wiped</SelectItem>
            <SelectItem value="scope_deleted">Scope Deleted</SelectItem>
            <SelectItem value="chunk_purged">Chunk Purged</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border/50 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="w-48">Timestamp</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead className="text-center">Compliance</TableHead>
              <TableHead className="text-right">Duration</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8">
                  Loading security events...
                </TableCell>
              </TableRow>
            ) : events?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  No security events found
                </TableCell>
              </TableRow>
            ) : (
              events?.map((event) => {
                const Icon = EVENT_ICONS[event.event_type];
                return (
                  <TableRow key={event.id} className="hover:bg-muted/20">
                    <TableCell className="font-mono text-xs">
                      <div>{format(new Date(event.performed_at), 'HH:mm:ss.SSS')}</div>
                      <div className="text-muted-foreground">
                        {formatDistanceToNow(new Date(event.performed_at), { addSuffix: true })}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{EVENT_LABELS[event.event_type]}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-[200px]">
                        <div className="truncate text-sm">{event.resource_name}</div>
                        <div className="text-[10px] font-mono text-muted-foreground">
                          {event.resource_id.slice(0, 12)}...
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <WipeVerificationBadge
                        wipedAt={event.performed_at}
                        pattern={event.wipe_pattern}
                        verified={event.wipe_verified}
                        variant="compact"
                      />
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {event.duration_ms}ms
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default SecurityLogTable;
```

---

## 4. Scope Guard: HITL Modals

### 4.1 MandateApprovalModal Component

**File:** `frontend-new/components/scope-guard/MandateApprovalModal.tsx`

**Purpose:** Full-screen overlay that freezes UI when agent requests destructive action

**Implementation:**

```typescript
// frontend-new/components/scope-guard/MandateApprovalModal.tsx

'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  Clock,
  Shield,
  Bot,
  FileText,
  Folder,
  Trash2,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SignatureAnimation } from './SignatureAnimation';
import { IntentExplanationCard } from './IntentExplanationCard';
import { cn } from '@/lib/utils';

interface Approval {
  id: string;
  action_type: 'delete_scope' | 'bulk_delete' | 'purge_all' | 'revoke_access';
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  requested_by: string;
  requested_by_name?: string;
  expires_at: string;
  request_context: {
    reason?: string;
    affected_count?: number;
    affected_documents?: Array<{ id: string; name: string }>;
  };
}

interface MandateApprovalModalProps {
  approval: Approval;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
}

const ACTION_CONFIG = {
  delete_scope: {
    icon: Folder,
    label: 'Delete Scope',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/50',
  },
  bulk_delete: {
    icon: Trash2,
    label: 'Bulk Delete',
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/50',
  },
  purge_all: {
    icon: AlertTriangle,
    label: 'Purge All Data',
    color: 'text-red-500',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500',
  },
  revoke_access: {
    icon: Shield,
    label: 'Revoke Access',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/50',
  },
};

export function MandateApprovalModal({
  approval,
  onApprove,
  onReject,
  isOpen,
  onClose,
}: MandateApprovalModalProps) {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isSigning, setIsSigning] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const config = ACTION_CONFIG[approval.action_type];
  const ActionIcon = config.icon;

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;

    const updateTimer = () => {
      const now = new Date().getTime();
      const expires = new Date(approval.expires_at).getTime();
      const remaining = Math.max(0, Math.floor((expires - now) / 1000));
      setTimeRemaining(remaining);

      if (remaining === 0) {
        onClose();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [isOpen, approval.expires_at, onClose]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleApprove = useCallback(async () => {
    setIsSigning(true);
    try {
      await onApprove();
    } finally {
      setIsSigning(false);
    }
  }, [onApprove]);

  const handleReject = useCallback(async () => {
    setIsRejecting(true);
    try {
      await onReject();
    } finally {
      setIsRejecting(false);
    }
  }, [onReject]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
        >
          {/* Backdrop with blur */}
          <div className="absolute inset-0 bg-black/80 backdrop-blur-md" />

          {/* Animated border pulse */}
          <div className={cn(
            'absolute inset-4 rounded-2xl opacity-30',
            'bg-gradient-to-r from-orange-500 via-red-500 to-orange-500',
            'animate-pulse bg-[length:200%_100%]'
          )} />

          {/* Main content */}
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="relative w-full max-w-2xl mx-4"
          >
            <Card className={cn(
              'border-2 bg-black/95 backdrop-blur-xl',
              config.borderColor
            )}>
              <CardHeader className="relative pb-4">
                {/* Close button (only for non-critical) */}
                {approval.action_type !== 'purge_all' && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-4 top-4"
                    onClick={onClose}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}

                {/* Warning header */}
                <div className="flex items-center gap-3">
                  <div className={cn(
                    'p-3 rounded-full',
                    config.bgColor
                  )}>
                    <AlertTriangle className={cn('h-6 w-6', config.color)} />
                  </div>
                  <div>
                    <CardTitle className={cn('text-xl', config.color)}>
                      ACTION REQUIRES APPROVAL
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Mandate expires in:{' '}
                      <span className={cn(
                        'font-mono font-bold',
                        timeRemaining < 60 ? 'text-red-400' : 'text-amber-400'
                      )}>
                        {formatTime(timeRemaining)}
                      </span>
                    </p>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-6">
                {/* Action details */}
                <div className={cn(
                  'p-4 rounded-lg border',
                  config.bgColor,
                  config.borderColor
                )}>
                  <div className="flex items-start gap-3">
                    <Bot className="h-5 w-5 text-violet-400 mt-0.5" />
                    <div className="space-y-2 flex-1">
                      <p className="text-sm text-muted-foreground">
                        AI Agent wants to:
                      </p>
                      <div className="flex items-center gap-2">
                        <ActionIcon className={cn('h-5 w-5', config.color)} />
                        <span className={cn('font-semibold', config.color)}>
                          {config.label}
                        </span>
                      </div>
                      <p className="text-lg font-medium">
                        "{approval.resource_name || approval.resource_id}"
                      </p>
                      {approval.request_context.affected_count && (
                        <p className="text-sm text-muted-foreground">
                          This will permanently remove{' '}
                          <span className="font-semibold text-foreground">
                            {approval.request_context.affected_count}
                          </span>{' '}
                          documents.
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Intent explanation */}
                {approval.request_context.reason && (
                  <IntentExplanationCard
                    reason={approval.request_context.reason}
                    affectedDocuments={approval.request_context.affected_documents}
                  />
                )}

                {/* Signing animation overlay */}
                <AnimatePresence>
                  {isSigning && (
                    <SignatureAnimation />
                  )}
                </AnimatePresence>

                {/* Action buttons */}
                <div className="flex gap-4 pt-4">
                  <Button
                    variant="outline"
                    className="flex-1 h-12"
                    onClick={handleReject}
                    disabled={isSigning || isRejecting}
                  >
                    {isRejecting ? 'Rejecting...' : 'Reject'}
                  </Button>
                  <Button
                    className={cn(
                      'flex-1 h-12 gap-2',
                      'bg-gradient-to-r from-amber-500 to-orange-500',
                      'hover:from-amber-600 hover:to-orange-600',
                      'text-black font-semibold'
                    )}
                    onClick={handleApprove}
                    disabled={isSigning || isRejecting}
                  >
                    <Shield className="h-4 w-4" />
                    {isSigning ? 'Signing...' : 'Approve & Sign'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default MandateApprovalModal;
```

### 4.2 SignatureAnimation Component

**File:** `frontend-new/components/scope-guard/SignatureAnimation.tsx`

**Purpose:** Show "Signing with HMAC-SHA256..." animation during approval

**Implementation:**

```typescript
// frontend-new/components/scope-guard/SignatureAnimation.tsx

'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, CheckCircle2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface SignatureAnimationProps {
  onComplete?: () => void;
  duration?: number;
}

export function SignatureAnimation({
  onComplete,
  duration = 2000,
}: SignatureAnimationProps) {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<'signing' | 'complete'>('signing');
  const [hashChars, setHashChars] = useState('');

  // Matrix-style character animation
  useEffect(() => {
    const chars = '0123456789abcdef';
    const interval = setInterval(() => {
      const newChars = Array.from({ length: 64 }, () =>
        chars[Math.floor(Math.random() * chars.length)]
      ).join('');
      setHashChars(newChars);
    }, 50);

    return () => clearInterval(interval);
  }, []);

  // Progress animation
  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min((elapsed / duration) * 100, 100);
      setProgress(newProgress);

      if (newProgress >= 100) {
        clearInterval(interval);
        setPhase('complete');
        setTimeout(() => {
          onComplete?.();
        }, 500);
      }
    }, 16);

    return () => clearInterval(interval);
  }, [duration, onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center rounded-lg"
    >
      <div className="text-center space-y-4 p-8">
        {phase === 'signing' ? (
          <>
            <div className="flex items-center justify-center gap-2">
              <Shield className="h-6 w-6 text-cyan-400 animate-pulse" />
              <span className="text-cyan-400 font-mono text-sm">
                Cryptographic Signature
              </span>
            </div>

            {/* Progress bar with glow */}
            <div className="relative w-64">
              <Progress
                value={progress}
                className="h-2 bg-cyan-950"
              />
              <div
                className="absolute inset-0 bg-cyan-400/20 blur-md"
                style={{ width: `${progress}%` }}
              />
            </div>

            {/* Matrix-style hash display */}
            <div className="font-mono text-[10px] text-cyan-400/60 break-all max-w-xs">
              {hashChars}
            </div>

            <p className="text-sm text-muted-foreground">
              Signing with HMAC-SHA256...
            </p>
          </>
        ) : (
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="flex flex-col items-center gap-2"
          >
            <CheckCircle2 className="h-12 w-12 text-green-400" />
            <span className="text-green-400 font-semibold">
              Mandate Signed
            </span>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

export default SignatureAnimation;
```

### 4.3 IntentExplanationCard Component

**File:** `frontend-new/components/scope-guard/IntentExplanationCard.tsx`

**Purpose:** Show AI's reasoning for the requested action

**Implementation:**

```typescript
// frontend-new/components/scope-guard/IntentExplanationCard.tsx

'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface IntentExplanationCardProps {
  reason: string;
  affectedDocuments?: Array<{ id: string; name: string }>;
  className?: string;
}

export function IntentExplanationCard({
  reason,
  affectedDocuments,
  className,
}: IntentExplanationCardProps) {
  const [showDocuments, setShowDocuments] = useState(false);

  return (
    <div className={cn(
      'p-4 rounded-lg bg-violet-500/10 border border-violet-500/30',
      className
    )}>
      <div className="flex items-start gap-3">
        <Brain className="h-5 w-5 text-violet-400 mt-0.5" />
        <div className="space-y-3 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-violet-400">
              Agent's Reasoning
            </span>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed">
            "{reason}"
          </p>

          {/* Affected documents list */}
          {affectedDocuments && affectedDocuments.length > 0 && (
            <div className="space-y-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-violet-400 hover:text-violet-300"
                onClick={() => setShowDocuments(!showDocuments)}
              >
                <FileText className="h-4 w-4 mr-1" />
                <span className="text-xs">
                  {affectedDocuments.length} documents affected
                </span>
                {showDocuments ? (
                  <ChevronUp className="h-3 w-3 ml-1" />
                ) : (
                  <ChevronDown className="h-3 w-3 ml-1" />
                )}
              </Button>

              <AnimatePresence>
                {showDocuments && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <ul className="text-xs text-muted-foreground space-y-1 pl-4 border-l border-violet-500/30">
                      {affectedDocuments.slice(0, 5).map((doc) => (
                        <li key={doc.id} className="truncate">
                          • {doc.name}
                        </li>
                      ))}
                      {affectedDocuments.length > 5 && (
                        <li className="text-violet-400">
                          +{affectedDocuments.length - 5} more...
                        </li>
                      )}
                    </ul>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default IntentExplanationCard;
```

### 4.4 PendingApprovalsWidget Component

**File:** `frontend-new/components/scope-guard/PendingApprovalsWidget.tsx`

**Purpose:** Dashboard widget showing pending approval count for admins

**Implementation:**

```typescript
// frontend-new/components/scope-guard/PendingApprovalsWidget.tsx

'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Clock, AlertTriangle, ArrowRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useApprovals } from '@/hooks/useApprovals';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

export function PendingApprovalsWidget() {
  const router = useRouter();
  const { pending, isLoading } = useApprovals();
  const count = pending?.length || 0;

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardContent className="p-6">
          <div className="h-24 bg-muted/20 rounded" />
        </CardContent>
      </Card>
    );
  }

  if (count === 0) {
    return null; // Don't show widget if no pending approvals
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card className={cn(
        'border-2 overflow-hidden',
        count > 0 ? 'border-orange-500/50 bg-orange-500/5' : 'border-border'
      )}>
        {/* Pulsing top border */}
        <div className="h-1 bg-gradient-to-r from-orange-500 via-amber-500 to-orange-500 animate-pulse" />

        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="p-3 rounded-full bg-orange-500/10">
                  <Clock className="h-6 w-6 text-orange-400" />
                </div>
                {/* Notification dot */}
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-[10px] font-bold text-white">
                    {count > 9 ? '9+' : count}
                  </span>
                </span>
              </div>

              <div>
                <h3 className="font-semibold text-orange-400">
                  Pending Approvals
                </h3>
                <p className="text-sm text-muted-foreground">
                  {count} action{count !== 1 ? 's' : ''} awaiting your approval
                </p>
              </div>
            </div>

            <Button
              variant="outline"
              className="gap-2 border-orange-500/30 hover:bg-orange-500/10"
              onClick={() => router.push('/dashboard/settings/approvals')}
            >
              Review Now
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>

          {/* Urgent item preview */}
          {pending && pending[0] && (
            <div className="mt-4 p-3 rounded-lg bg-black/20 flex items-center gap-3">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span className="text-sm truncate flex-1">
                {pending[0].resource_name || pending[0].resource_id}
              </span>
              <Badge variant="outline" className="text-amber-400 border-amber-500/30">
                {pending[0].action_type.replace('_', ' ')}
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default PendingApprovalsWidget;
```

---

## 5. Visual Ghost: Vision LLM UI

### 5.1 VisionVerifiedBadge Component

**File:** `frontend-new/components/vision/VisionVerifiedBadge.tsx`

**Purpose:** Eye icon indicating the source is a visual/diagram analyzed by Vision LLM

**Implementation:**

```typescript
// frontend-new/components/vision/VisionVerifiedBadge.tsx

'use client';

import { Eye, Image as ImageIcon } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface VisionVerifiedBadgeProps {
  diagramType: 'flowchart' | 'architecture' | 'chart' | 'schematic' | 'er_diagram' | 'uml' | 'unknown';
  confidence: number;
  modelUsed: string;
  onClick?: () => void;
  className?: string;
}

const DIAGRAM_LABELS: Record<string, string> = {
  flowchart: 'Flowchart',
  architecture: 'Architecture Diagram',
  chart: 'Chart/Graph',
  schematic: 'Technical Schematic',
  er_diagram: 'ER Diagram',
  uml: 'UML Diagram',
  unknown: 'Visual',
};

export function VisionVerifiedBadge({
  diagramType,
  confidence,
  modelUsed,
  onClick,
  className,
}: VisionVerifiedBadgeProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={cn(
            'gap-1.5 cursor-pointer',
            'border-violet-500/30 bg-violet-500/10 text-violet-400',
            'hover:bg-violet-500/20 hover:border-violet-500/50',
            'transition-all duration-200',
            className
          )}
          onClick={onClick}
        >
          <Eye className="h-3 w-3" />
          <span className="text-[10px] font-mono">
            Vision Verified
          </span>
        </Badge>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="max-w-xs bg-black/95 border-violet-500/30"
      >
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4 text-violet-400" />
            <span className="font-semibold text-violet-400">
              {DIAGRAM_LABELS[diagramType]}
            </span>
          </div>

          <div className="space-y-1 text-muted-foreground">
            <p>This source contains visual content that was</p>
            <p>semantically analyzed by AI vision model.</p>
          </div>

          <div className="flex items-center justify-between pt-1 border-t border-violet-500/20 text-[10px]">
            <span className="text-muted-foreground">
              Model: <span className="text-violet-400">{modelUsed}</span>
            </span>
            <span className="text-muted-foreground">
              Confidence: <span className="text-violet-400">{Math.round(confidence * 100)}%</span>
            </span>
          </div>

          <p className="text-[10px] text-violet-400/60">
            Click to view semantic description
          </p>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

export default VisionVerifiedBadge;
```

### 5.2 DiagramPreviewModal Component

**File:** `frontend-new/components/vision/DiagramPreviewModal.tsx`

**Purpose:** Modal showing semantic description of the analyzed visual

**Implementation:**

```typescript
// frontend-new/components/vision/DiagramPreviewModal.tsx

'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Eye,
  Image as ImageIcon,
  Shield,
  CheckCircle2,
  Brain,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface DiagramPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentTitle: string;
  diagramType: string;
  description: string;
  entities: string[];
  relationships: string[];
  confidence: number;
  modelUsed: string;
}

export function DiagramPreviewModal({
  isOpen,
  onClose,
  documentTitle,
  diagramType,
  description,
  entities,
  relationships,
  confidence,
  modelUsed,
}: DiagramPreviewModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-black/95 border-violet-500/30">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-violet-400">
            <Eye className="h-5 w-5" />
            Vision Analysis: {documentTitle}
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-[1fr,1.5fr] gap-6">
          {/* Left: Placeholder / Info */}
          <div className="space-y-4">
            {/* Image placeholder */}
            <div className="aspect-[4/5] rounded-lg border border-dashed border-violet-500/30 bg-violet-500/5 flex flex-col items-center justify-center gap-3">
              <ImageIcon className="h-12 w-12 text-violet-500/30" />
              <p className="text-xs text-center text-muted-foreground px-4">
                Original image securely wiped after processing
              </p>
              <Badge variant="outline" className="text-green-400 border-green-500/30">
                <Shield className="h-3 w-3 mr-1" />
                Ghost Protocol
              </Badge>
            </div>

            {/* Metadata */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Diagram Type</span>
                <Badge variant="secondary" className="capitalize">
                  {diagramType.replace('_', ' ')}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Confidence</span>
                <span className="text-violet-400 font-mono">
                  {Math.round(confidence * 100)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Analyzed by</span>
                <span className="text-violet-400">{modelUsed}</span>
              </div>
            </div>
          </div>

          {/* Right: Semantic Description */}
          <div className="space-y-4">
            {/* Description */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <Brain className="h-4 w-4 text-violet-400" />
                Semantic Description
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {description}
              </p>
            </div>

            <Separator className="bg-violet-500/20" />

            {/* Entities */}
            {entities.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Identified Entities</h4>
                <div className="flex flex-wrap gap-2">
                  {entities.map((entity, i) => (
                    <Badge
                      key={i}
                      variant="outline"
                      className="bg-violet-500/10 border-violet-500/30"
                    >
                      {entity}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Relationships */}
            {relationships.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Relationships</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {relationships.map((rel, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-violet-400">→</span>
                      {rel}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default DiagramPreviewModal;
```

---

## 6. KVKK Consent Panel

### 6.1 ConsentDashboard Component

**File:** `frontend-new/components/consent/ConsentDashboard.tsx`

**Purpose:** Main consent management page with org/scope/document controls

**Implementation:**

```typescript
// frontend-new/components/consent/ConsentDashboard.tsx

'use client';

import { useState } from 'react';
import { Shield, Building, Folder, FileText, Settings } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ConsentToggle } from './ConsentToggle';
import { InheritanceTree } from './InheritanceTree';
import { AgentAccessPanel } from './AgentAccessPanel';
import { ComplianceScoreWidget } from './ComplianceScoreWidget';
import { useConsent } from '@/hooks/useConsent';

export function ConsentDashboard() {
  const {
    orgConsent,
    scopeConsents,
    documentConsents,
    updateOrgConsent,
    updateScopeConsent,
    complianceReport,
    isLoading,
  } = useConsent();

  if (isLoading) {
    return <ConsentDashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10">
            <Shield className="h-6 w-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Data Consent Management</h1>
            <p className="text-sm text-muted-foreground">
              KVKK 2026 Compliant Granular Controls
            </p>
          </div>
        </div>
        <ComplianceScoreWidget score={complianceReport?.complianceScore || 0} />
      </div>

      {/* Organization Defaults */}
      <Card className="border-cyan-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Building className="h-5 w-5 text-cyan-400" />
            Organization Defaults
          </CardTitle>
          <CardDescription>
            These settings apply to all data unless overridden at scope or document level
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-6">
            <ConsentToggle
              label="AI Learning"
              description="Allow data to be used for AI model improvement"
              enabled={orgConsent?.allowAiLearning || false}
              onChange={(enabled) => updateOrgConsent('ai_learning', enabled)}
              consentedAt={orgConsent?.aiLearningConsentAt}
            />
            <ConsentToggle
              label="External Agents"
              description="Allow external AI agents (MCP) to access data"
              enabled={orgConsent?.allowExternalAgents || false}
              onChange={(enabled) => updateOrgConsent('external_agents', enabled)}
              consentedAt={orgConsent?.externalAgentsConsentAt}
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabs for Scopes, Documents, Agents */}
      <Tabs defaultValue="inheritance" className="space-y-4">
        <TabsList className="grid grid-cols-3 w-full max-w-md">
          <TabsTrigger value="inheritance" className="gap-2">
            <Folder className="h-4 w-4" />
            Inheritance
          </TabsTrigger>
          <TabsTrigger value="agents" className="gap-2">
            <Settings className="h-4 w-4" />
            Agents
          </TabsTrigger>
          <TabsTrigger value="documents" className="gap-2">
            <FileText className="h-4 w-4" />
            Overrides
          </TabsTrigger>
        </TabsList>

        <TabsContent value="inheritance">
          <InheritanceTree
            orgConsent={orgConsent}
            scopeConsents={scopeConsents}
            documentConsents={documentConsents}
          />
        </TabsContent>

        <TabsContent value="agents">
          <AgentAccessPanel />
        </TabsContent>

        <TabsContent value="documents">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Document-Level Overrides</CardTitle>
              <CardDescription>
                {documentConsents?.length || 0} documents with custom consent settings
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Document override list */}
              {documentConsents?.map((doc) => (
                <div key={doc.documentId} className="py-3 border-b last:border-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{doc.documentId}</span>
                    <div className="flex gap-2">
                      <ConsentToggle
                        label="AI"
                        enabled={doc.allowAiLearning ?? false}
                        onChange={() => {}}
                        compact
                      />
                      <ConsentToggle
                        label="Agents"
                        enabled={doc.allowExternalAgents ?? false}
                        onChange={() => {}}
                        compact
                      />
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ConsentDashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-20 bg-muted/20 rounded-lg" />
      <div className="h-48 bg-muted/20 rounded-lg" />
      <div className="h-64 bg-muted/20 rounded-lg" />
    </div>
  );
}

export default ConsentDashboard;
```

### 6.2 ConsentToggle Component

**File:** `frontend-new/components/consent/ConsentToggle.tsx`

**Implementation:**

```typescript
// frontend-new/components/consent/ConsentToggle.tsx

'use client';

import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
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
        <span className={cn(
          'text-xs',
          enabled ? 'text-green-400' : 'text-muted-foreground'
        )}>
          {label}
        </span>
      </div>
    );
  }

  return (
    <div className={cn(
      'p-4 rounded-lg border transition-colors',
      enabled
        ? 'border-green-500/30 bg-green-500/5'
        : 'border-border bg-muted/5'
    )}>
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Label className="text-sm font-medium">{label}</Label>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
          {consentedAt && enabled && (
            <p className="text-[10px] text-green-400/60">
              Consented: {format(new Date(consentedAt), 'MMM d, yyyy HH:mm')}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={cn(
              'text-[10px]',
              enabled
                ? 'border-green-500/30 text-green-400'
                : 'border-red-500/30 text-red-400'
            )}
          >
            {enabled ? 'ALLOWED' : 'DENIED'}
          </Badge>
          <Switch
            checked={enabled}
            onCheckedChange={onChange}
            disabled={disabled}
          />
        </div>
      </div>
    </div>
  );
}

export default ConsentToggle;
```

### 6.3 ComplianceScoreWidget Component

**File:** `frontend-new/components/consent/ComplianceScoreWidget.tsx`

**Implementation:**

```typescript
// frontend-new/components/consent/ComplianceScoreWidget.tsx

'use client';

import { Shield, ArrowRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface ComplianceScoreWidgetProps {
  score: number; // 0-100
  onViewReport?: () => void;
  variant?: 'card' | 'inline';
}

export function ComplianceScoreWidget({
  score,
  onViewReport,
  variant = 'card',
}: ComplianceScoreWidgetProps) {
  const getScoreColor = (s: number) => {
    if (s >= 80) return 'text-green-400';
    if (s >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  const getScoreLabel = (s: number) => {
    if (s >= 80) return 'Compliant';
    if (s >= 60) return 'Partial';
    return 'Non-Compliant';
  };

  if (variant === 'inline') {
    return (
      <div className="flex items-center gap-3">
        <Shield className={cn('h-5 w-5', getScoreColor(score))} />
        <div className="text-right">
          <span className={cn('text-2xl font-bold', getScoreColor(score))}>
            {score}%
          </span>
          <p className="text-xs text-muted-foreground">{getScoreLabel(score)}</p>
        </div>
      </div>
    );
  }

  return (
    <Card className="w-64 border-cyan-500/20">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-cyan-400" />
            <span className="text-sm font-medium">Data Sovereignty</span>
          </div>
        </div>

        <div className="text-center mb-3">
          <span className={cn('text-4xl font-bold', getScoreColor(score))}>
            {score}%
          </span>
        </div>

        <Progress
          value={score}
          className="h-2 mb-3"
        />

        <p className={cn(
          'text-center text-sm font-medium mb-3',
          getScoreColor(score)
        )}>
          KVKK 2026 {getScoreLabel(score)}
        </p>

        {onViewReport && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full gap-2"
            onClick={onViewReport}
          >
            View Report
            <ArrowRight className="h-3 w-3" />
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export default ComplianceScoreWidget;
```

---

## 7. API Hooks Implementation

### 7.1 useApprovals Hook

**File:** `frontend-new/hooks/useApprovals.ts`

```typescript
// frontend-new/hooks/useApprovals.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Approval {
  id: string;
  action_type: 'delete_scope' | 'bulk_delete' | 'purge_all' | 'revoke_access';
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'executed';
  requested_by: string;
  approved_by?: string;
  requested_at: string;
  expires_at: string;
  request_context: Record<string, unknown>;
}

const APPROVALS_KEY = ['approvals'];

export function useApprovals() {
  const queryClient = useQueryClient();

  // Fetch pending approvals
  const {
    data: pending,
    isLoading,
    error,
  } = useQuery({
    queryKey: [...APPROVALS_KEY, 'pending'],
    queryFn: async () => {
      const response = await api.get<Approval[]>('/api/py/approvals/pending');
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Approve action
  const approveMutation = useMutation({
    mutationFn: async (approvalId: string) => {
      const response = await api.post(`/api/py/approvals/${approvalId}/approve`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPROVALS_KEY });
    },
  });

  // Reject action
  const rejectMutation = useMutation({
    mutationFn: async (approvalId: string) => {
      const response = await api.post(`/api/py/approvals/${approvalId}/reject`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPROVALS_KEY });
    },
  });

  // Execute approved action
  const executeMutation = useMutation({
    mutationFn: async ({
      approvalId,
      mandateSignature,
    }: {
      approvalId: string;
      mandateSignature: string;
    }) => {
      const response = await api.post(`/api/py/approvals/${approvalId}/execute`, {
        mandate_signature: mandateSignature,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPROVALS_KEY });
    },
  });

  return {
    pending,
    isLoading,
    error,
    approve: approveMutation.mutateAsync,
    reject: rejectMutation.mutateAsync,
    execute: executeMutation.mutateAsync,
    isApproving: approveMutation.isPending,
    isRejecting: rejectMutation.isPending,
    isExecuting: executeMutation.isPending,
  };
}

export default useApprovals;
```

### 7.2 useConsent Hook

**File:** `frontend-new/hooks/useConsent.ts`

```typescript
// frontend-new/hooks/useConsent.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface OrgConsent {
  organizationId: string;
  allowAiLearning: boolean;
  aiLearningConsentAt?: string;
  allowExternalAgents: boolean;
  externalAgentsConsentAt?: string;
}

interface ScopeConsent {
  scopeId: string;
  organizationId: string;
  inheritOrgConsent: boolean;
  allowAiLearning?: boolean;
  allowExternalAgents?: boolean;
  allowedAgentIds: string[];
  blockedAgentIds: string[];
}

interface DocumentConsent {
  documentId: string;
  organizationId: string;
  inheritScopeConsent: boolean;
  allowAiLearning?: boolean;
  allowExternalAgents?: boolean;
}

interface ComplianceReport {
  organizationId: string;
  reportGeneratedAt: string;
  organizationConsent: OrgConsent;
  scopeOverrides: number;
  documentOverrides: number;
  totalDocuments: number;
  complianceStatus: string;
  complianceScore: number;
}

const CONSENT_KEY = ['consent'];

export function useConsent() {
  const queryClient = useQueryClient();

  // Organization consent
  const { data: orgConsent, isLoading: isLoadingOrg } = useQuery({
    queryKey: [...CONSENT_KEY, 'organization'],
    queryFn: async () => {
      const response = await api.get<OrgConsent>('/api/py/consent/organization');
      return {
        ...response.data,
        allowAiLearning: response.data.allow_ai_learning,
        aiLearningConsentAt: response.data.ai_learning_consent_at,
        allowExternalAgents: response.data.allow_external_agents,
        externalAgentsConsentAt: response.data.external_agents_consent_at,
      };
    },
  });

  // Scope consents
  const { data: scopeConsents } = useQuery({
    queryKey: [...CONSENT_KEY, 'scopes'],
    queryFn: async () => {
      // This would need a list endpoint - for now return empty
      return [] as ScopeConsent[];
    },
  });

  // Document consents
  const { data: documentConsents } = useQuery({
    queryKey: [...CONSENT_KEY, 'documents'],
    queryFn: async () => {
      return [] as DocumentConsent[];
    },
  });

  // Compliance report
  const { data: complianceReport } = useQuery({
    queryKey: [...CONSENT_KEY, 'report'],
    queryFn: async () => {
      const response = await api.get<ComplianceReport>('/api/py/consent/report');
      return {
        ...response.data,
        complianceScore: calculateComplianceScore(response.data),
      };
    },
  });

  // Update org consent
  const updateOrgConsentMutation = useMutation({
    mutationFn: async ({
      consentType,
      allowed,
    }: {
      consentType: 'ai_learning' | 'external_agents';
      allowed: boolean;
    }) => {
      const response = await api.patch('/api/py/consent/organization', {
        consent_type: consentType,
        allowed,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CONSENT_KEY });
    },
  });

  const updateOrgConsent = (
    consentType: 'ai_learning' | 'external_agents',
    allowed: boolean
  ) => {
    return updateOrgConsentMutation.mutateAsync({ consentType, allowed });
  };

  // Update scope consent
  const updateScopeConsent = async (
    scopeId: string,
    consentType: 'ai_learning' | 'external_agents',
    allowed: boolean
  ) => {
    await api.patch(`/api/py/consent/scope/${scopeId}`, {
      consent_type: consentType,
      allowed,
    });
    queryClient.invalidateQueries({ queryKey: CONSENT_KEY });
  };

  return {
    orgConsent,
    scopeConsents,
    documentConsents,
    complianceReport,
    isLoading: isLoadingOrg,
    updateOrgConsent,
    updateScopeConsent,
  };
}

function calculateComplianceScore(report: ComplianceReport): number {
  // Simple scoring logic - can be enhanced
  let score = 50; // Base score

  // +20 if org has explicit settings
  if (report.organizationConsent) {
    score += 20;
  }

  // +15 if consent audit exists
  score += 15;

  // +15 based on override coverage
  if (report.scopeOverrides > 0 || report.documentOverrides > 0) {
    score += 15;
  }

  return Math.min(score, 100);
}

export default useConsent;
```

### 7.3 useSecurityLog Hook

**File:** `frontend-new/hooks/useSecurityLog.ts`

```typescript
// frontend-new/hooks/useSecurityLog.ts

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface SecurityEvent {
  id: string;
  event_type: 'document_wiped' | 'scope_deleted' | 'chunk_purged';
  resource_type: string;
  resource_name: string;
  resource_id: string;
  wipe_pattern: 'dod_5220_22_m' | 'random';
  wipe_verified: boolean;
  performed_by: string;
  performed_at: string;
  duration_ms: number;
}

interface UseSecurityLogOptions {
  search?: string;
  eventType?: string;
  limit?: number;
  page?: number;
}

export function useSecurityLog(options: UseSecurityLogOptions = {}) {
  const { search, eventType, limit = 50, page = 1 } = options;

  return useQuery({
    queryKey: ['security-log', search, eventType, limit, page],
    queryFn: async () => {
      // This endpoint would need to be created in the backend
      // For now, returning mock data structure
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (eventType) params.set('event_type', eventType);
      params.set('limit', String(limit));
      params.set('offset', String((page - 1) * limit));

      const response = await api.get<SecurityEvent[]>(
        `/api/py/admin/security-log?${params.toString()}`
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export default useSecurityLog;
```

### 7.4 useWipeProgress Hook

**File:** `frontend-new/hooks/useWipeProgress.ts`

```typescript
// frontend-new/hooks/useWipeProgress.ts

import { useState, useEffect, useCallback } from 'react';

interface WipeProgress {
  documentId: string;
  documentName: string;
  currentPass: 1 | 2 | 3;
  passProgress: number;
  isComplete: boolean;
  error?: string;
}

export function useWipeProgress(documentId: string | null) {
  const [progress, setProgress] = useState<WipeProgress | null>(null);
  const [isWiping, setIsWiping] = useState(false);

  // Simulate wipe progress (in production, this would poll an endpoint or use SSE)
  const startWipe = useCallback(async (docId: string, docName: string) => {
    setIsWiping(true);
    setProgress({
      documentId: docId,
      documentName: docName,
      currentPass: 1,
      passProgress: 0,
      isComplete: false,
    });

    // Simulate 3-pass wipe
    for (let pass = 1; pass <= 3; pass++) {
      for (let p = 0; p <= 100; p += 5) {
        await new Promise((r) => setTimeout(r, 50));
        setProgress((prev) =>
          prev
            ? {
                ...prev,
                currentPass: pass as 1 | 2 | 3,
                passProgress: p,
              }
            : null
        );
      }
    }

    // Complete
    setProgress((prev) =>
      prev
        ? {
            ...prev,
            isComplete: true,
          }
        : null
    );
    setIsWiping(false);
  }, []);

  const reset = useCallback(() => {
    setProgress(null);
    setIsWiping(false);
  }, []);

  return {
    progress,
    isWiping,
    startWipe,
    reset,
  };
}

export default useWipeProgress;
```

---

## 8. Design System Extensions

### 8.1 Color Tokens (add to globals.css)

```css
/* Add to frontend-new/app/globals.css */

:root {
  /* Ghost Protocol Colors */
  --ghost-wipe-zeros: 189 94% 43%;     /* Cyan - Pass 1 */
  --ghost-wipe-ones: 38 92% 50%;       /* Orange - Pass 2 */
  --ghost-wipe-random: 142 76% 36%;    /* Green - Pass 3 */
  --ghost-verified: 142 76% 36%;       /* Green - Verified */

  /* Scope Guard Colors */
  --approval-pending: 38 92% 50%;      /* Orange */
  --approval-urgent: 0 84% 60%;        /* Red */
  --approval-approved: 142 76% 36%;    /* Green */
  --approval-rejected: 0 62% 50%;      /* Red */

  /* Vision Colors */
  --vision-verified: 263 83% 58%;      /* Purple */
  --vision-analyzing: 189 94% 43%;     /* Cyan */

  /* Consent Colors */
  --consent-allowed: 142 76% 36%;      /* Green */
  --consent-denied: 0 62% 50%;         /* Red */
  --consent-inherited: 217 19% 35%;    /* Gray */
}
```

### 8.2 Animations (add to tailwind.config.ts)

```typescript
// Add to frontend-new/tailwind.config.ts

export default {
  theme: {
    extend: {
      animation: {
        // Existing animations...

        // Ghost Protocol
        'shred': 'shred 1.5s ease-in forwards',
        'wipe-pass': 'wipe-pass 2s linear forwards',

        // Scope Guard
        'pulse-border': 'pulse-border 2s ease-in-out infinite',
        'countdown': 'countdown 1s linear infinite',

        // Vision
        'scan': 'scan 2s ease-in-out infinite',

        // Matrix effect
        'matrix': 'matrix 0.5s linear infinite',
      },
      keyframes: {
        shred: {
          '0%': { transform: 'translateY(0) rotate(0deg)', opacity: '1' },
          '50%': { transform: 'translateY(50px) rotate(5deg)', opacity: '0.8' },
          '100%': { transform: 'translateY(200px) rotate(15deg)', opacity: '0' },
        },
        'wipe-pass': {
          '0%': { width: '0%', backgroundPosition: '0% 50%' },
          '100%': { width: '100%', backgroundPosition: '100% 50%' },
        },
        'pulse-border': {
          '0%, 100%': { borderColor: 'rgba(251, 146, 60, 0.5)' },
          '50%': { borderColor: 'rgba(239, 68, 68, 0.8)' },
        },
        countdown: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.1)' },
          '100%': { transform: 'scale(1)' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        matrix: {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '0% 100%' },
        },
      },
    },
  },
};
```

---

## 9. Integration Points

### 9.1 Modify DocumentCard.tsx

Add wipe visualization to existing document deletion:

```typescript
// In frontend-new/components/documents/DocumentCard.tsx

import { WipeProgressCard } from '@/components/ghost-protocol/WipeProgressCard';
import { WipeVerificationBadge } from '@/components/ghost-protocol/WipeVerificationBadge';
import { useWipeProgress } from '@/hooks/useWipeProgress';

// Add to component:
const { progress, isWiping, startWipe } = useWipeProgress(null);

// In delete handler:
const handleDelete = async () => {
  startWipe(document.id, document.name);
  await deleteDocument(document.id);
};

// In render, show WipeProgressCard when wiping:
{isWiping && progress && (
  <WipeProgressCard
    documentName={progress.documentName}
    currentPass={progress.currentPass}
    passProgress={progress.passProgress}
    isComplete={progress.isComplete}
  />
)}

// Add badge if document was wiped:
{document.wipedAt && (
  <WipeVerificationBadge
    wipedAt={document.wipedAt}
    pattern="dod_5220_22_m"
    verified={true}
    variant="compact"
  />
)}
```

### 9.2 Modify SourceCard.tsx

Add Vision badge for visual sources:

```typescript
// In frontend-new/components/chat/SourceCard.tsx

import { VisionVerifiedBadge } from '@/components/vision/VisionVerifiedBadge';
import { DiagramPreviewModal } from '@/components/vision/DiagramPreviewModal';

// Add vision detection:
const isVisualSource = source.metadata?.diagramType !== undefined;

// In render:
{isVisualSource && (
  <VisionVerifiedBadge
    diagramType={source.metadata.diagramType}
    confidence={source.metadata.confidence}
    modelUsed={source.metadata.modelUsed}
    onClick={() => setShowDiagramModal(true)}
  />
)}
```

### 9.3 Add to Dashboard

```typescript
// In frontend-new/app/dashboard/page.tsx

import { PendingApprovalsWidget } from '@/components/scope-guard/PendingApprovalsWidget';
import { ComplianceScoreWidget } from '@/components/consent/ComplianceScoreWidget';

// Add to dashboard layout:
<div className="grid grid-cols-3 gap-6">
  {/* Existing widgets */}

  {/* New widgets */}
  <PendingApprovalsWidget />
  <ComplianceScoreWidget score={87} variant="card" />
</div>
```

---

## 10. Testing Strategy

### 10.1 Unit Tests (Vitest)

```typescript
// frontend-new/__tests__/components/ghost-protocol/WipeProgressCard.test.tsx

import { render, screen } from '@testing-library/react';
import { WipeProgressCard } from '@/components/ghost-protocol/WipeProgressCard';

describe('WipeProgressCard', () => {
  it('renders pass progress correctly', () => {
    render(
      <WipeProgressCard
        documentName="test.pdf"
        currentPass={2}
        passProgress={50}
        isComplete={false}
      />
    );

    expect(screen.getByText('Pass 1: Zero Fill')).toBeInTheDocument();
    expect(screen.getByText('Pass 2: One Fill')).toBeInTheDocument();
    expect(screen.getByText('Pass 3: Random Data')).toBeInTheDocument();
  });

  it('shows completion state', () => {
    render(
      <WipeProgressCard
        documentName="test.pdf"
        currentPass={3}
        passProgress={100}
        isComplete={true}
      />
    );

    expect(screen.getByText(/DoD 5220.22-M Compliant/)).toBeInTheDocument();
  });
});
```

### 10.2 E2E Tests (Playwright)

```typescript
// frontend-new/e2e/ghost-protocol.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Ghost Protocol UI', () => {
  test('shows wipe progress when deleting document', async ({ page }) => {
    await page.goto('/dashboard/documents');

    // Click delete on a document
    await page.click('[data-testid="delete-document-btn"]');

    // Confirm deletion
    await page.click('[data-testid="confirm-delete"]');

    // Verify wipe progress appears
    await expect(page.locator('text=SECURE DELETION IN PROGRESS')).toBeVisible();

    // Wait for completion
    await expect(page.locator('text=Forensic Wipe Complete')).toBeVisible({ timeout: 10000 });
  });
});
```

---

## Appendix A: File Checklist

### New Files to Create

```
□ frontend-new/components/ghost-protocol/WipeProgressCard.tsx
□ frontend-new/components/ghost-protocol/ShredderAnimation.tsx
□ frontend-new/components/ghost-protocol/WipeVerificationBadge.tsx
□ frontend-new/components/ghost-protocol/SecurityLogTable.tsx
□ frontend-new/components/ghost-protocol/index.ts

□ frontend-new/components/scope-guard/MandateApprovalModal.tsx
□ frontend-new/components/scope-guard/SignatureAnimation.tsx
□ frontend-new/components/scope-guard/IntentExplanationCard.tsx
□ frontend-new/components/scope-guard/PendingApprovalsWidget.tsx
□ frontend-new/components/scope-guard/index.ts

□ frontend-new/components/vision/VisionVerifiedBadge.tsx
□ frontend-new/components/vision/DiagramPreviewModal.tsx
□ frontend-new/components/vision/SemanticOverlay.tsx
□ frontend-new/components/vision/SmartLink.tsx
□ frontend-new/components/vision/index.ts

□ frontend-new/components/consent/ConsentDashboard.tsx
□ frontend-new/components/consent/InheritanceTree.tsx
□ frontend-new/components/consent/AgentAccessPanel.tsx
□ frontend-new/components/consent/ComplianceScoreWidget.tsx
□ frontend-new/components/consent/ConsentToggle.tsx
□ frontend-new/components/consent/index.ts

□ frontend-new/hooks/useApprovals.ts
□ frontend-new/hooks/useConsent.ts
□ frontend-new/hooks/useSecurityLog.ts
□ frontend-new/hooks/useWipeProgress.ts

□ frontend-new/app/dashboard/settings/security-log/page.tsx
□ frontend-new/app/dashboard/settings/consent/page.tsx
```

### Files to Modify

```
□ frontend-new/app/globals.css (add color tokens)
□ frontend-new/tailwind.config.ts (add animations)
□ frontend-new/components/documents/DocumentCard.tsx (integrate wipe UI)
□ frontend-new/components/chat/SourceCard.tsx (add vision badge)
□ frontend-new/app/dashboard/page.tsx (add widgets)
□ frontend-new/app/dashboard/settings/layout.tsx (add tabs)
```

---

**End of Implementation Guide**
