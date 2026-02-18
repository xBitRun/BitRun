/**
 * Tests for API response validation schemas.
 */

import {
  LoginResponseSchema,
  UserProfileSchema,
  StrategySchema,
  StrategyListSchema,
  AccountSchema,
  AccountListSchema,
  DashboardStatsSchema,
  validateResponse,
} from "@/lib/api/schemas";

describe("LoginResponseSchema", () => {
  it("validates valid login response", () => {
    const data = {
      access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      refresh_token: "refresh_token_value",
      token_type: "Bearer",
    };

    const result = LoginResponseSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("rejects missing access_token", () => {
    const data = {
      refresh_token: "refresh_token_value",
      token_type: "Bearer",
    };

    const result = LoginResponseSchema.safeParse(data);
    expect(result.success).toBe(false);
  });

  it("rejects wrong type for access_token", () => {
    const data = {
      access_token: 12345,
      refresh_token: "refresh_token_value",
      token_type: "Bearer",
    };

    const result = LoginResponseSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe("UserProfileSchema", () => {
  it("validates valid user profile", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      email: "user@example.com",
      username: "testuser",
      created_at: "2024-01-01T00:00:00Z",
    };

    const result = UserProfileSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("rejects invalid UUID", () => {
    const data = {
      id: "not-a-uuid",
      email: "user@example.com",
      username: "testuser",
      created_at: "2024-01-01T00:00:00Z",
    };

    const result = UserProfileSchema.safeParse(data);
    expect(result.success).toBe(false);
  });

  it("rejects invalid email", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      email: "not-an-email",
      username: "testuser",
      created_at: "2024-01-01T00:00:00Z",
    };

    const result = UserProfileSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe("StrategySchema", () => {
  it("validates valid strategy", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      user_id: "550e8400-e29b-41d4-a716-446655440001",
      type: "ai",
      name: "My Strategy",
      symbols: ["BTC"],
      config: { leverage: 5 },
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };

    const result = StrategySchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("validates strategy with optional fields", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      user_id: "550e8400-e29b-41d4-a716-446655440001",
      type: "ai",
      name: "My Strategy",
      description: "A simple strategy",
      symbols: ["BTC", "ETH"],
      config: { leverage: 5 },
      visibility: "public",
      category: "momentum",
      tags: ["crypto", "ai"],
      forked_from: null,
      fork_count: 3,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-02T00:00:00Z",
    };

    const result = StrategySchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("validates strategy with null category", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      user_id: "550e8400-e29b-41d4-a716-446655440001",
      type: "grid",
      name: "My Strategy",
      symbols: ["BTC"],
      config: {},
      category: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };

    const result = StrategySchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("rejects missing required fields", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "My Strategy",
      // Missing user_id, type, symbols, config, created_at, updated_at
    };

    const result = StrategySchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe("StrategyListSchema", () => {
  it("validates empty array", () => {
    const result = StrategyListSchema.safeParse([]);
    expect(result.success).toBe(true);
  });

  it("validates array of strategies", () => {
    const data = [
      {
        id: "550e8400-e29b-41d4-a716-446655440000",
        user_id: "550e8400-e29b-41d4-a716-446655440001",
        type: "ai",
        name: "Strategy 1",
        symbols: ["BTC"],
        config: {},
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
      {
        id: "550e8400-e29b-41d4-a716-446655440002",
        user_id: "550e8400-e29b-41d4-a716-446655440001",
        type: "grid",
        name: "Strategy 2",
        symbols: ["ETH"],
        config: {},
        created_at: "2024-01-02T00:00:00Z",
        updated_at: "2024-01-02T00:00:00Z",
      },
    ];

    const result = StrategyListSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("rejects if one strategy is invalid", () => {
    const data = [
      {
        id: "550e8400-e29b-41d4-a716-446655440000",
        user_id: "550e8400-e29b-41d4-a716-446655440001",
        type: "ai",
        name: "Strategy 1",
        symbols: ["BTC"],
        config: {},
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
      {
        id: "invalid-uuid",
        user_id: "550e8400-e29b-41d4-a716-446655440001",
        type: "grid",
        name: "Strategy 2",
        symbols: ["ETH"],
        config: {},
        created_at: "2024-01-02T00:00:00Z",
        updated_at: "2024-01-02T00:00:00Z",
      },
    ];

    const result = StrategyListSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe("AccountSchema", () => {
  it("validates valid account", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "My Binance",
      exchange: "binance",
      is_testnet: false,
      created_at: "2024-01-01T00:00:00Z",
    };

    const result = AccountSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("validates account with optional is_active", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "My Binance",
      exchange: "binance",
      is_testnet: false,
      is_active: true,
      created_at: "2024-01-01T00:00:00Z",
    };

    const result = AccountSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("rejects wrong type for is_testnet", () => {
    const data = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "My Binance",
      exchange: "binance",
      is_testnet: "yes",
      created_at: "2024-01-01T00:00:00Z",
    };

    const result = AccountSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe("AccountListSchema", () => {
  it("validates array of accounts", () => {
    const data = [
      {
        id: "550e8400-e29b-41d4-a716-446655440000",
        name: "My Binance",
        exchange: "binance",
        is_testnet: false,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    const result = AccountListSchema.safeParse(data);
    expect(result.success).toBe(true);
  });
});

describe("DashboardStatsSchema", () => {
  it("validates valid dashboard stats", () => {
    const data = {
      total_equity: 10000.5,
      daily_pnl: 500.25,
      daily_pnl_percentage: 5.25,
      active_strategies: 3,
      total_strategies: 5,
      active_positions: 2,
      total_accounts: 1,
    };

    const result = DashboardStatsSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("validates empty object (all optional)", () => {
    const data = {};

    const result = DashboardStatsSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("validates partial stats", () => {
    const data = {
      total_equity: 10000,
      active_strategies: 2,
    };

    const result = DashboardStatsSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("rejects wrong type for numeric fields", () => {
    const data = {
      total_equity: "10000",
    };

    const result = DashboardStatsSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe("validateResponse", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("returns validated data when valid", () => {
    const data = {
      access_token: "token",
      refresh_token: "refresh",
      token_type: "Bearer",
    };

    const result = validateResponse(data, LoginResponseSchema, "login");

    expect(result).toEqual(data);
  });

  it("returns original data on validation failure", () => {
    const invalidData = {
      access_token: 123,
      refresh_token: "refresh",
      token_type: "Bearer",
    };

    const result = validateResponse(invalidData, LoginResponseSchema, "login");

    // Should return original data even if invalid
    expect(result).toEqual(invalidData);
  });

  it("logs warning in development mode on failure", () => {
    const consoleSpy = jest.spyOn(console, "warn").mockImplementation();

    const invalidData = {
      access_token: 123,
    };

    validateResponse(invalidData, LoginResponseSchema, "login test");

    expect(consoleSpy).toHaveBeenCalled();
    expect(consoleSpy.mock.calls[0][0]).toContain("[API Validation]");
    expect(consoleSpy.mock.calls[0][0]).toContain("login test");
  });

  it("does not log in production mode", () => {
    const consoleSpy = jest.spyOn(console, "warn").mockImplementation();

    const invalidData = {
      access_token: 123,
    };

    validateResponse(invalidData, LoginResponseSchema, "login");

    expect(consoleSpy).not.toHaveBeenCalled();
  });

  it("uses default context when not provided", () => {
    const consoleSpy = jest.spyOn(console, "warn").mockImplementation();

    validateResponse({ invalid: true }, LoginResponseSchema);

    expect(consoleSpy).toHaveBeenCalled();
    expect(consoleSpy.mock.calls[0][0]).toContain("API response");
  });
});
