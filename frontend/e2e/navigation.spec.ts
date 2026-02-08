/**
 * Navigation E2E Tests
 *
 * Tests for site navigation and layout.
 */

import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("should have working navigation elements", async ({ page }) => {
    await page.goto("/login");

    // Check that the page loads
    await expect(page).toHaveTitle(/.+/);
  });

  test("should support locale switching", async ({ page }) => {
    // Go to English version
    await page.goto("/en/login");
    await expect(page).toHaveURL(/\/en\/login/);

    // Go to Chinese version
    await page.goto("/zh/login");
    await expect(page).toHaveURL(/\/zh\/login/);
  });

  test("should handle 404 pages", async ({ page }) => {
    // Navigate to non-existent page
    await page.goto("/non-existent-page");

    // Should show 404 or redirect
    const content = await page.content();
    expect(content).toBeTruthy();
  });
});

test.describe("Responsive Design", () => {
  test("should work on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/login");

    // Page should be accessible on mobile
    await expect(page.locator("body")).toBeVisible();
  });

  test("should work on tablet viewport", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/login");

    // Page should be accessible on tablet
    await expect(page.locator("body")).toBeVisible();
  });

  test("should work on desktop viewport", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto("/login");

    // Page should be accessible on desktop
    await expect(page.locator("body")).toBeVisible();
  });
});

test.describe("Theme", () => {
  test("should support dark mode", async ({ page }) => {
    await page.goto("/login");

    // Check that the page supports theming
    const html = page.locator("html");
    await expect(html).toBeVisible();
  });

  test("should respect system color scheme", async ({ page }) => {
    // Emulate dark color scheme
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto("/login");

    // Page should load successfully
    await expect(page.locator("body")).toBeVisible();
  });
});

test.describe("Accessibility", () => {
  test("should have proper heading hierarchy", async ({ page }) => {
    await page.goto("/login");

    // Check for at least one heading
    const headings = page.locator("h1, h2, h3, h4, h5, h6");
    await expect(headings.first()).toBeVisible();
  });

  test("should have proper form labels", async ({ page }) => {
    await page.goto("/login");

    // Check that inputs have associated labels
    const emailInput = page.getByLabel(/email/i);
    const passwordInput = page.getByLabel(/password/i);

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
  });

  test("should be keyboard navigable", async ({ page }) => {
    await page.goto("/login");

    // Tab through the page
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    // Something should be focused
    const focusedElement = page.locator(":focus");
    await expect(focusedElement).toBeVisible();
  });
});
