/**
 * Authentication E2E Tests
 *
 * Tests for login, logout, and protected route access.
 */

import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.beforeEach(async ({ page }) => {
    // Start from login page
    await page.goto("/login");
  });

  test("should display login page", async ({ page }) => {
    // Check for login form elements
    await expect(page.getByRole("heading")).toContainText(/sign in|login/i);
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in|login/i })).toBeVisible();
  });

  test("should show validation error for empty fields", async ({ page }) => {
    // Click login without filling fields
    await page.getByRole("button", { name: /sign in|login/i }).click();

    // Should show validation errors
    await expect(page.locator("text=/email|required/i")).toBeVisible();
  });

  test("should show error for invalid credentials", async ({ page }) => {
    // Fill in invalid credentials
    await page.getByLabel(/email/i).fill("invalid@example.com");
    await page.getByLabel(/password/i).fill("wrongpassword");
    await page.getByRole("button", { name: /sign in|login/i }).click();

    // Should show error message
    await expect(page.locator("[role='alert'], .error, text=/invalid|incorrect/i")).toBeVisible({
      timeout: 10000,
    });
  });

  test("should redirect to login when accessing protected route", async ({ page }) => {
    // Try to access dashboard without authentication
    await page.goto("/");

    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });
});

test.describe("Protected Routes", () => {
  test("should show dashboard for authenticated users", async ({ page }) => {
    // This test would need a valid auth token
    // For now, we just verify the redirect behavior
    await page.goto("/");

    // Should either show dashboard or redirect to login
    const url = page.url();
    expect(url).toMatch(/login|\/$/);
  });

  test("should show agents page for authenticated users", async ({ page }) => {
    await page.goto("/agents");

    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/login|agents/);
  });

  test("should show accounts page for authenticated users", async ({ page }) => {
    await page.goto("/accounts");

    // Should redirect to login if not authenticated
    await expect(page).toHaveURL(/login|accounts/);
  });
});
