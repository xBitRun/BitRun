/**
 * Tests for API endpoint wrapper functions
 */

import { api } from "@/lib/api/client";
import {
  authApi,
  strategiesApi,
  quantStrategiesApi,
  workersApi,
  accountsApi,
  decisionsApi,
  backtestApi,
  dashboardApi,
  healthApi,
  modelsApi,
  providersApi,
  agentsApi,
  systemApi,
} from "@/lib/api/endpoints";

jest.mock("@/lib/api/client", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
  TokenManager: { getAccessToken: jest.fn() },
}));

const mockedApi = api as jest.Mocked<typeof api>;

beforeEach(() => {
  jest.clearAllMocks();
});

// ==================== Auth ====================

describe("authApi", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  it("login should use form data format", async () => {
    const mockResponse = {
      ok: true,
      json: async () => ({
        access_token: "token",
        refresh_token: "refresh",
        token_type: "bearer",
        expires_in: 3600,
      }),
    };
    (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

    await authApi.login({ email: "test@example.com", password: "password123" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/login"),
      expect.objectContaining({
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: expect.stringContaining("username=test%40example.com"),
      }),
    );
  });

  it("login should handle structured auth error", async () => {
    const mockResponse = {
      ok: false,
      status: 401,
      json: async () => ({
        detail: {
          code: "AUTH_INVALID_CREDENTIALS",
          remaining_attempts: 2,
          remaining_minutes: 5,
        },
      }),
    };
    (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

    await expect(
      authApi.login({ email: "test@example.com", password: "wrong" }),
    ).rejects.toThrow();
  });

  it("login should handle string error detail", async () => {
    const mockResponse = {
      ok: false,
      status: 401,
      json: async () => ({
        detail: "Invalid credentials",
      }),
    };
    (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

    await expect(
      authApi.login({ email: "test@example.com", password: "wrong" }),
    ).rejects.toThrow();
  });

  it("login should handle JSON parse error", async () => {
    const mockResponse = {
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("Invalid JSON");
      },
    };
    (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

    await expect(
      authApi.login({ email: "test@example.com", password: "password" }),
    ).rejects.toThrow();
  });

  it("login should use default API URL when env var not set", async () => {
    const originalEnv = process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;

    const mockResponse = {
      ok: true,
      json: async () => ({
        access_token: "token",
        refresh_token: "refresh",
        token_type: "bearer",
        expires_in: 3600,
      }),
    };
    (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

    await authApi.login({ email: "test@example.com", password: "password123" });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("http://localhost:8000/api/v1/auth/login"),
      expect.any(Object),
    );

    if (originalEnv) {
      process.env.NEXT_PUBLIC_API_URL = originalEnv;
    }
  });

  it("register should POST to /auth/register with skipAuth", async () => {
    const data = { email: "a@b.com", password: "pw", name: "Test", invite_code: "TEST123" };
    mockedApi.post.mockResolvedValue({
      id: "1",
      email: "a@b.com",
      name: "Test",
      is_active: true,
      role: "user" as const,
    });

    await authApi.register(data);

    expect(mockedApi.post).toHaveBeenCalledWith("/auth/register", data, {
      skipAuth: true,
    });
  });

  it("logout should POST to /auth/logout", async () => {
    mockedApi.post.mockResolvedValue({ message: "ok" });

    await authApi.logout();

    expect(mockedApi.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("me should GET /auth/me", async () => {
    mockedApi.get.mockResolvedValue({
      id: "1",
      email: "a@b.com",
      name: "Test",
      is_active: true,
    });

    await authApi.me();

    expect(mockedApi.get).toHaveBeenCalledWith("/auth/me");
  });

  it("refresh should POST to /auth/refresh with skipAuth", async () => {
    mockedApi.post.mockResolvedValue({
      access_token: "t",
      refresh_token: "r",
      token_type: "bearer",
      expires_in: 3600,
    });

    await authApi.refresh("refresh-tok");

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/auth/refresh",
      { refresh_token: "refresh-tok" },
      { skipAuth: true },
    );
  });

  it("updateProfile should PUT to /auth/profile", async () => {
    mockedApi.put.mockResolvedValue({
      id: "1",
      email: "a@b.com",
      name: "New",
      is_active: true,
    });

    await authApi.updateProfile({ name: "New" });

    expect(mockedApi.put).toHaveBeenCalledWith("/auth/profile", {
      name: "New",
    });
  });

  it("changePassword should POST to /auth/change-password", async () => {
    mockedApi.post.mockResolvedValue({ message: "ok" });

    await authApi.changePassword({
      current_password: "old",
      new_password: "new",
    });

    expect(mockedApi.post).toHaveBeenCalledWith("/auth/change-password", {
      current_password: "old",
      new_password: "new",
    });
  });
});

// ==================== Strategies ====================

describe("strategiesApi", () => {
  it("list should GET /strategies", async () => {
    mockedApi.get.mockResolvedValue([]);
    await strategiesApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith("/strategies");
  });

  it("get should GET /strategies/:id", async () => {
    mockedApi.get.mockResolvedValue({ id: "s1" });
    await strategiesApi.get("s1");
    expect(mockedApi.get).toHaveBeenCalledWith("/strategies/s1");
  });

  it("create should POST /strategies", async () => {
    const data = {
      name: "Test",
      type: "ai" as const,
      symbols: ["BTCUSDT"],
      config: { test: true },
    };
    mockedApi.post.mockResolvedValue({ id: "s1" });
    await strategiesApi.create(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/strategies", data);
  });

  it("update should PATCH /strategies/:id", async () => {
    mockedApi.patch.mockResolvedValue({ id: "s1" });
    await strategiesApi.update("s1", { name: "Updated" });
    expect(mockedApi.patch).toHaveBeenCalledWith("/strategies/s1", {
      name: "Updated",
    });
  });

  it("delete should DELETE /strategies/:id", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await strategiesApi.delete("s1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/strategies/s1");
  });

  it("previewPrompt should POST /strategies/preview-prompt", async () => {
    const data = { prompt: "test" };
    mockedApi.post.mockResolvedValue({
      system_prompt: "",
      estimated_tokens: 0,
      sections: {},
    });
    await strategiesApi.previewPrompt(data);
    expect(mockedApi.post).toHaveBeenCalledWith(
      "/strategies/preview-prompt",
      data,
    );
  });
});

// ==================== Quant Strategies ====================

describe("quantStrategiesApi", () => {
  it("list should delegate to agentsApi (GET /agents)", async () => {
    mockedApi.get.mockResolvedValue([]);
    await quantStrategiesApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith(
      expect.stringContaining("/agents"),
    );
  });

  it("list should pass query params through to agents endpoint", async () => {
    mockedApi.get.mockResolvedValue([]);
    await quantStrategiesApi.list({
      status_filter: "active",
      strategy_type: "grid",
    });
    const url = mockedApi.get.mock.calls[0][0];
    expect(url).toContain("/agents");
    expect(url).toContain("status_filter=active");
    expect(url).toContain("strategy_type=grid");
  });

  it("get should delegate to agentsApi (GET /agents/:id)", async () => {
    mockedApi.get.mockResolvedValue({ id: "q1" });
    await quantStrategiesApi.get("q1");
    expect(mockedApi.get).toHaveBeenCalledWith("/agents/q1");
  });

  it("delete should delegate to agentsApi (DELETE /agents/:id)", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await quantStrategiesApi.delete("q1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/agents/q1");
  });

  it("create should throw deprecation error", async () => {
    expect(() =>
      quantStrategiesApi.create({
        name: "Grid Strategy",
        strategy_type: "grid",
        symbol: "BTC",
        config: { upper_price: 50000, lower_price: 40000 },
      }),
    ).toThrow("deprecated");
  });

  it("update should delegate to agentsApi (PATCH /agents/:id)", async () => {
    const data = { name: "Updated Grid" };
    mockedApi.patch.mockResolvedValue({ id: "q1", name: "Updated Grid" });
    await quantStrategiesApi.update("q1", data);
    expect(mockedApi.patch).toHaveBeenCalledWith("/agents/q1", data);
  });

  it("updateStatus should delegate to agentsApi (POST /agents/:id/status)", async () => {
    mockedApi.post.mockResolvedValue({ id: "q1", status: "active" });
    await quantStrategiesApi.updateStatus("q1", "active", true);
    expect(mockedApi.post).toHaveBeenCalledWith("/agents/q1/status", {
      status: "active",
      close_positions: true,
    });
  });
});

// ==================== Workers ====================

describe("workersApi", () => {
  it("triggerExecution should delegate to agentsApi (POST /agents/:id/trigger)", async () => {
    mockedApi.post.mockResolvedValue({ message: "ok", success: true });
    await workersApi.triggerExecution("s1");
    expect(mockedApi.post).toHaveBeenCalledWith("/agents/s1/trigger");
  });
});

// ==================== Accounts ====================

describe("accountsApi", () => {
  it("list should GET /accounts", async () => {
    mockedApi.get.mockResolvedValue([]);
    await accountsApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith("/accounts");
  });

  it("get should GET /accounts/:id", async () => {
    mockedApi.get.mockResolvedValue({ id: "a1" });
    await accountsApi.get("a1");
    expect(mockedApi.get).toHaveBeenCalledWith("/accounts/a1");
  });

  it("create should POST /accounts", async () => {
    const data = {
      name: "Main",
      exchange: "binance" as const,
      is_testnet: false,
    };
    mockedApi.post.mockResolvedValue({ id: "a1" });
    await accountsApi.create(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/accounts", data);
  });

  it("delete should DELETE /accounts/:id", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await accountsApi.delete("a1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/accounts/a1");
  });

  it("testConnection should POST /accounts/:id/test", async () => {
    mockedApi.post.mockResolvedValue({ success: true, message: "ok" });
    await accountsApi.testConnection("a1");
    expect(mockedApi.post).toHaveBeenCalledWith("/accounts/a1/test");
  });

  it("getBalance should GET /accounts/:id/balance", async () => {
    mockedApi.get.mockResolvedValue({ account_id: "a1", equity: 1000 });
    await accountsApi.getBalance("a1");
    expect(mockedApi.get).toHaveBeenCalledWith("/accounts/a1/balance");
  });

  it("getPositions should GET /accounts/:id/positions", async () => {
    mockedApi.get.mockResolvedValue([]);
    await accountsApi.getPositions("a1");
    expect(mockedApi.get).toHaveBeenCalledWith("/accounts/a1/positions");
  });

  it("update should PATCH /accounts/:id", async () => {
    const data = { name: "Updated Account" };
    mockedApi.patch.mockResolvedValue({ id: "a1", name: "Updated Account" });
    await accountsApi.update("a1", data);
    expect(mockedApi.patch).toHaveBeenCalledWith("/accounts/a1", data);
  });
});

// ==================== Decisions ====================

describe("decisionsApi", () => {
  it("listRecent should GET /decisions/recent with limit param", async () => {
    mockedApi.get.mockResolvedValue([]);
    await decisionsApi.listRecent(10);
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/recent", {
      params: { limit: 10 },
    });
  });

  it("listRecent should use default limit when not provided", async () => {
    mockedApi.get.mockResolvedValue([]);
    await decisionsApi.listRecent();
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/recent", {
      params: { limit: 20 },
    });
  });

  it("listByStrategy should include offset and execution_filter", async () => {
    mockedApi.get.mockResolvedValue([]);
    await decisionsApi.listByStrategy("s1", 5, 10, "executed");
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/strategy/s1", {
      params: { limit: 5, offset: 10, execution_filter: "executed" },
    });
  });

  it("listByStrategy should include action filter when provided", async () => {
    mockedApi.get.mockResolvedValue([]);
    await decisionsApi.listByStrategy("s1", 5, 10, "all", "open_long");
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/strategy/s1", {
      params: {
        limit: 5,
        offset: 10,
        execution_filter: "all",
        action: "open_long",
      },
    });
  });

  it("listByStrategy should use default values", async () => {
    mockedApi.get.mockResolvedValue([]);
    await decisionsApi.listByStrategy("s1");
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/strategy/s1", {
      params: { limit: 10, offset: 0, execution_filter: "all" },
    });
  });

  it("get should GET /decisions/:id", async () => {
    mockedApi.get.mockResolvedValue({ id: "d1" });
    await decisionsApi.get("d1");
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/d1");
  });

  it("getStats should GET /decisions/strategy/:id/stats", async () => {
    mockedApi.get.mockResolvedValue({ total_decisions: 10 });
    await decisionsApi.getStats("s1");
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/strategy/s1/stats");
  });
});

