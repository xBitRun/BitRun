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
  it("register should POST to /auth/register with skipAuth", async () => {
    const data = { email: "a@b.com", password: "pw", name: "Test" };
    mockedApi.post.mockResolvedValue({ id: "1", email: "a@b.com", name: "Test", is_active: true });

    await authApi.register(data);

    expect(mockedApi.post).toHaveBeenCalledWith("/auth/register", data, { skipAuth: true });
  });

  it("logout should POST to /auth/logout", async () => {
    mockedApi.post.mockResolvedValue({ message: "ok" });

    await authApi.logout();

    expect(mockedApi.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("me should GET /auth/me", async () => {
    mockedApi.get.mockResolvedValue({ id: "1", email: "a@b.com", name: "Test", is_active: true });

    await authApi.me();

    expect(mockedApi.get).toHaveBeenCalledWith("/auth/me");
  });

  it("refresh should POST to /auth/refresh with skipAuth", async () => {
    mockedApi.post.mockResolvedValue({ access_token: "t", refresh_token: "r", token_type: "bearer", expires_in: 3600 });

    await authApi.refresh("refresh-tok");

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/auth/refresh",
      { refresh_token: "refresh-tok" },
      { skipAuth: true }
    );
  });

  it("updateProfile should PUT to /auth/profile", async () => {
    mockedApi.put.mockResolvedValue({ id: "1", email: "a@b.com", name: "New", is_active: true });

    await authApi.updateProfile({ name: "New" });

    expect(mockedApi.put).toHaveBeenCalledWith("/auth/profile", { name: "New" });
  });

  it("changePassword should POST to /auth/change-password", async () => {
    mockedApi.post.mockResolvedValue({ message: "ok" });

    await authApi.changePassword({ current_password: "old", new_password: "new" });

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
    const data = { name: "Test", prompt: "p", trading_mode: "aggressive" as const, symbols: ["BTC"], account_id: "a1" };
    mockedApi.post.mockResolvedValue({ id: "s1" });
    await strategiesApi.create(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/strategies", data);
  });

  it("update should PATCH /strategies/:id", async () => {
    mockedApi.patch.mockResolvedValue({ id: "s1" });
    await strategiesApi.update("s1", { name: "Updated" });
    expect(mockedApi.patch).toHaveBeenCalledWith("/strategies/s1", { name: "Updated" });
  });

  it("delete should DELETE /strategies/:id", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await strategiesApi.delete("s1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/strategies/s1");
  });

  it("activate should POST status=active", async () => {
    mockedApi.post.mockResolvedValue({ id: "s1", status: "active" });
    await strategiesApi.activate("s1");
    expect(mockedApi.post).toHaveBeenCalledWith("/strategies/s1/status", { status: "active" });
  });

  it("pause should POST status=paused", async () => {
    mockedApi.post.mockResolvedValue({ id: "s1", status: "paused" });
    await strategiesApi.pause("s1");
    expect(mockedApi.post).toHaveBeenCalledWith("/strategies/s1/status", { status: "paused" });
  });

  it("stop should POST status=stopped", async () => {
    mockedApi.post.mockResolvedValue({ id: "s1", status: "stopped" });
    await strategiesApi.stop("s1");
    expect(mockedApi.post).toHaveBeenCalledWith("/strategies/s1/status", { status: "stopped" });
  });

  it("previewPrompt should POST /strategies/preview-prompt", async () => {
    const data = { prompt: "test" };
    mockedApi.post.mockResolvedValue({ system_prompt: "", estimated_tokens: 0, sections: {} });
    await strategiesApi.previewPrompt(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/strategies/preview-prompt", data);
  });
});

// ==================== Quant Strategies ====================

describe("quantStrategiesApi", () => {
  it("list should GET /quant-strategies (no params)", async () => {
    mockedApi.get.mockResolvedValue([]);
    await quantStrategiesApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith("/quant-strategies");
  });

  it("list should append query params when provided", async () => {
    mockedApi.get.mockResolvedValue([]);
    await quantStrategiesApi.list({ status_filter: "active", strategy_type: "grid" });
    expect(mockedApi.get).toHaveBeenCalledWith(
      expect.stringContaining("/quant-strategies?")
    );
    const url = mockedApi.get.mock.calls[0][0];
    expect(url).toContain("status_filter=active");
    expect(url).toContain("strategy_type=grid");
  });

  it("get should GET /quant-strategies/:id", async () => {
    mockedApi.get.mockResolvedValue({ id: "q1" });
    await quantStrategiesApi.get("q1");
    expect(mockedApi.get).toHaveBeenCalledWith("/quant-strategies/q1");
  });

  it("delete should DELETE /quant-strategies/:id", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await quantStrategiesApi.delete("q1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/quant-strategies/q1");
  });
});

