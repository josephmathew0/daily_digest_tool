import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        panel: "#f7f8f5",
        line: "#d9ded8",
        signal: "#0f766e",
        warn: "#b45309",
        danger: "#b91c1c"
      }
    }
  },
  plugins: []
};

export default config;
