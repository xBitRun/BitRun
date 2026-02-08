/**
 * Tests for utility functions
 */

import { cn } from "@/lib/utils";

describe("cn", () => {
  it("should merge class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("should handle conditional classes via clsx syntax", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });

  it("should merge conflicting Tailwind classes (last wins)", () => {
    // twMerge deduplicates Tailwind utilities
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
  });

  it("should handle undefined and null inputs", () => {
    expect(cn("base", undefined, null, "end")).toBe("base end");
  });

  it("should return empty string for no inputs", () => {
    expect(cn()).toBe("");
  });
});
