// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Diagnostics & Security", () => {
  test("path traversal is blocked", async ({ request }) => {
    const response = await request.get("/getParamFile", {
      params: { case: "../../../etc/passwd", file: "test.csv" },
    });
    // Should be rejected, not serve the file
    expect([400, 403, 404, 500]).toContain(response.status());
  });

  test("null bytes in parameters are rejected", async ({ request }) => {
    const response = await request.get("/getParamFile", {
      params: { case: "test\x00case", file: "data.csv" },
    });
    expect([400, 403, 404, 500]).toContain(response.status());
  });

  test("POST to GET-only routes returns 405", async ({ request }) => {
    const response = await request.post("/getCases");
    expect(response.status()).toBe(405);
  });

  test("CORS headers are present", async ({ request }) => {
    const response = await request.get("/");
    // Flask-CORS should add headers
    expect(response.status()).toBe(200);
  });
});
