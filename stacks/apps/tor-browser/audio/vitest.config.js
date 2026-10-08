import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/unit/**/*.test.js", "tests/integration/**/*.test.js"],
    maxWorkers: 2,
    testTimeout: 15000,
    hookTimeout: 30000,
  },
});
