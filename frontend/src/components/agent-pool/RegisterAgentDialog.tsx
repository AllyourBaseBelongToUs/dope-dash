'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import type { AgentPoolCreateRequest, AgentType, PoolAgentStatus } from '@/types';

interface RegisterAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: AgentPoolCreateRequest) => Promise<void>;
  isLoading?: boolean;
}

export function RegisterAgentDialog({
  open,
  onOpenChange,
  onSubmit,
  isLoading = false,
}: RegisterAgentDialogProps) {
  const [formData, setFormData] = useState<AgentPoolCreateRequest>({
    agentId: '',
    agentType: 'ralph',
    status: 'available',
    currentLoad: 0,
    maxCapacity: 5,
    capabilities: [],
    metadata: {},
    priority: 0,
  });

  const [capabilityInput, setCapabilityInput] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(formData);
    // Reset form
    setFormData({
      agentId: '',
      agentType: 'ralph',
      status: 'available',
      currentLoad: 0,
      maxCapacity: 5,
      capabilities: [],
      metadata: {},
      priority: 0,
    });
    setCapabilityInput('');
  };

  const addCapability = () => {
    if (capabilityInput.trim() && !formData.capabilities?.includes(capabilityInput.trim())) {
      setFormData({
        ...formData,
        capabilities: [...(formData.capabilities || []), capabilityInput.trim()],
      });
      setCapabilityInput('');
    }
  };

  const removeCapability = (cap: string) => {
    setFormData({
      ...formData,
      capabilities: formData.capabilities?.filter((c) => c !== cap) || [],
    });
  };

  const agentTypes: AgentType[] = ['ralph', 'claude', 'cursor', 'terminal', 'crawler', 'analyzer', 'reporter', 'tester', 'custom'];
  const statuses: PoolAgentStatus[] = ['available', 'busy', 'offline', 'maintenance', 'draining'];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Register Agent</DialogTitle>
          <DialogDescription>
            Add a new agent to the pool. The agent will be available for project assignments.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Agent ID */}
          <div className="space-y-2">
            <Label htmlFor="agentId">Agent ID *</Label>
            <Input
              id="agentId"
              placeholder="e.g., ralph-agent-001"
              value={formData.agentId}
              onChange={(e) => setFormData({ ...formData, agentId: e.target.value })}
              required
            />
            <p className="text-xs text-muted-foreground">
              Unique identifier for this agent (must be unique across the pool)
            </p>
          </div>

          {/* Agent Type */}
          <div className="space-y-2">
            <Label htmlFor="agentType">Agent Type *</Label>
            <Select
              value={formData.agentType}
              onValueChange={(value: AgentType) => setFormData({ ...formData, agentType: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {agentTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label htmlFor="status">Initial Status</Label>
            <Select
              value={formData.status}
              onValueChange={(value: PoolAgentStatus) => setFormData({ ...formData, status: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {statuses.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Capacity */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="maxCapacity">Max Capacity *</Label>
              <Input
                id="maxCapacity"
                type="number"
                min="1"
                max="100"
                value={formData.maxCapacity}
                onChange={(e) => setFormData({ ...formData, maxCapacity: parseInt(e.target.value) || 1 })}
                required
              />
              <p className="text-xs text-muted-foreground">
                Maximum concurrent tasks
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="priority">Priority</Label>
              <Input
                id="priority"
                type="number"
                min="-10"
                max="10"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
              />
              <p className="text-xs text-muted-foreground">
                Higher = preferred for assignment
              </p>
            </div>
          </div>

          {/* Affinity Tag */}
          <div className="space-y-2">
            <Label htmlFor="affinityTag">Affinity Tag (Optional)</Label>
            <Input
              id="affinityTag"
              placeholder="e.g., project-alpha"
              value={formData.affinityTag || ''}
              onChange={(e) => setFormData({ ...formData, affinityTag: e.target.value || undefined })}
            />
            <p className="text-xs text-muted-foreground">
              Agents with the same tag will be preferred for related projects
            </p>
          </div>

          {/* Capabilities */}
          <div className="space-y-2">
            <Label>Capabilities</Label>
            <div className="flex gap-2">
              <Input
                placeholder="e.g., python, docker, gpu"
                value={capabilityInput}
                onChange={(e) => setCapabilityInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCapability())}
              />
              <Button type="button" variant="outline" onClick={addCapability}>
                Add
              </Button>
            </div>
            {formData.capabilities && formData.capabilities.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {formData.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-secondary text-secondary-foreground text-xs rounded-md"
                  >
                    {cap}
                    <button
                      type="button"
                      onClick={() => removeCapability(cap)}
                      className="hover:text-destructive"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Optional Runtime Info */}
          <div className="space-y-4 border-t pt-4">
            <p className="text-sm font-medium">Runtime Information (Optional)</p>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="pid">Process ID</Label>
                <Input
                  id="pid"
                  type="number"
                  placeholder="e.g., 12345"
                  value={formData.pid || ''}
                  onChange={(e) => setFormData({ ...formData, pid: e.target.value ? parseInt(e.target.value) : undefined })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="tmuxSession">Tmux Session</Label>
                <Input
                  id="tmuxSession"
                  placeholder="e.g., agent-001"
                  value={formData.tmuxSession || ''}
                  onChange={(e) => setFormData({ ...formData, tmuxSession: e.target.value || undefined })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="workingDir">Working Directory</Label>
              <Input
                id="workingDir"
                placeholder="e.g., /home/user/projects"
                value={formData.workingDir || ''}
                onChange={(e) => setFormData({ ...formData, workingDir: e.target.value || undefined })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="command">Command</Label>
              <Input
                id="command"
                placeholder="e.g., python agent.py"
                value={formData.command || ''}
                onChange={(e) => setFormData({ ...formData, command: e.target.value || undefined })}
              />
            </div>
          </div>

          {/* Metadata */}
          <div className="space-y-2">
            <Label htmlFor="metadata">Metadata (JSON)</Label>
            <Textarea
              id="metadata"
              placeholder='{"version": "1.0.0", "region": "us-east"}'
              value={typeof formData.metadata === 'string' ? formData.metadata : JSON.stringify(formData.metadata, null, 2)}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value || '{}');
                  setFormData({ ...formData, metadata: parsed });
                } catch {
                  // Invalid JSON, don't update
                }
              }}
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || !formData.agentId}>
              {isLoading ? 'Registering...' : 'Register Agent'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
