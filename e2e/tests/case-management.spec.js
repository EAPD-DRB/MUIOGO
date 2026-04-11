// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Case Management", () => {
  test("GET /getCases returns valid JSON", async ({ request }) => {
    const response = await request.get("/getCases");
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data) || typeof data === "object").toBeTruthy();
  });

  test("GET /getSession returns session info", async ({ request }) => {
    const response = await request.get("/getSession");
    expect(response.status()).toBe(200);
  });

  test("POST /setSession sets session data", async ({ request }) => {
    const response = await request.post("/setSession", {
      data: { key: "testKey", value: "testValue" },
      headers: { "Content-Type": "application/json" },
    });
    expect([200, 204]).toContain(response.status());
  });

  test("GET /getCases with nonexistent case returns appropriate status", async ({
    request,
  }) => {
    const response = await request.get("/getParamFile", {
      params: { case: "nonexistent_case_12345", file: "test.csv" },
    });
    // Should not crash — either 404 or empty result
    expect([200, 404, 400]).toContain(response.status());
  });
});