// ==================== Backtest ====================

describe("backtestApi", () => {
  it("run should POST /backtest/run", async () => {
    const data = {
      strategy_id: "s1",
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
    };
    mockedApi.post.mockResolvedValue({ strategy_name: "Test" });
    await backtestApi.run(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/backtest/run", data);
  });

  it("quick should POST /backtest/quick", async () => {
    const data = {
      symbols: ["BTC"],
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
    };
    mockedApi.post.mockResolvedValue({ strategy_name: "Quick" });
    await backtestApi.quick(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/backtest/quick", data);
  });

  it("getSymbols should GET /backtest/symbols with exchange param", async () => {
    mockedApi.get.mockResolvedValue({ symbols: [] });
    await backtestApi.getSymbols("bybit");
    expect(mockedApi.get).toHaveBeenCalledWith("/backtest/symbols", {
      params: { exchange: "bybit" },
    });
  });

  it("getSymbols should use default exchange when not provided", async () => {
    mockedApi.get.mockResolvedValue({ symbols: [] });
    await backtestApi.getSymbols();
    expect(mockedApi.get).toHaveBeenCalledWith("/backtest/symbols", {
      params: { exchange: "binance" },
    });
  });
});

// ==================== Dashboard ====================

describe("dashboardApi", () => {
  it("getFullStats should GET /dashboard/stats", async () => {
    mockedApi.get.mockResolvedValue({ total_equity: 50000 });
    await dashboardApi.getFullStats();
    expect(mockedApi.get).toHaveBeenCalledWith("/dashboard/stats");
  });

  it("getActivity should GET /dashboard/activity with params", async () => {
    mockedApi.get.mockResolvedValue({ items: [], total: 0, has_more: false });
    await dashboardApi.getActivity(10, 5);
    expect(mockedApi.get).toHaveBeenCalledWith("/dashboard/activity", {
      params: { limit: 10, offset: 5 },
    });
  });

  it("getActivity should use default values", async () => {
    mockedApi.get.mockResolvedValue({ items: [], total: 0, has_more: false });
    await dashboardApi.getActivity();
    expect(mockedApi.get).toHaveBeenCalledWith("/dashboard/activity", {
      params: { limit: 20, offset: 0 },
    });
  });

  it("getStats should return transformed DashboardStats", async () => {
    const mockResponse = {
      total_equity: 50000,
      daily_pnl: 1000,
      daily_pnl_percent: 2.0,
      active_strategies: 5,
      open_positions: 10,
      today_executed_decisions: 20,
    };
    mockedApi.get.mockResolvedValue(mockResponse);

    const result = await dashboardApi.getStats();

    expect(result).toEqual({
      totalEquity: 50000,
      dailyPnl: 1000,
      dailyPnlPercent: 2.0,
      activeStrategies: 5,
      openPositions: 10,
      todayTrades: 20,
    });
  });

  it("getStats should fallback to local aggregation on error", async () => {
    mockedApi.get.mockRejectedValueOnce(new Error("API error"));
    mockedApi.get.mockResolvedValueOnce([]); // accountsApi.list
    mockedApi.get.mockResolvedValueOnce([]); // strategiesApi.list

    const result = await dashboardApi.getStats();

    expect(result).toEqual({
      totalEquity: 0,
      dailyPnl: 0,
      dailyPnlPercent: 0,
      activeStrategies: 0,
      openPositions: 0,
      todayTrades: 0,
    });
  });

  it("getStats should count active strategies in fallback", async () => {
    mockedApi.get.mockRejectedValueOnce(new Error("API error"));
    mockedApi.get.mockResolvedValueOnce([]); // accountsApi.list
    mockedApi.get.mockResolvedValueOnce([
      { id: "s1", status: "active" },
      { id: "s2", status: "paused" },
      { id: "s3", status: "active" },
    ]); // strategiesApi.list

    const result = await dashboardApi.getStats();

    expect(result.activeStrategies).toBe(2);
  });
});

// ==================== Health ====================

describe("healthApi", () => {
  it("check should GET /health with skipAuth", async () => {
    mockedApi.get.mockResolvedValue({ status: "healthy" });
    await healthApi.check();
    expect(mockedApi.get).toHaveBeenCalledWith("/health", { skipAuth: true });
  });

  it("detailed should GET /health/detailed", async () => {
    mockedApi.get.mockResolvedValue({ status: "healthy" });
    await healthApi.detailed();
    expect(mockedApi.get).toHaveBeenCalledWith("/health/detailed");
  });
});

// ==================== Models ====================

describe("modelsApi", () => {
  it("listProviders should GET /models/providers", async () => {
    mockedApi.get.mockResolvedValue([]);
    await modelsApi.listProviders();
    expect(mockedApi.get).toHaveBeenCalledWith("/models/providers");
  });

  it("list should GET /models with optional provider param", async () => {
    mockedApi.get.mockResolvedValue([]);
    await modelsApi.list("deepseek");
    expect(mockedApi.get).toHaveBeenCalledWith("/models", {
      params: { provider: "deepseek" },
    });
  });

  it("list without provider should pass empty params", async () => {
    mockedApi.get.mockResolvedValue([]);
    await modelsApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith("/models", { params: {} });
  });

  it("test should POST /models/test", async () => {
    mockedApi.post.mockResolvedValue({
      model_id: "m1",
      success: true,
      message: "ok",
    });
    await modelsApi.test({ model_id: "deepseek:chat" });
    expect(mockedApi.post).toHaveBeenCalledWith("/models/test", {
      model_id: "deepseek:chat",
    });
  });

  it("get should GET /models/:id with encoded modelId", async () => {
    mockedApi.get.mockResolvedValue({ id: "m1" });
    await modelsApi.get("deepseek:chat");
    expect(mockedApi.get).toHaveBeenCalledWith("/models/deepseek%3Achat");
  });

  it("get should encode special characters in modelId", async () => {
    mockedApi.get.mockResolvedValue({ id: "m1" });
    await modelsApi.get("provider/model@version");
    expect(mockedApi.get).toHaveBeenCalledWith(
      "/models/provider%2Fmodel%40version",
    );
  });
});

// ==================== Providers ====================

describe("providersApi", () => {
  it("list should GET /providers", async () => {
    mockedApi.get.mockResolvedValue([]);
    await providersApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith("/providers");
  });

  it("create should POST /providers", async () => {
    const data = {
      provider_type: "openai",
      name: "My OpenAI",
      api_key: "sk-xxx",
    };
    mockedApi.post.mockResolvedValue({ id: "p1" });
    await providersApi.create(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/providers", data);
  });

  it("update should PATCH /providers/:id", async () => {
    mockedApi.patch.mockResolvedValue({ id: "p1" });
    await providersApi.update("p1", { name: "Renamed" });
    expect(mockedApi.patch).toHaveBeenCalledWith("/providers/p1", {
      name: "Renamed",
    });
  });

  it("delete should DELETE /providers/:id", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await providersApi.delete("p1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/providers/p1");
  });

  it("test should POST /providers/:id/test", async () => {
    mockedApi.post.mockResolvedValue({ success: true, message: "ok" });
    await providersApi.test("p1", "sk-key");
    expect(mockedApi.post).toHaveBeenCalledWith("/providers/p1/test", {
      api_key: "sk-key",
    });
  });

  it("replaceModels should PUT /providers/:id/models", async () => {
    const models = [{ id: "m1", name: "Model 1" }];
    mockedApi.put.mockResolvedValue(models);
    await providersApi.replaceModels("p1", models);
    expect(mockedApi.put).toHaveBeenCalledWith("/providers/p1/models", {
      models,
    });
  });

  it("listPresets should GET /providers/presets", async () => {
    mockedApi.get.mockResolvedValue([]);
    await providersApi.listPresets();
    expect(mockedApi.get).toHaveBeenCalledWith("/providers/presets");
  });

  it("listFormats should GET /providers/formats", async () => {
    mockedApi.get.mockResolvedValue({ formats: [] });
    await providersApi.listFormats();
    expect(mockedApi.get).toHaveBeenCalledWith("/providers/formats");
  });

  it("listModels should GET /providers/:id/models", async () => {
    mockedApi.get.mockResolvedValue([]);
    await providersApi.listModels("p1");
    expect(mockedApi.get).toHaveBeenCalledWith("/providers/p1/models");
  });

  it("addModel should POST /providers/:id/models", async () => {
    const modelData = { id: "m1", name: "Model 1" };
    mockedApi.post.mockResolvedValue(modelData);
    await providersApi.addModel("p1", modelData);
    expect(mockedApi.post).toHaveBeenCalledWith(
      "/providers/p1/models",
      modelData,
    );
  });

  it("deleteModel should DELETE /providers/:id/models/:modelId", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await providersApi.deleteModel("p1", "model:1");
    expect(mockedApi.delete).toHaveBeenCalledWith(
      "/providers/p1/models/model%3A1",
    );
  });

  it("test should POST /providers/:id/test with optional apiKey", async () => {
    mockedApi.post.mockResolvedValue({ success: true, message: "ok" });
    await providersApi.test("p1", "sk-key");
    expect(mockedApi.post).toHaveBeenCalledWith("/providers/p1/test", {
      api_key: "sk-key",
    });
  });

  it("test should POST /providers/:id/test without apiKey", async () => {
    mockedApi.post.mockResolvedValue({ success: true, message: "ok" });
    await providersApi.test("p1");
    expect(mockedApi.post).toHaveBeenCalledWith("/providers/p1/test", {
      api_key: undefined,
    });
  });
});

// ==================== Agents ====================

describe("agentsApi", () => {
  it("list should GET /agents with optional params", async () => {
    mockedApi.get.mockResolvedValue([]);
    await agentsApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith("/agents");
  });

  it("list should pass filter params", async () => {
    mockedApi.get.mockResolvedValue([]);
    await agentsApi.list({
      status_filter: "active",
      strategy_type: "dca" as const,
    });
    expect(mockedApi.get).toHaveBeenCalledWith(
      "/agents?status_filter=active&strategy_type=dca",
    );
  });

  it("get should GET /agents/:id", async () => {
    mockedApi.get.mockResolvedValue({ id: "a1" });
    await agentsApi.get("a1");
    expect(mockedApi.get).toHaveBeenCalledWith("/agents/a1");
  });

  it("create should POST /agents", async () => {
    const data = {
      name: "Test Agent",
      strategy_id: "s1",
      execution_mode: "live" as const,
    };
    mockedApi.post.mockResolvedValue({ id: "a1" });
    await agentsApi.create(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/agents", data);
  });

  it("update should PATCH /agents/:id", async () => {
    mockedApi.patch.mockResolvedValue({ id: "a1" });
    await agentsApi.update("a1", { name: "Updated" });
    expect(mockedApi.patch).toHaveBeenCalledWith("/agents/a1", {
      name: "Updated",
    });
  });

  it("delete should DELETE /agents/:id", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await agentsApi.delete("a1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/agents/a1");
  });

  it("updateStatus should POST /agents/:id/status", async () => {
    mockedApi.post.mockResolvedValue({ id: "a1", status: "paused" });
    await agentsApi.updateStatus("a1", "paused", true);
    expect(mockedApi.post).toHaveBeenCalledWith("/agents/a1/status", {
      status: "paused",
      close_positions: true,
    });
  });

  it("activate should POST /agents/:id/status with active", async () => {
    mockedApi.post.mockResolvedValue({ id: "a1", status: "active" });
    await agentsApi.activate("a1");
    expect(mockedApi.post).toHaveBeenCalledWith("/agents/a1/status", {
      status: "active",
    });
  });

  it("pause should POST /agents/:id/status with paused", async () => {
    mockedApi.post.mockResolvedValue({ id: "a1", status: "paused" });
    await agentsApi.pause("a1");
    expect(mockedApi.post).toHaveBeenCalledWith("/agents/a1/status", {
      status: "paused",
    });
  });

  it("stop should POST /agents/:id/status with stopped", async () => {
    mockedApi.post.mockResolvedValue({ id: "a1", status: "stopped" });
    await agentsApi.stop("a1", true);
    expect(mockedApi.post).toHaveBeenCalledWith("/agents/a1/status", {
      status: "stopped",
      close_positions: true,
    });
  });

  it("getPositions should GET /agents/:id/positions", async () => {
    mockedApi.get.mockResolvedValue([]);
    await agentsApi.getPositions("a1");
    expect(mockedApi.get).toHaveBeenCalledWith("/agents/a1/positions");
  });

  it("trigger should POST /agents/:id/trigger", async () => {
    mockedApi.post.mockResolvedValue({ message: "ok", success: true });
    await agentsApi.trigger("a1");
    expect(mockedApi.post).toHaveBeenCalledWith("/agents/a1/trigger");
  });
});

// ==================== System ====================

describe("systemApi", () => {
  it("getOutboundIP should GET /system/outbound-ip", async () => {
    mockedApi.get.mockResolvedValue({
      ip: "1.2.3.4",
      source: "aws",
      cached: false,
    });
    await systemApi.getOutboundIP();
    expect(mockedApi.get).toHaveBeenCalledWith("/system/outbound-ip");
  });

  it("getOutboundIP should return cached response", async () => {
    mockedApi.get.mockResolvedValue({
      ip: "1.2.3.4",
      source: "cache",
      cached: true,
    });
    const result = await systemApi.getOutboundIP();
    expect(result.cached).toBe(true);
  });

  it("getOutboundIP should handle null IP", async () => {
    mockedApi.get.mockResolvedValue({
      ip: null,
      source: "error",
      cached: false,
    });
    const result = await systemApi.getOutboundIP();
    expect(result.ip).toBeNull();
  });
});
