// @ts-check
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests",
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:5002",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "python ../API/app.py",
    url: "http://127.0.0.1:5002",
    timeout: 30000,
    reuseExistingServer: true,
  },
  reporter: [["html", { open: "never" }], ["list"]],
});
