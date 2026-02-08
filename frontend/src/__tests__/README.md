# Frontend Testing

This directory contains unit and integration tests for the BITRUN frontend.

## Test Structure

```
src/__tests__/
├── components/        # Component unit tests
│   └── Button.test.tsx
├── stores/           # Zustand store tests
│   └── auth-store.test.ts
├── hooks/            # Custom hook tests
├── utils/            # Test utilities
│   └── test-utils.tsx
└── README.md
```

## Running Tests

### Unit Tests (Jest)

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### E2E Tests (Playwright)

```bash
# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui
```

## Writing Tests

### Component Tests

```tsx
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders correctly", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button")).toHaveTextContent("Click me");
  });
});
```

### Store Tests

```ts
import { act } from "@testing-library/react";
import { useAuthStore } from "@/stores/auth-store";

describe("Auth Store", () => {
  it("sets user correctly", () => {
    act(() => {
      useAuthStore.getState().setUser({ id: "1", name: "Test" });
    });
    expect(useAuthStore.getState().user).toBeTruthy();
  });
});
```

### E2E Tests

```ts
import { test, expect } from "@playwright/test";

test("user can login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("test@example.com");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).toHaveURL("/");
});
```

## Test Utilities

Use the custom render function from `test-utils.tsx` to include providers:

```tsx
import { render, screen } from "@/__tests__/utils/test-utils";
```

## Mocking

### API Calls

```tsx
import { mockFetch } from "@/__tests__/utils/test-utils";

beforeEach(() => {
  global.fetch = mockFetch({ data: "test" });
});
```

### Navigation

```tsx
import { useRouter } from "next/navigation";

jest.mock("next/navigation");
(useRouter as jest.Mock).mockReturnValue({
  push: jest.fn(),
});
```

### Translations

```tsx
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));
```

## Coverage

Coverage reports are generated in the `coverage/` directory when running:

```bash
npm run test:coverage
```

## Best Practices

1. **Test behavior, not implementation** - Focus on what the component does, not how it does it
2. **Use accessible queries** - Prefer `getByRole`, `getByLabelText` over `getByTestId`
3. **Mock external dependencies** - Mock API calls, navigation, etc.
4. **Keep tests isolated** - Each test should be independent
5. **Use meaningful assertions** - Be specific about what you're testing
