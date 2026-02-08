/**
 * Tests for logger and wsLogger
 */

// We need to control process.env BEFORE the module is loaded,
// so we use jest.isolateModules for environment-dependent tests.

describe("logger", () => {
  let consoleSpy: {
    log: jest.SpyInstance;
    info: jest.SpyInstance;
    warn: jest.SpyInstance;
    error: jest.SpyInstance;
  };

  beforeEach(() => {
    consoleSpy = {
      log: jest.spyOn(console, "log").mockImplementation(),
      info: jest.spyOn(console, "info").mockImplementation(),
      warn: jest.spyOn(console, "warn").mockImplementation(),
      error: jest.spyOn(console, "error").mockImplementation(),
    };
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("in development mode", () => {
    let logger: typeof import("@/lib/logger").logger;

    beforeEach(() => {
      jest.resetModules();
      process.env.NODE_ENV = "development";
      process.env.NEXT_PUBLIC_DEBUG = "";
      // Re-import to pick up new env
      logger = require("@/lib/logger").logger;
    });

    it("debug should log in development", () => {
      logger.debug("test message");
      expect(consoleSpy.log).toHaveBeenCalledWith("test message");
    });

    it("info should log in development", () => {
      logger.info("info message");
      expect(consoleSpy.info).toHaveBeenCalledWith("info message");
    });

    it("warn should always log", () => {
      logger.warn("warn message");
      expect(consoleSpy.warn).toHaveBeenCalledWith("warn message");
    });

    it("error should always log", () => {
      logger.error("error message");
      expect(consoleSpy.error).toHaveBeenCalledWith("error message");
    });
  });

  describe("in production mode without debug", () => {
    let logger: typeof import("@/lib/logger").logger;

    beforeEach(() => {
      jest.resetModules();
      process.env.NODE_ENV = "production";
      process.env.NEXT_PUBLIC_DEBUG = "";
      logger = require("@/lib/logger").logger;
    });

    it("debug should NOT log in production", () => {
      logger.debug("hidden");
      expect(consoleSpy.log).not.toHaveBeenCalled();
    });

    it("info should NOT log in production", () => {
      logger.info("hidden");
      expect(consoleSpy.info).not.toHaveBeenCalled();
    });

    it("warn should still log in production", () => {
      logger.warn("visible warning");
      expect(consoleSpy.warn).toHaveBeenCalledWith("visible warning");
    });

    it("error should still log in production", () => {
      logger.error("visible error");
      expect(consoleSpy.error).toHaveBeenCalledWith("visible error");
    });
  });

  describe("with NEXT_PUBLIC_DEBUG=true in production", () => {
    let logger: typeof import("@/lib/logger").logger;

    beforeEach(() => {
      jest.resetModules();
      process.env.NODE_ENV = "production";
      process.env.NEXT_PUBLIC_DEBUG = "true";
      logger = require("@/lib/logger").logger;
    });

    it("debug should log when debug flag is set", () => {
      logger.debug("debug enabled");
      expect(consoleSpy.log).toHaveBeenCalledWith("debug enabled");
    });

    it("info should log when debug flag is set", () => {
      logger.info("info enabled");
      expect(consoleSpy.info).toHaveBeenCalledWith("info enabled");
    });
  });
});

describe("wsLogger", () => {
  let consoleSpy: {
    log: jest.SpyInstance;
    error: jest.SpyInstance;
  };
  let wsLogger: typeof import("@/lib/logger").wsLogger;

  beforeEach(() => {
    jest.resetModules();
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_DEBUG = "";

    consoleSpy = {
      log: jest.spyOn(console, "log").mockImplementation(),
      error: jest.spyOn(console, "error").mockImplementation(),
    };

    wsLogger = require("@/lib/logger").wsLogger;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("connected should log connection message", () => {
    wsLogger.connected();
    expect(consoleSpy.log).toHaveBeenCalledWith("[WS] Connected");
  });

  it("disconnected should log code and reason", () => {
    wsLogger.disconnected(1000, "Normal closure");
    expect(consoleSpy.log).toHaveBeenCalledWith(
      "[WS] Disconnected:",
      1000,
      "Normal closure"
    );
  });

  it("reconnecting should log attempt info", () => {
    wsLogger.reconnecting(2, 5);
    expect(consoleSpy.log).toHaveBeenCalledWith("[WS] Reconnecting (2/5)...");
  });

  it("subscribed should log channel name", () => {
    wsLogger.subscribed("ticker:BTC");
    expect(consoleSpy.log).toHaveBeenCalledWith(
      "[WS] Subscribed to ticker:BTC"
    );
  });

  it("unsubscribed should log channel name", () => {
    wsLogger.unsubscribed("ticker:BTC");
    expect(consoleSpy.log).toHaveBeenCalledWith(
      "[WS] Unsubscribed from ticker:BTC"
    );
  });

  it("message should log type and data", () => {
    wsLogger.message("price_update", { price: 100 });
    expect(consoleSpy.log).toHaveBeenCalledWith("[WS] price_update:", {
      price: 100,
    });
  });

  it("error should log formatted Error instance", () => {
    wsLogger.error(new Error("Connection failed"));
    expect(consoleSpy.error).toHaveBeenCalledWith(
      "[WS] Error:",
      "Connection failed"
    );
  });

  it("error should log string errors", () => {
    wsLogger.error("timeout");
    expect(consoleSpy.error).toHaveBeenCalledWith("[WS] Error:", "timeout");
  });

  it("error should log object with message property", () => {
    wsLogger.error({ message: "custom error" });
    expect(consoleSpy.error).toHaveBeenCalledWith(
      "[WS] Error:",
      "custom error"
    );
  });

  it("error should handle unknown error types", () => {
    wsLogger.error(42);
    expect(consoleSpy.error).toHaveBeenCalledWith(
      "[WS] Error:",
      "Unknown error"
    );
  });

  it("parseError should log parse errors", () => {
    wsLogger.parseError(new Error("Invalid JSON"));
    expect(consoleSpy.error).toHaveBeenCalledWith(
      "[WS] Parse error:",
      "Invalid JSON"
    );
  });
});
