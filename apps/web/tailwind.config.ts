import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--bg-base)",
        surface: {
          DEFAULT: "var(--bg-surface)",
          raised: "var(--bg-surface-raised)",
          hover: "var(--bg-surface-hover)",
          active: "var(--bg-surface-active)",
        },
        foreground: {
          DEFAULT: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          disabled: "var(--text-disabled)",
        },
        accent: {
          DEFAULT: "var(--accent-primary)",
          soft: "var(--accent-primary-soft)",
          cyan: "var(--accent-cyan)",
          blue: "var(--accent-blue)",
        },
        state: {
          success: "var(--state-success)",
          warning: "var(--state-warning)",
          error: "var(--state-error)",
          info: "var(--state-info)",
        },
        border: {
          DEFAULT: "var(--border-default)",
          strong: "var(--border-strong)",
          active: "var(--border-active)",
        },
        thermal: {
          DEFAULT: "var(--thermal-primary)",
          hot: "var(--thermal-hot)",
          glow: "var(--thermal-glow)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        control: "4px",
        panel: "6px",
        overlay: "8px",
        pill: "9999px",
      },
      boxShadow: {
        panel: "0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 0 1px var(--border-default)",
        "panel-glow": "0 0 25px -5px rgba(57, 255, 136, 0.15), 0 0 0 1px var(--border-active)",
        "thermal-glow": "0 0 25px -2px rgba(255, 106, 0, 0.35)",
        inset: "inset 0 1px 0 0 rgba(255, 255, 255, 0.05)",
      },
      animation: {
        "pulse-subtle": "pulseSubtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "thermal-pulse": "thermalPulse 1.8s ease-in-out infinite",
        "radar-sweep": "radarSweep 6s linear infinite",
      },
      keyframes: {
        pulseSubtle: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        thermalPulse: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.9" },
          "50%": { transform: "scale(1.08)", opacity: "1" },
        },
        radarSweep: {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
