'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot,
  Plus,
  Trash2,
  Shield,
  ShieldOff,
  Search,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

interface Agent {
  id: string;
  name: string;
  agentId: string;
  isAllowed: boolean;
  createdAt: string;
  lastAccess?: string;
}

interface AgentAccessPanelProps {
  agents?: Agent[];
  onToggleAccess?: (agentId: string, allowed: boolean) => void;
  onAddAgent?: (name: string, agentId: string) => void;
  onRemoveAgent?: (agentId: string) => void;
}

function formatDate(dateString?: string): string {
  if (!dateString) return 'Never';
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

export function AgentAccessPanel({
  agents = [],
  onToggleAccess,
  onAddAgent,
  onRemoveAgent,
}: AgentAccessPanelProps) {
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentId, setNewAgentId] = useState('');

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(search.toLowerCase()) ||
    agent.agentId.toLowerCase().includes(search.toLowerCase())
  );

  const handleAddAgent = () => {
    if (newAgentName && newAgentId) {
      onAddAgent?.(newAgentName, newAgentId);
      setNewAgentName('');
      setNewAgentId('');
      setShowAddModal(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Bot className="h-5 w-5 text-violet-400" />
              Agent Access Control
            </CardTitle>
            <CardDescription>
              Manage which AI agents can access your organization&apos;s data
            </CardDescription>
          </div>
          <Button
            size="sm"
            className="gap-2"
            onClick={() => setShowAddModal(true)}
          >
            <Plus className="h-4 w-4" />
            Add Agent
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Agent list */}
        <div className="space-y-2">
          <AnimatePresence>
            {filteredAgents.map((agent) => (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={cn(
                  'flex items-center gap-4 p-4 rounded-lg border transition-colors',
                  agent.isAllowed
                    ? 'border-green-500/30 bg-green-500/5'
                    : 'border-red-500/30 bg-red-500/5'
                )}
              >
                {/* Agent icon and status */}
                <div className="relative">
                  <div className={cn(
                    'p-2 rounded-full',
                    agent.isAllowed ? 'bg-green-500/10' : 'bg-red-500/10'
                  )}>
                    <Bot className={cn(
                      'h-5 w-5',
                      agent.isAllowed ? 'text-green-400' : 'text-red-400'
                    )} />
                  </div>
                  <div className={cn(
                    'absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-background',
                    agent.isAllowed ? 'bg-green-500' : 'bg-red-500'
                  )} />
                </div>

                {/* Agent info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{agent.name}</span>
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-[10px]',
                        agent.isAllowed
                          ? 'text-green-400 border-green-500/30'
                          : 'text-red-400 border-red-500/30'
                      )}
                    >
                      {agent.isAllowed ? (
                        <>
                          <Shield className="h-3 w-3 mr-1" />
                          ALLOWED
                        </>
                      ) : (
                        <>
                          <ShieldOff className="h-3 w-3 mr-1" />
                          BLOCKED
                        </>
                      )}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono truncate">
                    {agent.agentId}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    Last access: {formatDate(agent.lastAccess)}
                  </p>
                </div>

                {/* Toggle and delete */}
                <div className="flex items-center gap-3">
                  <Switch
                    checked={agent.isAllowed}
                    onCheckedChange={(checked) => onToggleAccess?.(agent.id, checked)}
                    className={cn(
                      agent.isAllowed && 'data-[state=checked]:bg-green-500'
                    )}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-red-400"
                    onClick={() => onRemoveAgent?.(agent.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredAgents.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No agents configured</p>
              <p className="text-xs">Add agents to control data access</p>
            </div>
          )}
        </div>
      </CardContent>

      {/* Add Agent Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Agent</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Agent Name</label>
              <Input
                placeholder="e.g., Claude Desktop"
                value={newAgentName}
                onChange={(e) => setNewAgentName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Agent ID</label>
              <Input
                placeholder="e.g., agent_claude_abc123"
                value={newAgentId}
                onChange={(e) => setNewAgentId(e.target.value)}
                className="font-mono"
              />
              <p className="text-xs text-muted-foreground">
                The unique identifier provided by the agent
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddAgent} disabled={!newAgentName || !newAgentId}>
              Add Agent
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

export default AgentAccessPanel;
