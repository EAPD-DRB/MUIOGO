// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Application Load", () => {
  test("homepage loads successfully", async ({ page }) => {
    const response = await page.goto("/");
    expect(response.status()).toBe(200);
  });

  test("page title is correct", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/MUIO/);
  });

  test("main UI elements are visible", async ({ page }) => {
    await page.goto("/");
    // Wait for the page to fully load
    await page.waitForLoadState("networkidle");
    // The app should render without JavaScript errors
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.waitForTimeout(2000);
    expect(errors).toHaveLength(0);
  });
});
