// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Navigation", () => {
  test("root path serves the frontend", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");
    // The page should have HTML content (not a JSON API response)
    const contentType = await page.evaluate(() => document.contentType);
    expect(contentType).toBe("text/html");
  });

  test("unknown API routes return 404", async ({ request }) => {
    const response = await request.get("/api/nonexistent");
    expect([404, 405]).toContain(response.status());
  });

  test("static assets are served", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Check that CSS loaded (bootstrap is used)
    const hasStyles = await page.evaluate(() => {
      return document.styleSheets.length > 0;
    });
    expect(hasStyles).toBeTruthy();
  });
});
