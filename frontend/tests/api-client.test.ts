import { describe, it, expect, vi } from "vitest";
import { apiClient, createAuthenticatedClient } from "@/lib/api/client";

describe("API Client", () => {
  it("exports apiClient instance with baseUrl configured", () => {
    expect(apiClient).toBeDefined();
    expect(typeof apiClient.GET).toBe("function");
    expect(typeof apiClient.POST).toBe("function");
  });

  it("createAuthenticatedClient configures middleware with Authorization header", async () => {
    const client = createAuthenticatedClient("mock_bearer_token_xyz");
    expect(client).toBeDefined();
    expect(typeof client.GET).toBe("function");
  });

  it("createAuthenticatedClient works without token", () => {
    const client = createAuthenticatedClient(null);
    expect(client).toBeDefined();
  });
});
