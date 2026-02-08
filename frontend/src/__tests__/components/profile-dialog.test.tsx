/**
 * Tests for ProfileDialog component
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock auth store
const mockUser = {
  id: "test-user-id",
  email: "test@example.com",
  name: "Test User",
};

jest.mock("@/stores/auth-store", () => ({
  useAuthStore: () => ({
    user: mockUser,
    checkAuth: jest.fn().mockResolvedValue(undefined),
  }),
}));

// Mock API
jest.mock("@/lib/api", () => ({
  authApi: {
    updateProfile: jest.fn().mockResolvedValue({}),
    changePassword: jest.fn().mockResolvedValue({}),
  },
}));

import { ProfileDialog } from "@/components/dialogs/profile-dialog";

describe("ProfileDialog", () => {
  const defaultProps = {
    open: true,
    onOpenChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render dialog when open", () => {
    render(<ProfileDialog {...defaultProps} />);

    expect(screen.getByText("title")).toBeInTheDocument();
    expect(screen.getByText("description")).toBeInTheDocument();
  });

  it("should display user profile fields", () => {
    render(<ProfileDialog {...defaultProps} />);

    expect(screen.getByDisplayValue("Test User")).toBeInTheDocument();
    expect(screen.getByDisplayValue("test@example.com")).toBeInTheDocument();
  });

  it("should have email field disabled", () => {
    render(<ProfileDialog {...defaultProps} />);

    const emailInput = screen.getByDisplayValue("test@example.com");
    expect(emailInput).toBeDisabled();
  });

  it("should show change password button", () => {
    render(<ProfileDialog {...defaultProps} />);

    expect(screen.getByText("changePassword")).toBeInTheDocument();
  });

  it("should show password form when change password is clicked", async () => {
    const user = userEvent.setup();
    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    expect(screen.getByText("currentPassword")).toBeInTheDocument();
    expect(screen.getByText("newPassword")).toBeInTheDocument();
    expect(screen.getByText("confirmPassword")).toBeInTheDocument();
  });
});
