import type { SpecProgress } from '@/types';

interface ProgressBarProps {
  specs: SpecProgress[];
  completedSpecs: number;
  totalSpecs: number;
  progress: number;
  currentSpec?: string;
}

export function ProgressBar({ specs, completedSpecs, totalSpecs, progress, currentSpec }: ProgressBarProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-foreground">
          {completedSpecs} of {totalSpecs} specs complete
        </span>
        <span className="text-sm text-muted-foreground">
          {Math.round(progress)}%
        </span>
      </div>

      <div className="w-full bg-muted rounded-full h-2.5 overflow-hidden">
        <div
          className="bg-primary h-2.5 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {currentSpec && (
        <div className="mt-2 text-sm text-muted-foreground">
          Currently running: {currentSpec}
        </div>
      )}

      {specs.length > 0 && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {specs.map((spec) => (
            <div
              key={spec.specName}
              className={`flex items-center gap-2 px-3 py-2 rounded-md border text-sm ${
                spec.status === 'completed'
                  ? 'bg-green-950/30 border-green-900/50 text-green-400'
                  : spec.status === 'running'
                    ? 'bg-blue-950/30 border-blue-900/50 text-blue-400'
                    : spec.status === 'failed'
                      ? 'bg-red-950/30 border-red-900/50 text-red-400'
                      : 'bg-muted/50 border-muted text-muted-foreground'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  spec.status === 'completed'
                    ? 'bg-green-500'
                    : spec.status === 'running'
                      ? 'bg-blue-500 animate-pulse'
                      : spec.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-muted-foreground'
                }`}
              />
              <span className="font-mono text-xs">{spec.specName}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
