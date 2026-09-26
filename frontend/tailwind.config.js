/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#030712",
        surface: {
          DEFAULT: "#0b0f19",
          hover: "#111827",
          border: "rgba(255, 255, 255, 0.08)",
        },
        cyan: {
          400: "#22d3ee",
          500: "#06b6d4",
          glow: "rgba(6, 182, 212, 0.25)",
        },
        accent: {
          blue: "#3b82f6",
          purple: "#8b5cf6",
          emerald: "#10b981",
          amber: "#f59e0b",
          rose: "#f43f5e",
        },
      },
      fontFamily: {
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
        sans: ["var(--font-sans)", "Inter", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 25px -5px rgba(6, 182, 212, 0.3)",
        "glow-purple": "0 0 25px -5px rgba(139, 92, 246, 0.3)",
      },
    },
  },
  plugins: [],
};
