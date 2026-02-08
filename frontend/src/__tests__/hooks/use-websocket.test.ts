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
  useAppStore: () => ({
    setWsConnected: jest.fn(),
    addNotification: jest.fn(),
  }),
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
});
