import { useEffect, useRef, useMemo } from 'react';
import { Virtuoso } from 'react-virtuoso';
import type { Event } from '@/types';
import { Scroll } from 'lucide-react';

interface EventLogProps {
  events: Event[];
  maxEvents?: number;
}

export function EventLog({ events, maxEvents = 50 }: EventLogProps) {
  const virtuosoRef = useRef<any>(null);
  const displayEvents = events.slice(0, maxEvents);

  // FIXED: Memoize event data rendering to avoid JSON.stringify on every render
  const eventsWithFormattedData = useMemo(() => {
    return displayEvents.map((event) => ({
      ...event,
      formattedData:
        event.data && Object.keys(event.data).length > 0
          ? JSON.stringify(event.data).slice(0, 50) +
            (JSON.stringify(event.data).length > 50 ? '...' : '')
          : null,
    }));
  }, [displayEvents]);

  // Auto-scroll to bottom when new events arrive
  // FIXED: Use Virtuoso's scrollToIndex for virtualized list
  useEffect(() => {
    if (virtuosoRef.current && displayEvents.length > 0) {
      virtuosoRef.current.scrollToIndex({
        index: displayEvents.length - 1,
        behavior: 'smooth',
      });
    }
  }, [displayEvents.length]);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'spec_start':
      case 'atom_start':
      case 'iteration_start':
      case 'subtask_start':
        return 'text-blue-400';
      case 'spec_complete':
      case 'atom_complete':
      case 'iteration_complete':
      case 'subtask_complete':
        return 'text-green-400';
      case 'spec_fail':
      case 'error':
        return 'text-red-400';
      case 'progress':
        return 'text-yellow-400';
      case 'session_start':
        return 'text-purple-400';
      case 'session_end':
        return 'text-gray-400';
      default:
        return 'text-muted-foreground';
    }
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'spec_start':
        return '▶';
      case 'spec_complete':
        return '✓';
      case 'spec_fail':
      case 'error':
        return '✕';
      case 'progress':
        return '⋯';
      case 'session_start':
        return '◉';
      case 'session_end':
        return '○';
      case 'atom_start':
      case 'atom_complete':
        return '◆';
      case 'iteration_start':
      case 'iteration_complete':
        return '↻';
      default:
        return '•';
    }
  };

  return (
    <div className="w-full h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Scroll className="h-4 w-4" />
          Event Log
        </h3>
        <span className="text-xs text-muted-foreground">
          {displayEvents.length} events
        </span>
      </div>

      <div className="bg-muted/50 rounded-md border border-border h-64 font-mono text-xs">
        {displayEvents.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            No events yet...
          </div>
        ) : (
          <Virtuoso
            ref={virtuosoRef}
            style={{ height: '256px' }}
            data={eventsWithFormattedData}
            itemContent={(index, event) => (
              <div className="flex items-start gap-2 hover:bg-muted/80 rounded px-3 py-1 transition-colors">
                <span className="text-muted-foreground select-none">
                  {getEventIcon(event.eventType)}
                </span>
                <span className="text-muted-foreground select-none">
                  {formatTimestamp(event.createdAt)}
                </span>
                <span className={getEventColor(event.eventType)}>
                  {event.eventType}
                </span>
                {event.formattedData && (
                  <span className="text-muted-foreground truncate">
                    {event.formattedData}
                  </span>
                )}
              </div>
            )}
            components={{
              Scroller: (props: any) => (
                <div {...props} className="overflow-y-auto" />
              ),
            }}
          />
        )}
      </div>
    </div>
  );
}
