/**
 * Tests for crypto transport encryption utility
 *
 * Note: Due to module caching, these tests use jest.doMock to set up mocks
 * before importing the module in each test.
 */

describe("crypto utilities", () => {
  describe("isTransportEncryptionEnabled", () => {
    it("returns false when server returns error", async () => {
      jest.doMock("@/lib/api/client", () => ({
        api: {
          get: jest.fn().mockRejectedValue(new Error("Not enabled")),
        },
      }));

      const { isTransportEncryptionEnabled } = await import("@/lib/crypto");
      const result = await isTransportEncryptionEnabled();

      expect(result).toBe(false);
    });
  });

  describe("encryptForTransport", () => {
    it("returns plaintext when encryption not available", async () => {
      jest.doMock("@/lib/api/client", () => ({
        api: {
          get: jest.fn().mockRejectedValue(new Error("Not enabled")),
        },
      }));

      const { encryptForTransport } = await import("@/lib/crypto");
      const result = await encryptForTransport("secret-data");

      expect(result).toBe("secret-data");
    });
  });

  describe("encryptFields", () => {
    it("returns original data when encryption not enabled", async () => {
      jest.doMock("@/lib/api/client", () => ({
        api: {
          get: jest.fn().mockRejectedValue(new Error("Not enabled")),
        },
      }));

      const { encryptFields } = await import("@/lib/crypto");
      const data = { api_key: "secret", name: "test" };
      const result = await encryptFields(data, ["api_key"]);

      expect(result).toEqual(data);
    });

    it("preserves object structure", async () => {
      jest.doMock("@/lib/api/client", () => ({
        api: {
          get: jest.fn().mockRejectedValue(new Error("Not enabled")),
        },
      }));

      const { encryptFields } = await import("@/lib/crypto");
      const data = { name: "test", count: 5, nested: { key: "value" } };
      const result = await encryptFields(data, ["api_key"]);

      expect(result).toEqual(data);
    });

    it("handles non-string fields gracefully", async () => {
      jest.doMock("@/lib/api/client", () => ({
        api: {
          get: jest.fn().mockRejectedValue(new Error("Not enabled")),
        },
      }));

      const { encryptFields } = await import("@/lib/crypto");
      const data = { count: 5, flag: true, empty: "" };
      const result = await encryptFields(data, ["count", "flag", "empty"]);

      expect(result).toEqual(data);
    });
  });
});
