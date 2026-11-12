import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: ".",
  testMatch: "desk.spec.ts",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8787", headless: true },
  webServer: {
    command:
      "npx wrangler d1 execute roleproof-desk-demo --local --file schema.sql && npx wrangler dev --port 8787 --ip 127.0.0.1",
    url: "http://127.0.0.1:8787/api/health",
    reuseExistingServer: false,
    gracefulShutdown: { signal: "SIGTERM", timeout: 5000 },
  },
  reporter: [["list"]],
});
