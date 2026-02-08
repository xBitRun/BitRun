/**
 * Conditional Logger
 *
 * Only logs in development mode or when debug is explicitly enabled.
 */

const isDev = process.env.NODE_ENV === 'development';
const isDebug = process.env.NEXT_PUBLIC_DEBUG === 'true';

export const logger = {
  debug: (...args: unknown[]) => {
    if (isDev || isDebug) {
      console.log(...args);
    }
  },

  info: (...args: unknown[]) => {
    if (isDev || isDebug) {
      console.info(...args);
    }
  },

  warn: (...args: unknown[]) => {
    console.warn(...args);
  },

  error: (...args: unknown[]) => {
    console.error(...args);
  },
};

// Helper to extract meaningful error info
const formatError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object') {
    // Handle objects with message property
    if ('message' in error && typeof error.message === 'string') {
      return error.message;
    }
    // Try to stringify, but avoid empty objects
    const str = JSON.stringify(error);
    if (str && str !== '{}') {
      return str;
    }
  }
  return 'Unknown error';
};

// WebSocket-specific logger
export const wsLogger = {
  connected: () => logger.debug('[WS] Connected'),
  disconnected: (code?: number, reason?: string) => logger.debug('[WS] Disconnected:', code, reason),
  reconnecting: (attempt: number, max: number) => logger.debug(`[WS] Reconnecting (${attempt}/${max})...`),
  subscribed: (channel: string) => logger.debug(`[WS] Subscribed to ${channel}`),
  unsubscribed: (channel: string) => logger.debug(`[WS] Unsubscribed from ${channel}`),
  message: (type: string, data?: unknown) => logger.debug(`[WS] ${type}:`, data),
  error: (error: unknown) => logger.error('[WS] Error:', formatError(error)),
  parseError: (error: unknown) => logger.error('[WS] Parse error:', formatError(error)),
};
