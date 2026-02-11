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

  it("should update name field", async () => {
    const user = userEvent.setup();
    render(<ProfileDialog {...defaultProps} />);

    const nameInput = screen.getByDisplayValue("Test User");
    await user.clear(nameInput);
    await user.type(nameInput, "New Name");

    expect(nameInput).toHaveValue("New Name");
  });

  it("should save profile changes", async () => {
    const user = userEvent.setup();
    const { authApi } = await import("@/lib/api");
    render(<ProfileDialog {...defaultProps} />);

    const nameInput = screen.getByDisplayValue("Test User");
    await user.clear(nameInput);
    await user.type(nameInput, "Updated Name");

    const saveButton = screen.getByRole("button", { name: /save/i });
    await user.click(saveButton);

    expect(authApi.updateProfile).toHaveBeenCalledWith({ name: "Updated Name" });
  });

  it("should not call API if name hasn't changed", async () => {
    const user = userEvent.setup();
    const { authApi } = await import("@/lib/api");
    render(<ProfileDialog {...defaultProps} />);

    const saveButton = screen.getByRole("button", { name: /save/i });
    await user.click(saveButton);

    expect(authApi.updateProfile).not.toHaveBeenCalled();
    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("should handle save error", async () => {
    const user = userEvent.setup();
    const { authApi } = await import("@/lib/api");
    (authApi.updateProfile as jest.Mock).mockRejectedValue(new Error("Update failed"));

    render(<ProfileDialog {...defaultProps} />);

    const nameInput = screen.getByDisplayValue("Test User");
    await user.clear(nameInput);
    await user.type(nameInput, "New Name");

    const saveButton = screen.getByRole("button", { name: /save/i });
    await user.click(saveButton);

    await screen.findByText("Update failed");
  });

  it("should validate password mismatch", async () => {
    const user = userEvent.setup();
    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    const newPasswordInput = screen.getByLabelText(/newPassword/i);
    const confirmPasswordInput = screen.getByLabelText(/confirmPassword/i);

    await user.type(newPasswordInput, "password123");
    await user.type(confirmPasswordInput, "password456");

    const changeButton = screen.getByRole("button", { name: /change/i });
    await user.click(changeButton);

    expect(screen.getByText("passwordMismatch")).toBeInTheDocument();
  });

  it("should validate password too short", async () => {
    const user = userEvent.setup();
    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    const currentPasswordInput = screen.getByLabelText(/currentPassword/i);
    const newPasswordInput = screen.getByLabelText(/newPassword/i);
    const confirmPasswordInput = screen.getByLabelText(/confirmPassword/i);

    await user.type(currentPasswordInput, "oldpass");
    await user.type(newPasswordInput, "short");
    await user.type(confirmPasswordInput, "short");

    const changeButton = screen.getByRole("button", { name: /change/i });
    await user.click(changeButton);

    expect(screen.getByText("passwordTooShort")).toBeInTheDocument();
  });

  it("should change password successfully", async () => {
    const user = userEvent.setup();
    const { authApi } = await import("@/lib/api");
    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    const currentPasswordInput = screen.getByLabelText(/currentPassword/i);
    const newPasswordInput = screen.getByLabelText(/newPassword/i);
    const confirmPasswordInput = screen.getByLabelText(/confirmPassword/i);

    await user.type(currentPasswordInput, "oldpassword123");
    await user.type(newPasswordInput, "newpassword123");
    await user.type(confirmPasswordInput, "newpassword123");

    const changeButton = screen.getByRole("button", { name: /change/i });
    await user.click(changeButton);

    expect(authApi.changePassword).toHaveBeenCalledWith({
      current_password: "oldpassword123",
      new_password: "newpassword123",
    });
  });

  it("should handle password change error", async () => {
    const user = userEvent.setup();
    const { authApi } = await import("@/lib/api");
    (authApi.changePassword as jest.Mock).mockRejectedValue(new Error("Invalid password"));

    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    const currentPasswordInput = screen.getByLabelText(/currentPassword/i);
    const newPasswordInput = screen.getByLabelText(/newPassword/i);
    const confirmPasswordInput = screen.getByLabelText(/confirmPassword/i);

    await user.type(currentPasswordInput, "wrongpassword");
    await user.type(newPasswordInput, "newpassword123");
    await user.type(confirmPasswordInput, "newpassword123");

    const changeButton = screen.getByRole("button", { name: /change/i });
    await user.click(changeButton);

    await screen.findByText("Invalid password");
  });

  it("should toggle password visibility", async () => {
    const user = userEvent.setup();
    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    const passwordInputs = screen.getAllByLabelText(/password/i);
    const toggleButtons = screen.getAllByRole("button", { name: /eye/i });

    if (toggleButtons.length > 0) {
      await user.click(toggleButtons[0]);
      // Password should be visible
      expect(passwordInputs[0]).toHaveAttribute("type", "text");
    }
  });

  it("should cancel password change", async () => {
    const user = userEvent.setup();
    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    const cancelButton = screen.getByRole("button", { name: /cancel/i });
    await user.click(cancelButton);

    expect(screen.queryByText("currentPassword")).not.toBeInTheDocument();
  });

  it("should reset form when dialog closes", () => {
    const { rerender } = render(<ProfileDialog {...defaultProps} open={true} />);

    expect(screen.getByDisplayValue("Test User")).toBeInTheDocument();

    rerender(<ProfileDialog {...defaultProps} open={false} />);
    rerender(<ProfileDialog {...defaultProps} open={true} />);

    // Form should be reset
    expect(screen.getByDisplayValue("Test User")).toBeInTheDocument();
  });

  it("should update profile when user changes", () => {
    const { useAuthStore } = require("@/stores/auth-store");
    const newUser = {
      id: "new-user-id",
      email: "new@example.com",
      name: "New User",
    };

    (useAuthStore as jest.Mock).mockReturnValue({
      user: newUser,
      checkAuth: jest.fn().mockResolvedValue(undefined),
    });

    const { rerender } = render(<ProfileDialog {...defaultProps} />);

    rerender(<ProfileDialog {...defaultProps} />);

    expect(screen.getByDisplayValue("New User")).toBeInTheDocument();
    expect(screen.getByDisplayValue("new@example.com")).toBeInTheDocument();
  });

  it("should show loading state when saving", async () => {
    const user = userEvent.setup();
    const { authApi } = await import("@/lib/api");
    (authApi.updateProfile as jest.Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(<ProfileDialog {...defaultProps} />);

    const nameInput = screen.getByDisplayValue("Test User");
    await user.clear(nameInput);
    await user.type(nameInput, "New Name");

    const saveButton = screen.getByRole("button", { name: /save/i });
    await user.click(saveButton);

    // Should show loading indicator
    expect(screen.getByRole("button", { name: /save/i })).toBeDisabled();
  });

  it("should show loading state when changing password", async () => {
    const user = userEvent.setup();
    const { authApi } = await import("@/lib/api");
    (authApi.changePassword as jest.Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(<ProfileDialog {...defaultProps} />);

    await user.click(screen.getByText("changePassword"));

    const currentPasswordInput = screen.getByLabelText(/currentPassword/i);
    const newPasswordInput = screen.getByLabelText(/newPassword/i);
    const confirmPasswordInput = screen.getByLabelText(/confirmPassword/i);

    await user.type(currentPasswordInput, "oldpassword123");
    await user.type(newPasswordInput, "newpassword123");
    await user.type(confirmPasswordInput, "newpassword123");

    const changeButton = screen.getByRole("button", { name: /change/i });
    await user.click(changeButton);

    // Should show loading indicator
    expect(changeButton).toBeDisabled();
  });

  it("should close dialog after successful save", async () => {
    const user = userEvent.setup();
    render(<ProfileDialog {...defaultProps} />);

    const nameInput = screen.getByDisplayValue("Test User");
    await user.clear(nameInput);
    await user.type(nameInput, "New Name");

    const saveButton = screen.getByRole("button", { name: /save/i });
    await user.click(saveButton);

    // Wait for success message and auto-close
    await screen.findByText(/success/i);
    // Dialog should close after 1 second
    await new Promise((resolve) => setTimeout(resolve, 1100));
    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("should handle user being null", () => {
    const { useAuthStore } = require("@/stores/auth-store");
    (useAuthStore as jest.Mock).mockReturnValue({
      user: null,
      checkAuth: jest.fn().mockResolvedValue(undefined),
    });

    render(<ProfileDialog {...defaultProps} />);

    const nameInput = screen.getByDisplayValue("");
    expect(nameInput).toBeInTheDocument();
  });
});
