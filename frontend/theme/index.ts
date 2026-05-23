import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react";

const config = defineConfig({
  cssVarsPrefix: "ccg",
  globalCss: {
    "html, body": {
      bg: "bg.canvas",
      color: "fg",
      lineHeight: "1.6",
    },
  },
  theme: {
    tokens: {
      colors: {
        brand: {
          50: { value: "#f0f9ff" },
          100: { value: "#e0f2fe" },
          500: { value: "#22c55e" },
          600: { value: "#22c55e" },
          700: { value: "#22c55e" },
        },
      },
    },
  },
});

export const system = createSystem(defaultConfig, config);
