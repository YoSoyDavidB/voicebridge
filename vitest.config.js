const { defineConfig } = require("vitest/config");

module.exports = defineConfig({
  test: {
    environment: "node",
    include: ["src/voicebridge/web/static/js/__tests__/**/*.test.js"]
  }
});
