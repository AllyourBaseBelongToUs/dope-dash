'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Loader2, MessageSquare, Clock, Send, AlertCircle } from 'lucide-react';

interface FeedbackRequest {
  request_id: string;
  message: string;
  options?: string[];
  timeout: number;
  project_directory?: string;
  timestamp: string;
}

interface FeedbackWebSocketMessage {
  type: string;
  request_id?: string;
  message?: string;
  options?: string[];
  timeout?: number;
  project_directory?: string;
  timestamp?: string;
  client_id?: string;
}

export function FeedbackPanel() {
  const [request, setRequest] = useState<FeedbackRequest | null>(null);
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Track current request ID to prevent race conditions
  const currentRequestIdRef = useRef<string | null>(null);

  // Handle feedback submission
  const submitFeedback = useCallback(async (selectedOption?: string) => {
    if (!request) return;

    const feedbackText = selectedOption || feedback;

    // Validate for free-form input (options are pre-validated)
    if (!request.options && !feedbackText.trim()) {
      setError("Please enter feedback before submitting");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/feedback/${request.request_id}/submit`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            feedback: feedbackText,
            images: null,
            settings: null,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      // Success - close dialog
      setRequest(null);
      setFeedback('');
      setCountdown(null);
      currentRequestIdRef.current = null;

    } catch (err) {
      setError("Failed to submit feedback. Please try again.");
      console.error('Feedback submission error:', err);
    } finally {
      setIsSubmitting(false);
    }
  }, [request, feedback]);

  // Handle option button click
  const handleOptionClick = (option: string) => {
    setError(null);
    submitFeedback(option);
  };

  // WebSocket connection for feedback requests
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/feedback/ws`;

    const connect = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          console.log('[FeedbackPanel] Connected to feedback WebSocket');
        };

        ws.onmessage = (event) => {
          try {
            const data: FeedbackWebSocketMessage = JSON.parse(event.data);

            if (data.type === 'connection_established') {
              console.log('[FeedbackPanel] Connection confirmed:', data.client_id);
            } else if (data.type === 'feedback_request') {
              // New feedback request from AI agent
              // Track this request ID for countdown race condition prevention
              currentRequestIdRef.current = data.request_id || null;

              setRequest({
                request_id: data.request_id!,
                message: data.message!,
                options: data.options,
                timeout: data.timeout || 300,
                project_directory: data.project_directory,
                timestamp: data.timestamp || new Date().toISOString(),
              });
              setCountdown(data.timeout || 300);
              setFeedback('');
              setError(null); // Clear any previous errors
            } else if (data.type === 'heartbeat_response') {
              // Heartbeat response - connection is alive
            } else if (data.type === 'error') {
              console.error('[FeedbackPanel] Server error:', data.message);
            }
          } catch (err) {
            console.error('[FeedbackPanel] Failed to parse message:', err);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          console.log('[FeedbackPanel] Disconnected from feedback WebSocket');
          // Reconnect after 3 seconds
          setTimeout(connect, 3000);
        };

        ws.onerror = (err) => {
          console.error('[FeedbackPanel] WebSocket error:', err);
        };
      } catch (err) {
        console.error('[FeedbackPanel] Failed to connect:', err);
        setTimeout(connect, 3000);
      }
    };

    connect();

    // Heartbeat to keep connection alive
    const heartbeatInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, 30000);

    return () => {
      clearInterval(heartbeatInterval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Countdown timer - fixed race condition
  useEffect(() => {
    // Only run if we have a request
    if (!request?.request_id) return;

    const requestId = request.request_id;

    // Store the request ID we're counting down for
    currentRequestIdRef.current = requestId;

    const tick = () => {
      // Check if this is still the current request
      if (currentRequestIdRef.current !== requestId) {
        return; // Stop counting - different request is active
      }

      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          // Timeout - only clear if still same request
          if (currentRequestIdRef.current === requestId) {
            setRequest(null);
            setFeedback('');
            setError(null);
            currentRequestIdRef.current = null;
          }
          return null;
        }
        return prev - 1;
      });
    };

    const intervalId = setInterval(tick, 1000);

    return () => {
      clearInterval(intervalId);
    };
  }, [request?.request_id]); // Only re-run when request ID changes

  // Format countdown as MM:SS
  const formatCountdown = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Don't render anything if no active request
  if (!request) {
    return null;
  }

  return (
    <Dialog open={!!request} onOpenChange={(open) => {
      if (!open) {
        setRequest(null);
        setFeedback('');
        setError(null);
        currentRequestIdRef.current = null;
      }
    }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            AI Needs Your Input
          </DialogTitle>
          <DialogDescription className="sr-only">
            The AI agent is requesting your feedback to continue.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* The AI's question */}
          <div className="rounded-lg bg-muted p-4">
            <p className="text-sm whitespace-pre-wrap">{request.message}</p>
          </div>

          {/* Project directory context */}
          {request.project_directory && (
            <div className="text-xs text-muted-foreground">
              <span className="font-medium">Project:</span>{' '}
              <code className="bg-muted px-1 rounded">{request.project_directory}</code>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {/* Options buttons if available */}
          {request.options && request.options.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Choose an option:</p>
              <div className="flex flex-wrap gap-2">
                {request.options.map((option, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    onClick={() => handleOptionClick(option)}
                    disabled={isSubmitting}
                    className="flex-1 min-w-[100px]"
                  >
                    {option}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            /* Free-form text input */
            <div className="space-y-2">
              <Textarea
                value={feedback}
                onChange={(e) => {
                  setFeedback(e.target.value);
                  setError(null); // Clear error on input
                }}
                placeholder="Type your feedback..."
                className="min-h-[100px]"
                disabled={isSubmitting}
              />
              <Button
                onClick={() => submitFeedback()}
                disabled={isSubmitting}
                className="w-full"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Send Feedback
                  </>
                )}
              </Button>
            </div>
          )}
        </div>

        <DialogFooter className="sm:justify-between items-center">
          {/* Connection status */}
          <div className="flex items-center gap-2">
            <Badge
              variant={isConnected ? 'default' : 'secondary'}
              className="text-xs"
            >
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>

          {/* Countdown timer */}
          {countdown !== null && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span
                className={
                  countdown < 60 ? 'text-destructive font-mono' : 'font-mono'
                }
              >
                {formatCountdown(countdown)}
              </span>
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
