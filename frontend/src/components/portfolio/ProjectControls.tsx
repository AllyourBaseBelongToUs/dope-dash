import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Pause,
  Play,
  SkipForward,
  Square,
  RotateCcw,
  RotateCw,
  Loader2,
} from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { usePortfolioStore } from '@/store/portfolioStore';
import type { Project, ProjectStatus } from '@/types';
import { formatDistanceToNow } from 'date-fns';

interface ProjectControlsProps {
  project: Project;
  onControlApplied?: () => void;
}

const getAvailableControls = (status: ProjectStatus) => {
  switch (status) {
    case 'idle':
      return ['restart'];
    case 'running':
      return ['pause', 'stop', 'skip'];
    case 'paused':
      return ['resume', 'stop', 'skip'];
    case 'error':
      return ['retry', 'stop', 'restart'];
    case 'completed':
      return ['restart'];
    default:
      return [];
  }
};

const controlConfigs = {
  pause: {
    icon: Pause,
    label: 'Pause',
    description: 'Pause all active agents in this project. Agents will stop processing but remain available.',
    variant: 'outline' as const,
    requiresConfirmation: false,
  },
  resume: {
    icon: Play,
    label: 'Resume',
    description: 'Resume a paused project. Agents will continue processing from where they left off.',
    variant: 'default' as const,
    requiresConfirmation: false,
  },
  skip: {
    icon: SkipForward,
    label: 'Skip',
    description: 'Skip remaining specs in this project. The project will be marked as completed.',
    variant: 'outline' as const,
    requiresConfirmation: true,
  },
  stop: {
    icon: Square,
    label: 'Stop',
    description: 'Stop all agents in this project. This will terminate all active sessions.',
    variant: 'destructive' as const,
    requiresConfirmation: true,
  },
  retry: {
    icon: RotateCcw,
    label: 'Retry',
    description: 'Retry failed specs in this project. Only specs that previously failed will be re-run.',
    variant: 'outline' as const,
    requiresConfirmation: false,
  },
  restart: {
    icon: RotateCw,
    label: 'Restart',
    description: 'Restart this project from the beginning. All progress will be reset and specs will run from the start.',
    variant: 'outline' as const,
    requiresConfirmation: true,
  },
};

export function ProjectControls({ project, onControlApplied }: ProjectControlsProps) {
  const [pendingControl, setPendingControl] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const pauseProject = usePortfolioStore((state) => state.pauseProject);
  const resumeProject = usePortfolioStore((state) => state.resumeProject);
  const skipProject = usePortfolioStore((state) => state.skipProject);
  const stopProject = usePortfolioStore((state) => state.stopProject);
  const retryProject = usePortfolioStore((state) => state.retryProject);
  const restartProject = usePortfolioStore((state) => state.restartProject);

  const availableControls = getAvailableControls(project.status);

  const executeControl = async (controlType: string) => {
    setIsExecuting(true);
    try {
      let result;
      switch (controlType) {
        case 'pause':
          result = await pauseProject(project.id);
          break;
        case 'resume':
          result = await resumeProject(project.id);
          break;
        case 'skip':
          result = await skipProject(project.id);
          break;
        case 'stop':
          result = await stopProject(project.id);
          break;
        case 'retry':
          result = await retryProject(project.id);
          break;
        case 'restart':
          result = await restartProject(project.id);
          break;
      }

      if (result && onControlApplied) {
        onControlApplied();
      }
    } finally {
      setIsExecuting(false);
      setPendingControl(null);
    }
  };

  const handleControlClick = (controlType: string, requiresConfirmation: boolean) => {
    if (requiresConfirmation) {
      setPendingControl(controlType);
    } else {
      executeControl(controlType);
    }
  };

  const ControlButton = ({
    controlType,
  }: {
    controlType: string;
  }) => {
    const config = controlConfigs[controlType as keyof typeof controlConfigs];
    const Icon = config.icon;

    return (
      <Button
        variant={config.variant}
        size="sm"
        onClick={() => handleControlClick(controlType, config.requiresConfirmation)}
        disabled={isExecuting}
        className="min-w-[90px]"
      >
        {isExecuting && pendingControl === controlType ? (
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        ) : (
          <Icon className="h-4 w-4 mr-2" />
        )}
        {config.label}
      </Button>
    );
  };

  return (
    <div className="flex flex-wrap gap-2">
      {availableControls.map((controlType) => {
        const config = controlConfigs[controlType as keyof typeof controlConfigs];

        if (config.requiresConfirmation) {
          return (
            <AlertDialog
              key={controlType}
              open={pendingControl === controlType}
              onOpenChange={(open) => {
                if (!open) setPendingControl(null);
              }}
            >
              <AlertDialogTrigger asChild>
                <ControlButton controlType={controlType} />
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle asChild>
                    <div className="flex items-center gap-2">
                      <config.icon className="h-5 w-5" />
                      <span>
                        {config.label} {project.name}?
                      </span>
                    </div>
                  </AlertDialogTitle>
                  <AlertDialogDescription>
                    {config.description}
                    {controlType === 'stop' && project.activeAgents > 0 && (
                      <div className="mt-2 p-2 bg-destructive/10 rounded-md border border-destructive/20">
                        <strong>Warning:</strong> This will affect {project.activeAgents} active agent
                        {project.activeAgents > 1 ? 's' : ''}.
                      </div>
                    )}
                    {controlType === 'restart' && project.progress > 0 && (
                      <div className="mt-2 p-2 bg-destructive/10 rounded-md border border-destructive/20">
                        <strong>Warning:</strong> This will reset all progress. Currently{' '}
                        {Math.round(project.progress * 100)}% complete ({project.completedSpecs} of{' '}
                        {project.totalSpecs} specs done).
                      </div>
                    )}
                    {controlType === 'skip' && (
                      <div className="mt-2 p-2 bg-muted rounded-md border">
                        The project will be marked as completed with current progress.
                      </div>
                    )}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.preventDefault();
                      executeControl(controlType);
                    }}
                    className={controlType === 'stop' ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90' : ''}
                  >
                    {isExecuting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        {config.label}ing...
                      </>
                    ) : (
                      `${config.label} Project`
                    )}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          );
        }

        return <ControlButton key={controlType} controlType={controlType} />;
      })}
    </div>
  );
}
