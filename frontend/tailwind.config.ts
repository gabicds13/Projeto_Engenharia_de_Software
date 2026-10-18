import type { Config } from "tailwindcss";

// Mapeia os tokens do design-system (CSS variables) para classes utilitárias.
// Nunca use hex direto nos componentes — sempre uma classe daqui.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        primary: "var(--color-primary)",
        "primary-hover": "var(--color-primary-hover)",
        "brand-accent": "var(--color-brand-accent)",
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        border: "var(--color-border)",
        text: "var(--color-text)",
        "text-muted": "var(--color-text-muted)",
        "priority-critical": "var(--color-priority-critical)",
        "priority-high": "var(--color-priority-high)",
        "priority-medium": "var(--color-priority-medium)",
        "priority-low": "var(--color-priority-low)",
        success: "var(--color-success)",
        "chart-1": "var(--chart-1)",
        "chart-2": "var(--chart-2)",
        "chart-3": "var(--chart-3)",
        "chart-4": "var(--chart-4)",
        "chart-5": "var(--chart-5)",
      },
      fontFamily: {
        sans: "var(--font-sans)",
        mono: "var(--font-mono)",
      },
      fontSize: {
        xs: "var(--text-xs)",
        sm: "var(--text-sm)",
        md: "var(--text-md)",
        lg: "var(--text-lg)",
        xl: "var(--text-xl)",
        "2xl": "var(--text-2xl)",
      },
    },
  },
  plugins: [],
} satisfies Config;
