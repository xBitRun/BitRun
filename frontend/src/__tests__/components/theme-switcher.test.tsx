/**
 * Tests for ThemeSwitcher component
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Polyfill for PointerEvent (needed for Radix UI DropdownMenu)
class MockPointerEvent extends Event {
  button: number;
  ctrlKey: boolean;
  pointerType: string;
  constructor(type: string, props: PointerEventInit) {
    super(type, props);
    this.button = props.button ?? 0;
    this.ctrlKey = props.ctrlKey ?? false;
    this.pointerType = props.pointerType ?? "mouse";
  }
}
// @ts-expect-error - polyfill
global.PointerEvent = MockPointerEvent;

// Override next-themes mock with a controllable setTheme
const mockSetTheme = jest.fn();
jest.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "light",
    setTheme: mockSetTheme,
    themes: ["light", "dark", "system"],
    resolvedTheme: "light",
    systemTheme: "light",
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

import { ThemeSwitcher } from "@/components/layout/theme-switcher";

describe("ThemeSwitcher", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render the trigger button", () => {
    render(<ThemeSwitcher />);

    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
  });

  it("should open dropdown with theme options on click", async () => {
    const user = userEvent.setup();
    render(<ThemeSwitcher />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      // useTranslations mock returns the key itself
      expect(screen.getByText("light")).toBeInTheDocument();
      expect(screen.getByText("dark")).toBeInTheDocument();
      expect(screen.getByText("system")).toBeInTheDocument();
    });
  });

  it("should call setTheme with 'dark' when dark option is clicked", async () => {
    const user = userEvent.setup();
    render(<ThemeSwitcher />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("dark")).toBeInTheDocument();
    });

    await user.click(screen.getByText("dark"));

    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("should call setTheme with 'light' when light option is clicked", async () => {
    const user = userEvent.setup();
    render(<ThemeSwitcher />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("light")).toBeInTheDocument();
    });

    await user.click(screen.getByText("light"));

    expect(mockSetTheme).toHaveBeenCalledWith("light");
  });

  it("should call setTheme with 'system' when system option is clicked", async () => {
    const user = userEvent.setup();
    render(<ThemeSwitcher />);

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByText("system")).toBeInTheDocument();
    });

    await user.click(screen.getByText("system"));

    expect(mockSetTheme).toHaveBeenCalledWith("system");
  });
});