// ==================== Workers ====================

describe("workersApi", () => {
  it("triggerExecution should POST /workers/:id/trigger", async () => {
    mockedApi.post.mockResolvedValue({ message: "ok", success: true });
    await workersApi.triggerExecution("s1");
    expect(mockedApi.post).toHaveBeenCalledWith("/workers/s1/trigger");
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
    const data = { name: "Main", exchange: "binance" as const, is_testnet: false };
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
});

// ==================== Decisions ====================

describe("decisionsApi", () => {
  it("listRecent should GET /decisions/recent with limit param", async () => {
    mockedApi.get.mockResolvedValue([]);
    await decisionsApi.listRecent(10);
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/recent", { params: { limit: 10 } });
  });

  it("listByStrategy should include offset and execution_filter", async () => {
    mockedApi.get.mockResolvedValue([]);
    await decisionsApi.listByStrategy("s1", 5, 10, "executed");
    expect(mockedApi.get).toHaveBeenCalledWith("/decisions/strategy/s1", {
      params: { limit: 5, offset: 10, execution_filter: "executed" },
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
    expect(mockedApi.get).toHaveBeenCalledWith("/models", { params: { provider: "deepseek" } });
  });

  it("list without provider should pass empty params", async () => {
    mockedApi.get.mockResolvedValue([]);
    await modelsApi.list();
    expect(mockedApi.get).toHaveBeenCalledWith("/models", { params: {} });
  });

  it("test should POST /models/test", async () => {
    mockedApi.post.mockResolvedValue({ model_id: "m1", success: true, message: "ok" });
    await modelsApi.test({ model_id: "deepseek:chat" });
    expect(mockedApi.post).toHaveBeenCalledWith("/models/test", { model_id: "deepseek:chat" });
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
    const data = { provider_type: "openai", name: "My OpenAI", api_key: "sk-xxx" };
    mockedApi.post.mockResolvedValue({ id: "p1" });
    await providersApi.create(data);
    expect(mockedApi.post).toHaveBeenCalledWith("/providers", data);
  });

  it("update should PATCH /providers/:id", async () => {
    mockedApi.patch.mockResolvedValue({ id: "p1" });
    await providersApi.update("p1", { name: "Renamed" });
    expect(mockedApi.patch).toHaveBeenCalledWith("/providers/p1", { name: "Renamed" });
  });

  it("delete should DELETE /providers/:id", async () => {
    mockedApi.delete.mockResolvedValue(undefined);
    await providersApi.delete("p1");
    expect(mockedApi.delete).toHaveBeenCalledWith("/providers/p1");
  });

  it("test should POST /providers/:id/test", async () => {
    mockedApi.post.mockResolvedValue({ success: true, message: "ok" });
    await providersApi.test("p1", "sk-key");
    expect(mockedApi.post).toHaveBeenCalledWith("/providers/p1/test", { api_key: "sk-key" });
  });

  it("replaceModels should PUT /providers/:id/models", async () => {
    const models = [{ id: "m1", name: "Model 1" }];
    mockedApi.put.mockResolvedValue(models);
    await providersApi.replaceModels("p1", models);
    expect(mockedApi.put).toHaveBeenCalledWith("/providers/p1/models", { models });
  });
});
