import type { Config } from "tailwindcss";

const neutral = {
  50: "#f7f7f7",
  100: "#eaeaea",
  200: "#d0d0d0",
  300: "#b4b4b4",
  400: "#888888",
  500: "#6e6e6e",
  600: "#555555",
  700: "#454545",
  800: "#2e2e2e",
  900: "#171717",
  950: "#0e0e0e",
  DEFAULT: "#171717",
};

const lime = {
  50: "#f6ffe0",
  100: "#edffb3",
  200: "#e2ff80",
  300: "#d6ff4d",
  400: "#c6ff26",
  500: "#b7ff00",
  600: "#95ce00",
  700: "#749f00",
  800: "#5b7d00",
  900: "#4b6600",
  950: "#263300",
  DEFAULT: "#b7ff00",
};

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border) / <alpha-value>)",
        input: "hsl(var(--input) / <alpha-value>)",
        ring: "hsl(var(--ring) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        primary: {
          DEFAULT: "hsl(var(--primary) / <alpha-value>)",
          foreground: "hsl(var(--primary-foreground) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary) / <alpha-value>)",
          foreground: "hsl(var(--secondary-foreground) / <alpha-value>)",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive) / <alpha-value>)",
          foreground: "hsl(var(--destructive-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
        },
        popover: {
          DEFAULT: "hsl(var(--popover) / <alpha-value>)",
          foreground: "hsl(var(--popover-foreground) / <alpha-value>)",
        },
        card: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          foreground: "hsl(var(--card-foreground) / <alpha-value>)",
        },
        success: {
          DEFAULT: "hsl(var(--success) / <alpha-value>)",
          foreground: "hsl(var(--success-foreground) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "hsl(var(--warning) / <alpha-value>)",
          foreground: "hsl(var(--warning-foreground) / <alpha-value>)",
        },
        danger: {
          DEFAULT: "hsl(var(--danger) / <alpha-value>)",
          foreground: "hsl(var(--danger-foreground) / <alpha-value>)",
        },
        blue: neutral,
        indigo: neutral,
        violet: lime,
        emerald: neutral,
        slate: neutral,
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Funnel Display", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["Turret Road", "Funnel Display", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Consolas", "monospace"],
      },
      boxShadow: {
        soft: "0 18px 50px -24px rgba(23, 23, 23, 0.35)",
        glow: "0 0 0 1px rgba(183, 255, 0, 0.35), 0 20px 60px -30px rgba(183, 255, 0, 0.45)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
