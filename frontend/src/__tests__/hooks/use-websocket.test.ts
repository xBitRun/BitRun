/**
 * Tests for useWebSocket hook
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { useWebSocket } from "@/hooks/use-websocket";

// Mock dependencies
jest.mock("@/lib/api", () => ({
  TokenManager: {
    getAccessToken: jest.fn(() => "mock-token"),
  },
}));

jest.mock("@/stores", () => ({
  useAppStore: jest.fn(() => ({
    setWsConnected: jest.fn(),
    addNotification: jest.fn(),
  })),
}));

jest.mock("@/lib/logger", () => ({
  wsLogger: {
    connected: jest.fn(),
    disconnected: jest.fn(),
    error: jest.fn(),
    message: jest.fn(),
    subscribed: jest.fn(),
    unsubscribed: jest.fn(),
    reconnecting: jest.fn(),
    parseError: jest.fn(),
  },
}));

// Mock WebSocket
class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  readonly CONNECTING = MockWebSocket.CONNECTING;
  readonly OPEN = MockWebSocket.OPEN;
  readonly CLOSING = MockWebSocket.CLOSING;
  readonly CLOSED = MockWebSocket.CLOSED;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  url: string;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event("open"));
    }, 10);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code: 1000, reason: "Normal closure" } as CloseEvent);
  }

  // Helper methods for testing
  simulateMessage(data: Record<string, unknown>) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }

  simulateError() {
    this.onerror?.(new Event("error"));
  }

  simulateClose(code = 1000, reason = "") {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code, reason } as CloseEvent);
  }
}

// Store instances for test access
let mockWsInstances: MockWebSocket[] = [];

// Setup global WebSocket mock
const OriginalWebSocket = global.WebSocket;

beforeAll(() => {
  // @ts-expect-error - Mocking WebSocket
  global.WebSocket = class extends MockWebSocket {
    constructor(url: string) {
      super(url);
      mockWsInstances.push(this);
    }
  };
});

afterAll(() => {
  global.WebSocket = OriginalWebSocket;
});

beforeEach(() => {
  mockWsInstances = [];
  jest.useFakeTimers();
  jest.clearAllMocks();
});

afterEach(() => {
  jest.useRealTimers();
  jest.clearAllMocks();
});

describe("useWebSocket", () => {
  describe("connection", () => {
    it("should auto-connect by default", async () => {
      const { result } = renderHook(() => useWebSocket());

      // Advance timers to allow connection
      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBe(1);
      expect(result.current.isConnected).toBe(true);
    });

    it("should not auto-connect when autoConnect is false", async () => {
      const { result } = renderHook(() =>
        useWebSocket({ autoConnect: false })
      );

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBe(0);
      expect(result.current.isConnected).toBe(false);
    });

    it("should connect manually when connect is called", async () => {
      const { result } = renderHook(() =>
        useWebSocket({ autoConnect: false })
      );

      expect(result.current.isConnected).toBe(false);

      await act(async () => {
        result.current.connect();
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBe(1);
      expect(result.current.isConnected).toBe(true);
    });

    it("should disconnect when disconnect is called", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(result.current.isConnected).toBe(true);

      act(() => {
        result.current.disconnect();
      });

      expect(result.current.isConnected).toBe(false);
    });

    it("should include token in URL when available", async () => {
      renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances[0].url).toContain("token=mock-token");
    });
  });

  describe("subscription", () => {
    it("should subscribe to channel", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        result.current.subscribe("strategy:123");
      });

      expect(result.current.subscribedChannels).toContain("strategy:123");

      const lastMessage = mockWsInstances[0].sentMessages.pop();
      expect(JSON.parse(lastMessage!)).toEqual({
        type: "subscribe",
        channel: "strategy:123",
      });
    });

    it("should unsubscribe from channel", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        result.current.subscribe("strategy:123");
      });

      expect(result.current.subscribedChannels).toContain("strategy:123");

      act(() => {
        result.current.unsubscribe("strategy:123");
      });

      expect(result.current.subscribedChannels).not.toContain("strategy:123");

      const lastMessage = mockWsInstances[0].sentMessages.pop();
      expect(JSON.parse(lastMessage!)).toEqual({
        type: "unsubscribe",
        channel: "strategy:123",
      });
    });

    it("should track multiple subscriptions", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        result.current.subscribe("strategy:1");
        result.current.subscribe("strategy:2");
        result.current.subscribe("account:1");
      });

      expect(result.current.subscribedChannels).toContain("strategy:1");
      expect(result.current.subscribedChannels).toContain("strategy:2");
      expect(result.current.subscribedChannels).toContain("account:1");
      expect(result.current.subscribedChannels.length).toBe(3);
    });
  });

  describe("message handling", () => {
    it("should call onDecision callback for decision messages", async () => {
      const onDecision = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onDecision }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "decision",
          data: { strategyId: "123", action: "buy" },
        });
      });

      expect(onDecision).toHaveBeenCalledWith({
        strategyId: "123",
        action: "buy",
      });
    });

    it("should call onPositionUpdate callback", async () => {
      const onPositionUpdate = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onPositionUpdate }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "position_update",
          data: { symbol: "BTC", pnl: 100 },
        });
      });

      expect(onPositionUpdate).toHaveBeenCalledWith({
        symbol: "BTC",
        pnl: 100,
      });
    });

    it("should call onAccountUpdate callback", async () => {
      const onAccountUpdate = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onAccountUpdate }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "account_update",
          data: { accountId: "acc-1", balance: 1000 },
        });
      });

      expect(onAccountUpdate).toHaveBeenCalledWith({
        accountId: "acc-1",
        balance: 1000,
      });
    });

    it("should call onStrategyStatus callback", async () => {
      const onStrategyStatus = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onStrategyStatus }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "strategy_status",
          data: { strategyId: "123", status: "active" },
        });
      });

      expect(onStrategyStatus).toHaveBeenCalledWith({
        strategyId: "123",
        status: "active",
      });
    });

    it("should call onNotification callback", async () => {
      const onNotification = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onNotification }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "notification",
          data: { title: "Alert", message: "Price alert triggered" },
        });
      });

      expect(onNotification).toHaveBeenCalledWith({
        title: "Alert",
        message: "Price alert triggered",
      });
    });

    it("should call onError callback for error messages", async () => {
      const onError = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onError }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "error",
          data: { message: "Something went wrong" },
        });
      });

      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({ message: "Something went wrong" })
      );
    });
  });

  describe("send", () => {
    it("should send messages when connected", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        result.current.send({ type: "ping" });
      });

      const lastMessage = mockWsInstances[0].sentMessages.pop();
      expect(JSON.parse(lastMessage!)).toEqual({ type: "ping" });
    });

    it("should not throw when sending while disconnected", async () => {
      const { result } = renderHook(() =>
        useWebSocket({ autoConnect: false })
      );

      // Should not throw
      act(() => {
        result.current.send({ type: "ping" });
      });

      expect(mockWsInstances.length).toBe(0);
    });
  });

  describe("error handling", () => {
    it("should call onError callback on connection error", async () => {
      const onError = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onError }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateError();
      });

      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({ message: "WebSocket connection error" })
      );
    });
  });

  describe("cleanup", () => {
    it("should disconnect on unmount", async () => {
      const { result, unmount } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(result.current.isConnected).toBe(true);

      unmount();

      // The disconnect should have been called
      expect(mockWsInstances[0].readyState).toBe(MockWebSocket.CLOSED);
    });
  });

  describe("connection edge cases", () => {
    it("should not connect if already connecting", async () => {
      const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

      // Start first connection
      act(() => {
        result.current.connect();
      });

      const firstInstanceCount = mockWsInstances.length;

      // Try to connect again immediately
      act(() => {
        result.current.connect();
      });

      // Should not create another instance
      expect(mockWsInstances.length).toBe(firstInstanceCount);
    });

    it("should not connect if already connected", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(result.current.isConnected).toBe(true);
      const instanceCount = mockWsInstances.length;

      // Try to connect again
      act(() => {
        result.current.connect();
      });

      // Should not create another instance
      expect(mockWsInstances.length).toBe(instanceCount);
    });

    it("should close existing connection before reconnecting", async () => {
      const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

      // Connect first time
      act(() => {
        result.current.connect();
      });

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      const firstInstance = mockWsInstances[0];
      expect(firstInstance.readyState).toBe(MockWebSocket.OPEN);

      // Disconnect and reconnect
      act(() => {
        firstInstance.readyState = MockWebSocket.CONNECTING; // Simulate bad state
        result.current.connect();
      });

      // First instance should be closed
      expect(firstInstance.readyState).toBe(MockWebSocket.CLOSED);
    });

    it("should handle connection when component unmounted", async () => {
      const { result, unmount } = renderHook(() => useWebSocket({ autoConnect: false }));

      act(() => {
        result.current.connect();
      });

      // Unmount before connection completes
      unmount();

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      // Connection should be closed if it opened after unmount
      if (mockWsInstances.length > 0) {
        expect(mockWsInstances[0].readyState).toBe(MockWebSocket.CLOSED);
      }
    });
  });

  describe("ping and heartbeat", () => {
    it("should send ping messages periodically", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(result.current.isConnected).toBe(true);

      // Advance time to trigger ping
      await act(async () => {
        jest.advanceTimersByTime(30000);
      });

      const pingMessages = mockWsInstances[0].sentMessages.filter((msg) => {
        const parsed = JSON.parse(msg);
        return parsed.type === "ping";
      });

      expect(pingMessages.length).toBeGreaterThan(0);
    });

    it("should handle pong messages", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      // Should not throw or call any callbacks
      act(() => {
        mockWsInstances[0].simulateMessage({ type: "pong" });
      });

      // No assertions needed, just should not crash
    });
  });

  describe("resubscription on reconnect", () => {
    it("should resubscribe to channels on reconnect", async () => {
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      // Subscribe to channels
      act(() => {
        result.current.subscribe("strategy:1");
        result.current.subscribe("strategy:2");
      });

      // Clear sent messages
      mockWsInstances[0].sentMessages = [];

      // Simulate disconnect and reconnect
      act(() => {
        mockWsInstances[0].simulateClose();
      });

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      // Create new connection
      act(() => {
        result.current.connect();
      });

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      // Should resubscribe to both channels
      const subscribeMessages = mockWsInstances
        .flatMap((ws) => ws.sentMessages)
        .filter((msg) => {
          const parsed = JSON.parse(msg);
          return parsed.type === "subscribe";
        });

      expect(subscribeMessages.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe("message parsing errors", () => {
    it("should handle invalid JSON messages", async () => {
      const { wsLogger } = require("@/lib/logger");
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        // Simulate invalid JSON
        mockWsInstances[0].onmessage?.({ data: "invalid json" } as MessageEvent);
      });

      expect(wsLogger.parseError).toHaveBeenCalled();
    });
  });

  describe("reconnection logic", () => {
    it("should attempt reconnection on close", async () => {
      const { wsLogger } = require("@/lib/logger");
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(result.current.isConnected).toBe(true);

      // Simulate unexpected close
      act(() => {
        mockWsInstances[0].simulateClose(1006, "Abnormal closure");
      });

      expect(result.current.isConnected).toBe(false);

      // Advance time for reconnection
      await act(async () => {
        jest.advanceTimersByTime(3000);
      });

      expect(wsLogger.reconnecting).toHaveBeenCalled();
      expect(mockWsInstances.length).toBeGreaterThan(1);
    });

    it("should stop reconnecting after max attempts", async () => {
      const { wsLogger } = require("@/lib/logger");
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(result.current.isConnected).toBe(true);

      // Reset call count after initial connection
      wsLogger.reconnecting.mockClear();

      // Simulate multiple disconnections
      for (let i = 0; i < 5; i++) {
        act(() => {
          if (mockWsInstances.length > 0) {
            const lastInstance = mockWsInstances[mockWsInstances.length - 1];
            if (lastInstance.readyState === MockWebSocket.OPEN) {
              lastInstance.simulateClose();
            }
          }
        });

        await act(async () => {
          jest.advanceTimersByTime(3000);
        });
      }

      // Should have attempted reconnection up to MAX_RECONNECT_ATTEMPTS (5 times)
      expect(wsLogger.reconnecting).toHaveBeenCalledTimes(5);
    });

    it("should not reconnect if component unmounted", async () => {
      const { result, unmount } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      unmount();

      // Simulate close after unmount
      act(() => {
        mockWsInstances[0].simulateClose();
      });

      const instanceCount = mockWsInstances.length;

      await act(async () => {
        jest.advanceTimersByTime(3000);
      });

      // Should not create new connection
      expect(mockWsInstances.length).toBe(instanceCount);
    });
  });

  describe("connection error handling", () => {
    it("should handle WebSocket constructor error", async () => {
      const onError = jest.fn();
      const OriginalWebSocket = global.WebSocket;
      const originalInstances = [...mockWsInstances];

      // Mock WebSocket to throw error
      // @ts-expect-error - Mocking WebSocket
      global.WebSocket = jest.fn(() => {
        throw new Error("Connection failed");
      });

      renderHook(() => useWebSocket({ onError, autoConnect: true }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(onError).toHaveBeenCalled();

      global.WebSocket = OriginalWebSocket;
      mockWsInstances = originalInstances;
    });
  });

  describe("message type handling", () => {
    it("should handle subscribed message", async () => {
      const { wsLogger } = require("@/lib/logger");
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBeGreaterThan(0);

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "subscribed",
          channel: "strategy:123",
        });
      });

      expect(wsLogger.subscribed).toHaveBeenCalledWith("strategy:123");
    });

    it("should handle unsubscribed message", async () => {
      const { wsLogger } = require("@/lib/logger");
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBeGreaterThan(0);

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "unsubscribed",
          channel: "strategy:123",
        });
      });

      expect(wsLogger.unsubscribed).toHaveBeenCalledWith("strategy:123");
    });

    it("should handle notification with addNotification", async () => {
      const onNotification = jest.fn();
      const { useAppStore } = require("@/stores");
      const mockAddNotification = jest.fn();
      const mockSetWsConnected = jest.fn();

      // Override the mock for this test
      useAppStore.mockReturnValue({
        setWsConnected: mockSetWsConnected,
        addNotification: mockAddNotification,
      });

      const { result } = renderHook(() => useWebSocket({ onNotification }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBeGreaterThan(0);

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "notification",
          data: {
            level: "success",
            title: "Success",
            message: "Operation completed",
          },
        });
      });

      expect(onNotification).toHaveBeenCalledWith({
        level: "success",
        title: "Success",
        message: "Operation completed",
      });
      expect(mockAddNotification).toHaveBeenCalledWith({
        type: "success",
        title: "Success",
        message: "Operation completed",
      });
    });

    it("should handle notification with default values", async () => {
      const onNotification = jest.fn();
      const { useAppStore } = require("@/stores");
      const mockAddNotification = jest.fn();
      const mockSetWsConnected = jest.fn();

      // Override the mock for this test
      useAppStore.mockReturnValue({
        setWsConnected: mockSetWsConnected,
        addNotification: mockAddNotification,
      });

      const { result } = renderHook(() => useWebSocket({ onNotification }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBeGreaterThan(0);

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "notification",
          data: {},
        });
      });

      expect(onNotification).toHaveBeenCalledWith({});
      expect(mockAddNotification).toHaveBeenCalledWith({
        type: "info",
        title: "Notification",
        message: undefined,
      });
    });

    it("should handle unknown message types", async () => {
      const { wsLogger } = require("@/lib/logger");
      const { result } = renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBeGreaterThan(0);

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "unknown_type",
          data: { test: "data" },
        });
      });

      expect(wsLogger.message).toHaveBeenCalledWith("Unknown message", expect.any(Object));
    });
  });

  describe("subscription edge cases", () => {
    it("should not send subscribe when not connected", () => {
      const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

      act(() => {
        result.current.subscribe("strategy:123");
      });

      expect(result.current.subscribedChannels).toContain("strategy:123");
      expect(mockWsInstances.length).toBe(0);
    });

    it("should not send unsubscribe when not connected", () => {
      const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

      act(() => {
        result.current.subscribe("strategy:123");
        result.current.unsubscribe("strategy:123");
      });

      expect(result.current.subscribedChannels).not.toContain("strategy:123");
      expect(mockWsInstances.length).toBe(0);
    });
  });

  describe("send edge cases", () => {
    it("should not send when not connected", () => {
      const { result } = renderHook(() => useWebSocket({ autoConnect: false }));

      act(() => {
        result.current.send({ type: "ping" });
      });

      expect(mockWsInstances.length).toBe(0);
    });
  });

  describe("notification handling", () => {
    it("should handle notification without data", async () => {
      const onNotification = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onNotification }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "notification",
        });
      });

      expect(onNotification).toHaveBeenCalledWith({});
    });

    it("should handle error message without data", async () => {
      const onError = jest.fn();
      const { result } = renderHook(() => useWebSocket({ onError }));

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        mockWsInstances[0].simulateMessage({
          type: "error",
        });
      });

      expect(onError).toHaveBeenCalledWith(expect.any(Error));
    });
  });

  describe("URL construction", () => {
    it("should use default URL when token not available", async () => {
      const { TokenManager } = require("@/lib/api");
      TokenManager.getAccessToken.mockReturnValue(null);

      renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBeGreaterThan(0);
      expect(mockWsInstances[0].url).not.toContain("token=");
    });

    it("should use custom WS URL from env", async () => {
      const originalEnv = process.env.NEXT_PUBLIC_WS_URL;
      process.env.NEXT_PUBLIC_WS_URL = "ws://custom:9000/ws";

      renderHook(() => useWebSocket());

      await act(async () => {
        jest.advanceTimersByTime(50);
      });

      expect(mockWsInstances.length).toBeGreaterThan(0);
      expect(mockWsInstances[0].url).toContain("custom:9000");

      if (originalEnv) {
        process.env.NEXT_PUBLIC_WS_URL = originalEnv;
      } else {
        delete process.env.NEXT_PUBLIC_WS_URL;
      }
    });
  });
});
