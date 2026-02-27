'use client';

import { useRef, useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  MoreVertical,
  Edit,
  Trash2,
  Play,
  Pause,
  Power,
  Wrench,
  ArrowDownToLine,
  GripVertical,
  Crown,
  Gift,
  CheckCircle2,
  AlertCircle,
  Timer,
  ChevronDown,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { AgentPoolAgent, PoolAgentStatus } from '@/types';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { getAgentColor } from '@/lib/agentColors';

interface AgentCardProps {
  agent: AgentPoolAgent;
  onSelect?: (agent: AgentPoolAgent) => void;
  onEdit?: (agent: AgentPoolAgent) => void;
  onDelete?: (agent: AgentPoolAgent) => void;
  onStatusChange?: (agentId: string, status: PoolAgentStatus) => void;
  /** Whether the card is draggable (default: true) */
  draggable?: boolean;
}

export function AgentCard({ agent, onSelect, onEdit, onDelete, onStatusChange, draggable = true }: AgentCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [showMetrics, setShowMetrics] = useState(false);

  // Get color for agent-project linking
  const agentColor = getAgentColor(agent.agentId);

  // Setup draggable
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `agent-${agent.id}`,
    data: {
      type: 'agent',
      agent,
      agentId: agent.agentId,
    },
    disabled: !draggable,
  });

  // Apply transform for drag
  const style = transform
    ? {
        transform: CSS.Translate.toString(transform),
        zIndex: isDragging ? 50 : undefined,
        opacity: isDragging ? 0.5 : 1,
      }
    : undefined;

  // Combine refs
  const refs = (node: HTMLDivElement) => {
    (cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
    setNodeRef(node);
  };

  const getStatusColor = (status: PoolAgentStatus): string => {
    switch (status) {
      case 'available':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'busy':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'offline':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'maintenance':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'draining':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  const getStatusIcon = (status: PoolAgentStatus) => {
    switch (status) {
      case 'available':
        return <Play className="h-3 w-3" />;
      case 'busy':
        return <Pause className="h-3 w-3" />;
      case 'offline':
        return <Power className="h-3 w-3" />;
      case 'maintenance':
        return <Wrench className="h-3 w-3" />;
      case 'draining':
        return <ArrowDownToLine className="h-3 w-3" />;
      default:
        return null;
    }
  };

  const getAgentTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      ralph: 'bg-purple-500/10 text-purple-500',
      claude: 'bg-orange-500/10 text-orange-500',
      cursor: 'bg-blue-500/10 text-blue-500',
      terminal: 'bg-gray-500/10 text-gray-500',
      crawler: 'bg-green-500/10 text-green-500',
      analyzer: 'bg-cyan-500/10 text-cyan-500',
      reporter: 'bg-pink-500/10 text-pink-500',
      tester: 'bg-yellow-500/10 text-yellow-500',
      custom: 'bg-indigo-500/10 text-indigo-500',
    };
    return colors[type] || 'bg-muted text-muted-foreground';
  };

  const getUtilizationColor = (percent: number): string => {
    if (percent >= 80) return 'bg-red-500';
    if (percent >= 60) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const handleStatusChange = (newStatus: PoolAgentStatus) => {
    if (onStatusChange) {
      onStatusChange(agent.agentId, newStatus);
    }
  };

  return (
    <Card
      ref={refs}
      style={{
        ...style,
        borderTopColor: agentColor,
        borderTopWidth: 3,
      }}
      className={cn(
        'group hover:border-primary/50 transition-all cursor-pointer',
        !agent.isAvailable && 'opacity-75',
        isDragging && 'shadow-xl ring-2 ring-primary',
        draggable && 'hover:shadow-md'
      )}
      onClick={() => !isDragging && onSelect?.(agent)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-2 flex-1 min-w-0">
            {/* Drag Handle */}
            {draggable && (
              <div
                {...attributes}
                {...listeners}
                className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground pt-1 flex-shrink-0"
                onClick={(e) => e.stopPropagation()}
              >
                <GripVertical className="h-4 w-4" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base font-medium truncate flex items-center gap-2">
                {agent.agentId}
                <Badge className={`text-xs ${getAgentTypeColor(agent.agentType)}`}>
                  {agent.agentType}
                </Badge>
              </CardTitle>
              <div className="text-xs text-muted-foreground mt-1">
                Pool ID: {agent.id.slice(0, 8)}...
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`gap-1.5 ${getStatusColor(agent.status)}`}>
              {getStatusIcon(agent.status)}
              {agent.status}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                <DropdownMenuItem onClick={() => onEdit?.(agent)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                {agent.status !== 'available' && (
                  <DropdownMenuItem onClick={() => handleStatusChange('available')}>
                    <Play className="h-4 w-4 mr-2" />
                    Set Available
                  </DropdownMenuItem>
                )}
                {agent.status !== 'maintenance' && (
                  <DropdownMenuItem onClick={() => handleStatusChange('maintenance')}>
                    <Wrench className="h-4 w-4 mr-2" />
                    Set Maintenance
                  </DropdownMenuItem>
                )}
                {agent.status !== 'offline' && (
                  <DropdownMenuItem onClick={() => handleStatusChange('offline')}>
                    <Power className="h-4 w-4 mr-2" />
                    Set Offline
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => onDelete?.(agent)}
                  className="text-red-600 focus:text-red-600"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Unregister
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Capacity and Utilization */}
        <div>
          <div className="flex items-center justify-between text-sm mb-1.5">
            <span className="text-muted-foreground">Load</span>
            <span className="font-medium">
              {agent.currentLoad} / {agent.maxCapacity}
            </span>
          </div>
          <Progress
            value={agent.utilizationPercent}
            className="h-2"
          />
          <div className="text-xs text-muted-foreground mt-1">
            {agent.utilizationPercent.toFixed(0)}% utilized
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-lg font-bold">{agent.totalAssigned}</div>
            <div className="text-xs text-muted-foreground">Assigned</div>
          </div>
          <div>
            <div className="text-lg font-bold text-green-600">{agent.totalCompleted}</div>
            <div className="text-xs text-muted-foreground">Completed</div>
          </div>
          <div>
            <div className="text-lg font-bold text-red-600">{agent.totalFailed}</div>
            <div className="text-xs text-muted-foreground">Failed</div>
          </div>
        </div>

        {/* Completion Rate */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Success Rate</span>
          <span className={`font-medium ${agent.completionRate >= 0.8 ? 'text-green-600' : agent.completionRate >= 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
            {(agent.completionRate * 100).toFixed(1)}%
          </span>
        </div>

        {/* Last Heartbeat */}
        {agent.lastHeartbeat && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Last Heartbeat</span>
            <span className="text-xs">
              {formatDistanceToNow(new Date(agent.lastHeartbeat), { addSuffix: true })}
            </span>
          </div>
        )}

        {/* Current Project */}
        {agent.currentProjectId && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Project</span>
            <span className="text-xs font-mono truncate ml-2" title={agent.currentProjectId}>
              {agent.currentProjectId.slice(0, 8)}...
            </span>
          </div>
        )}

        {/* Capabilities */}
        {agent.capabilities && agent.capabilities.length > 0 && (
          <div>
            <div className="text-xs text-muted-foreground mb-1.5">Capabilities</div>
            <div className="flex flex-wrap gap-1">
              {agent.capabilities.slice(0, 3).map((cap, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {cap}
                </Badge>
              ))}
              {agent.capabilities.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{agent.capabilities.length - 3}
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Affinity Tag */}
        {agent.affinityTag && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Affinity</span>
            <Badge variant="secondary" className="text-xs">
              {agent.affinityTag}
            </Badge>
          </div>
        )}

        {/* Priority */}
        {agent.priority !== 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Priority</span>
            <Badge variant="outline" className="text-xs">
              {agent.priority > 0 ? `+${agent.priority}` : agent.priority}
            </Badge>
          </div>
        )}

        {/* Quota Usage Bar */}
        {agent.usage && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Quota Usage</span>
              <span className="font-medium">
                {agent.usage.current.toLocaleString()} / {agent.usage.max.toLocaleString()}
              </span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full transition-all',
                  (agent.usage.current / agent.usage.max) >= 1 ? 'bg-red-500' :
                  (agent.usage.current / agent.usage.max) >= 0.8 ? 'bg-yellow-500' : 'bg-green-500'
                )}
                style={{ width: `${Math.min(100, (agent.usage.current / agent.usage.max) * 100)}%` }}
              />
            </div>
            {agent.usage.current >= agent.usage.max && agent.usage.resetsAt && (
              <div className="text-xs text-amber-500 flex items-center gap-1">
                <Timer className="h-3 w-3" />
                Resets in {formatDistanceToNow(new Date(agent.usage.resetsAt))}
              </div>
            )}
          </div>
        )}

        {/* Status with Assigned Project */}
        {(agent.assignedProject || agent.currentProjectId) && (
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={getStatusColor(agent.status)}>
              {getStatusIcon(agent.status)}
              {agent.status}
            </Badge>
            {agent.assignedProject && (
              <Badge variant="outline" className="text-xs" style={{ borderColor: agentColor }}>
                → {agent.assignedProject.name}
              </Badge>
            )}
          </div>
        )}

        {/* Tier and Auth Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {agent.tier === 'paid' ? (
              <span title="Paid tier">
                <Crown className="h-4 w-4 text-amber-500" />
              </span>
            ) : agent.tier === 'free' ? (
              <span title="Free tier">
                <Gift className="h-4 w-4 text-muted-foreground" />
              </span>
            ) : null}
            {agent.isAuthenticated !== undefined && (
              <span title={agent.isAuthenticated ? 'Authenticated' : 'Not authenticated'}>
                {agent.isAuthenticated ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-500" />
                )}
              </span>
            )}
          </div>
          {agent.startedAt && (
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <Timer className="h-3 w-3" />
              {formatDistanceToNow(new Date(agent.startedAt))}
            </div>
          )}
        </div>

        {/* Collapsible Additional Metrics */}
        {(agent.model || agent.requestRate !== undefined || agent.errorRate !== undefined || agent.avgResponseTime !== undefined) && (
          <Collapsible open={showMetrics} onOpenChange={setShowMetrics}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between h-8 px-2">
                <span className="text-xs">More Metrics</span>
                <ChevronDown className={cn('h-4 w-4 transition-transform', showMetrics && 'rotate-180')} />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 pt-2">
              <div className="grid grid-cols-2 gap-2 text-xs">
                {agent.model && (
                  <div className="text-muted-foreground">Model: <span className="font-medium">{agent.model}</span></div>
                )}
                {agent.requestRate !== undefined && (
                  <div className="text-muted-foreground">Req/min: <span className="font-medium">{agent.requestRate}</span></div>
                )}
                {agent.errorRate !== undefined && (
                  <div className={cn(agent.errorRate > 5 ? 'text-red-500' : 'text-muted-foreground')}>
                    Errors: <span className="font-medium">{agent.errorRate}%</span>
                  </div>
                )}
                {agent.avgResponseTime !== undefined && (
                  <div className="text-muted-foreground">Avg Response: <span className="font-medium">{agent.avgResponseTime}ms</span></div>
                )}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}
