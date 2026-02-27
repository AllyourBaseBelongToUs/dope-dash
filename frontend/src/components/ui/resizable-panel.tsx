'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { GripVertical } from 'lucide-react';

interface ResizableSplitPanelProps {
  left: React.ReactNode;
  right: React.ReactNode;
  defaultLeftWidth?: number; // percentage 0-100
  minLeftWidth?: number;
  maxLeftWidth?: number;
  storageKey?: string; // for persisting size
  className?: string;
}

export function ResizableSplitPanel({
  left,
  right,
  defaultLeftWidth = 50,
  minLeftWidth = 25,
  maxLeftWidth = 75,
  storageKey,
  className,
}: ResizableSplitPanelProps) {
  // Load from localStorage if available
  const getInitialWidth = useCallback(() => {
    if (storageKey && typeof window !== 'undefined') {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = parseFloat(saved);
        if (!isNaN(parsed) && parsed >= minLeftWidth && parsed <= maxLeftWidth) {
          return parsed;
        }
      }
    }
    return defaultLeftWidth;
  }, [storageKey, defaultLeftWidth, minLeftWidth, maxLeftWidth]);

  const [leftWidth, setLeftWidth] = useState(getInitialWidth);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Persist to localStorage
  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(storageKey, leftWidth.toString());
    }
  }, [leftWidth, storageKey]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const newWidth = ((e.clientX - rect.left) / rect.width) * 100;
    const clampedWidth = Math.min(maxLeftWidth, Math.max(minLeftWidth, newWidth));

    setLeftWidth(clampedWidth);
  }, [isDragging, minLeftWidth, maxLeftWidth]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Global mouse events for smooth dragging
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Keyboard accessibility - arrow keys to resize
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    const step = 1; // 1% per keypress
    switch (e.key) {
      case 'ArrowLeft':
        e.preventDefault();
        setLeftWidth(w => Math.min(maxLeftWidth, Math.max(minLeftWidth, w - step)));
        break;
      case 'ArrowRight':
        e.preventDefault();
        setLeftWidth(w => Math.min(maxLeftWidth, Math.max(minLeftWidth, w + step)));
        break;
    }
  }, [minLeftWidth, maxLeftWidth]);

  return (
    <div
      ref={containerRef}
      className={cn('flex h-full', className)}
    >
      {/* Left Panel */}
      <div
        style={{ width: `${leftWidth}%` }}
        className="overflow-hidden"
      >
        {left}
      </div>

      {/* Resizer */}
      <div
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={leftWidth}
        aria-valuemin={minLeftWidth}
        aria-valuemax={maxLeftWidth}
        className={cn(
          'w-1.5 flex-shrink-0 cursor-col-resize focus:outline-none',
          'bg-border hover:bg-primary/50 transition-colors',
          'flex items-center justify-center',
          isDragging && 'bg-primary'
        )}
      >
        <GripVertical className="h-6 w-3 text-muted-foreground" />
      </div>

      {/* Right Panel */}
      <div
        style={{ width: `${100 - leftWidth}%` }}
        className="overflow-hidden"
      >
        {right}
      </div>
    </div>
  );
}
