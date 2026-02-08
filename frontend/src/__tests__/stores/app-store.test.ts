/**
 * App Store Tests
 *
 * Tests for the Zustand app store.
 */

import { act } from "@testing-library/react";
import { useAppStore } from "@/stores/app-store";

// Mock crypto.randomUUID
const mockUUID = "test-uuid-12345";
Object.defineProperty(global, "crypto", {
  value: {
    randomUUID: jest.fn(() => mockUUID),
  },
});

describe("App Store", () => {
  beforeEach(() => {
    // Reset store state before each test
    act(() => {
      useAppStore.setState({
        sidebarCollapsed: false,
        theme: "dark",
        notifications: [],
        wsConnected: false,
      });
    });
    jest.clearAllMocks();
  });

  describe("initial state", () => {
    it("should have correct default values", () => {
      const state = useAppStore.getState();

      expect(state.sidebarCollapsed).toBe(false);
      expect(state.theme).toBe("dark");
      expect(state.notifications).toEqual([]);
      expect(state.wsConnected).toBe(false);
    });
  });

  describe("sidebar", () => {
    it("should toggle sidebar", () => {
      act(() => {
        useAppStore.getState().toggleSidebar();
      });

      expect(useAppStore.getState().sidebarCollapsed).toBe(true);

      act(() => {
        useAppStore.getState().toggleSidebar();
      });

      expect(useAppStore.getState().sidebarCollapsed).toBe(false);
    });

    it("should set sidebar collapsed state", () => {
      act(() => {
        useAppStore.getState().setSidebarCollapsed(true);
      });

      expect(useAppStore.getState().sidebarCollapsed).toBe(true);

      act(() => {
        useAppStore.getState().setSidebarCollapsed(false);
      });

      expect(useAppStore.getState().sidebarCollapsed).toBe(false);
    });
  });

  describe("theme", () => {
    it("should set theme to light", () => {
      act(() => {
        useAppStore.getState().setTheme("light");
      });

      expect(useAppStore.getState().theme).toBe("light");
    });

    it("should set theme to dark", () => {
      // First set to light
      act(() => {
        useAppStore.getState().setTheme("light");
      });

      // Then back to dark
      act(() => {
        useAppStore.getState().setTheme("dark");
      });

      expect(useAppStore.getState().theme).toBe("dark");
    });
  });

  describe("notifications", () => {
    it("should add notification", () => {
      const mockDate = new Date("2024-01-01T00:00:00Z");
      jest.spyOn(global, "Date").mockImplementation(() => mockDate);

      act(() => {
        useAppStore.getState().addNotification({
          type: "info",
          title: "Test notification",
          message: "Test message",
        });
      });

      const state = useAppStore.getState();
      expect(state.notifications.length).toBe(1);
      expect(state.notifications[0]).toEqual({
        id: mockUUID,
        type: "info",
        title: "Test notification",
        message: "Test message",
        timestamp: mockDate,
      });

      jest.restoreAllMocks();
    });

    it("should add notification without message", () => {
      act(() => {
        useAppStore.getState().addNotification({
          type: "success",
          title: "Success!",
        });
      });

      const state = useAppStore.getState();
      expect(state.notifications[0].title).toBe("Success!");
      expect(state.notifications[0].message).toBeUndefined();
    });

    it("should add multiple notifications", () => {
      act(() => {
        useAppStore.getState().addNotification({
          type: "info",
          title: "First",
        });
        useAppStore.getState().addNotification({
          type: "warning",
          title: "Second",
        });
        useAppStore.getState().addNotification({
          type: "error",
          title: "Third",
        });
      });

      expect(useAppStore.getState().notifications.length).toBe(3);
    });

    it("should remove notification by id", () => {
      // Add notifications
      act(() => {
        useAppStore.setState({
          notifications: [
            {
              id: "notification-1",
              type: "info",
              title: "First",
              timestamp: new Date(),
            },
            {
              id: "notification-2",
              type: "warning",
              title: "Second",
              timestamp: new Date(),
            },
          ],
        });
      });

      act(() => {
        useAppStore.getState().removeNotification("notification-1");
      });

      const state = useAppStore.getState();
      expect(state.notifications.length).toBe(1);
      expect(state.notifications[0].id).toBe("notification-2");
    });

    it("should not fail when removing non-existent notification", () => {
      act(() => {
        useAppStore.getState().addNotification({
          type: "info",
          title: "Test",
        });
      });

      act(() => {
        useAppStore.getState().removeNotification("non-existent-id");
      });

      expect(useAppStore.getState().notifications.length).toBe(1);
    });

    it("should clear all notifications", () => {
      act(() => {
        useAppStore.getState().addNotification({ type: "info", title: "1" });
        useAppStore.getState().addNotification({ type: "info", title: "2" });
        useAppStore.getState().addNotification({ type: "info", title: "3" });
      });

      expect(useAppStore.getState().notifications.length).toBe(3);

      act(() => {
        useAppStore.getState().clearNotifications();
      });

      expect(useAppStore.getState().notifications).toEqual([]);
    });

    it("should handle all notification types", () => {
      const types: Array<"info" | "success" | "warning" | "error"> = [
        "info",
        "success",
        "warning",
        "error",
      ];

      types.forEach((type) => {
        act(() => {
          useAppStore.getState().addNotification({
            type,
            title: `${type} notification`,
          });
        });
      });

      const notifications = useAppStore.getState().notifications;
      expect(notifications.length).toBe(4);
      expect(notifications[0].type).toBe("info");
      expect(notifications[1].type).toBe("success");
      expect(notifications[2].type).toBe("warning");
      expect(notifications[3].type).toBe("error");
    });
  });

  describe("WebSocket", () => {
    it("should set WebSocket connected state", () => {
      expect(useAppStore.getState().wsConnected).toBe(false);

      act(() => {
        useAppStore.getState().setWsConnected(true);
      });

      expect(useAppStore.getState().wsConnected).toBe(true);
    });

    it("should set WebSocket disconnected state", () => {
      // First connect
      act(() => {
        useAppStore.getState().setWsConnected(true);
      });

      // Then disconnect
      act(() => {
        useAppStore.getState().setWsConnected(false);
      });

      expect(useAppStore.getState().wsConnected).toBe(false);
    });
  });

  describe("state isolation", () => {
    it("should not affect other state when updating one property", () => {
      // Set initial state
      act(() => {
        useAppStore.setState({
          sidebarCollapsed: true,
          theme: "light",
          notifications: [
            { id: "1", type: "info", title: "Test", timestamp: new Date() },
          ],
          wsConnected: true,
        });
      });

      // Change only theme
      act(() => {
        useAppStore.getState().setTheme("dark");
      });

      const state = useAppStore.getState();
      expect(state.sidebarCollapsed).toBe(true);
      expect(state.theme).toBe("dark");
      expect(state.notifications.length).toBe(1);
      expect(state.wsConnected).toBe(true);
    });
  });
});
