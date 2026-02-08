/**
 * Tests for useIsMobile hook
 */

import { renderHook, act } from "@testing-library/react";
import { useIsMobile } from "@/hooks/use-mobile";

// Helper to mock matchMedia and innerWidth
function mockWindow(width: number) {
  Object.defineProperty(window, "innerWidth", {
    writable: true,
    configurable: true,
    value: width,
  });

  const listeners: Array<(e: { matches: boolean }) => void> = [];

  const mql = {
    matches: width < 768,
    media: `(max-width: 767px)`,
    onchange: null as (() => void) | null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(
      (_event: string, handler: (e: { matches: boolean }) => void) => {
        listeners.push(handler);
      }
    ),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  };

  window.matchMedia = jest.fn().mockReturnValue(mql);

  return { mql, listeners };
}

describe("useIsMobile", () => {
  const originalInnerWidth = window.innerWidth;

  afterEach(() => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    });
  });

  it("should return false on desktop width", () => {
    mockWindow(1024);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);
  });

  it("should return true on mobile width", () => {
    mockWindow(375);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(true);
  });

  it("should return false at exactly 768px", () => {
    mockWindow(768);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);
  });

  it("should return true at 767px", () => {
    mockWindow(767);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(true);
  });

  it("should respond to media query change events", () => {
    const { listeners } = mockWindow(1024);

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);

    // Simulate resize to mobile
    act(() => {
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        configurable: true,
        value: 500,
      });
      listeners.forEach((fn) => fn({ matches: true }));
    });

    expect(result.current).toBe(true);
  });

  it("should clean up event listener on unmount", () => {
    const { mql } = mockWindow(1024);

    const { unmount } = renderHook(() => useIsMobile());

    unmount();

    expect(mql.removeEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function)
    );
  });
});
