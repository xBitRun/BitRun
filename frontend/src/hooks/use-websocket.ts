/**
 * WebSocket Hook
 *
 * Manages WebSocket connection for real-time updates.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { TokenManager } from '@/lib/api';
import { useAppStore } from '@/stores';
import { wsLogger } from '@/lib/logger';

// WebSocket configuration
// API v1 is the current stable version
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;
const PING_INTERVAL = 30000;

// Message types
export type WSMessageType =
  | 'subscribe'
  | 'unsubscribe'
  | 'ping'
  | 'pong'
  | 'subscribed'
  | 'unsubscribed'
  | 'decision'
  | 'position_update'
  | 'account_update'
  | 'strategy_status'
  | 'notification'
  | 'error';

export interface WSMessage {
  type: WSMessageType;
  channel?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

export interface UseWebSocketOptions {
  autoConnect?: boolean;
  onDecision?: (data: Record<string, unknown>) => void;
  onPositionUpdate?: (data: Record<string, unknown>) => void;
  onAccountUpdate?: (data: Record<string, unknown>) => void;
  onStrategyStatus?: (data: Record<string, unknown>) => void;
  onNotification?: (data: Record<string, unknown>) => void;
  onError?: (error: Error) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    autoConnect = true,
    onDecision,
    onPositionUpdate,
    onAccountUpdate,
    onStrategyStatus,
    onNotification,
    onError,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isConnectingRef = useRef(false);
  const isMountedRef = useRef(true);

  const [isConnected, setIsConnected] = useState(false);
  const [subscribedChannels, setSubscribedChannels] = useState<Set<string>>(new Set());

  // Use ref to access current subscribedChannels without adding to dependencies
  const subscribedChannelsRef = useRef<Set<string>>(subscribedChannels);
  subscribedChannelsRef.current = subscribedChannels;

  const { setWsConnected, addNotification } = useAppStore();

  // Clean up timers
  const clearTimers = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // Ref to avoid circular dependency between connect and handleMessage
  const handleMessageRef = useRef<(message: WSMessage) => void>(() => {});

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current) {
      wsLogger.message('Connection already in progress, skipping');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Close any existing connection that might be in a bad state
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
      wsRef.current = null;
    }

    isConnectingRef.current = true;

    // Get auth token
    const token = TokenManager.getAccessToken();
    const url = token ? `${WS_BASE_URL}?token=${token}` : WS_BASE_URL;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) {
          ws.close();
          return;
        }

        isConnectingRef.current = false;
        wsLogger.connected();
        setIsConnected(true);
        setWsConnected(true);
        reconnectAttemptsRef.current = 0;

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, PING_INTERVAL);

        // Resubscribe to channels using ref to get current value
        subscribedChannelsRef.current.forEach((channel) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'subscribe', channel }));
          }
        });
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          handleMessageRef.current(message);
        } catch (err) {
          wsLogger.parseError(err);
        }
      };

      ws.onerror = () => {
        // WebSocket error events don't expose error details for security reasons
        // The actual error info will come through the onclose event
        isConnectingRef.current = false;
        wsLogger.error('Connection error (details unavailable - check network tab)');
        onError?.(new Error('WebSocket connection error'));
      };

      ws.onclose = (event) => {
        isConnectingRef.current = false;
        wsLogger.disconnected(event.code, event.reason);
        setIsConnected(false);
        setWsConnected(false);
        clearTimers();

        // Only attempt reconnect if component is still mounted
        if (isMountedRef.current && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++;
          wsLogger.reconnecting(reconnectAttemptsRef.current, MAX_RECONNECT_ATTEMPTS);
          reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
        }
      };
    } catch (err) {
      isConnectingRef.current = false;
      wsLogger.error(err);
      onError?.(err instanceof Error ? err : new Error('Connection failed'));
    }
  }, [setWsConnected, clearTimers, onError]);

  // Handle incoming messages
  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.type) {
      case 'pong':
        // Heartbeat response, ignore
        break;

      case 'subscribed':
        wsLogger.subscribed(message.channel || '');
        break;

      case 'unsubscribed':
        wsLogger.unsubscribed(message.channel || '');
        break;

      case 'decision':
        wsLogger.message('Decision received', message.data);
        onDecision?.(message.data || {});
        break;

      case 'position_update':
        wsLogger.message('Position update', message.data);
        onPositionUpdate?.(message.data || {});
        break;

      case 'account_update':
        wsLogger.message('Account update', message.data);
        onAccountUpdate?.(message.data || {});
        break;

      case 'strategy_status':
        wsLogger.message('Strategy status', message.data);
        onStrategyStatus?.(message.data || {});
        break;

      case 'notification':
        wsLogger.message('Notification', message.data);
        onNotification?.(message.data || {});

        // Also add to app store
        if (message.data) {
          addNotification({
            type: (message.data.level as 'info' | 'success' | 'warning' | 'error') || 'info',
            title: (message.data.title as string) || 'Notification',
            message: message.data.message as string,
          });
        }
        break;

      case 'error':
        wsLogger.error(message.data);
        onError?.(new Error((message.data?.message as string) || 'Server error'));
        break;

      default:
        wsLogger.message('Unknown message', message);
    }
  }, [onDecision, onPositionUpdate, onAccountUpdate, onStrategyStatus, onNotification, onError, addNotification]);

  handleMessageRef.current = handleMessage;

  // Disconnect
  const disconnect = useCallback(() => {
    clearTimers();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setWsConnected(false);
  }, [clearTimers, setWsConnected]);

  // Subscribe to channel
  const subscribe = useCallback((channel: string) => {
    setSubscribedChannels((prev) => new Set([...prev, channel]));

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', channel }));
    }
  }, []);

  // Unsubscribe from channel
  const unsubscribe = useCallback((channel: string) => {
    setSubscribedChannels((prev) => {
      const next = new Set(prev);
      next.delete(channel);
      return next;
    });

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', channel }));
    }
  }, []);

  // Send raw message
  const send = useCallback((message: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Auto connect on mount
  useEffect(() => {
    isMountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
    // Note: We intentionally exclude `connect` and `disconnect` from deps
    // to prevent reconnection loops. The refs handle the state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]);

  return {
    isConnected,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    send,
    subscribedChannels: Array.from(subscribedChannels),
  };
}
