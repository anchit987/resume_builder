import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./client/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        brand: {
          purple: {
            50: "hsl(270 100% 98%)",
            100: "hsl(269 100% 95%)",
            200: "hsl(269 100% 92%)",
            300: "hsl(268 100% 86%)",
            400: "hsl(270 95% 75%)",
            500: "hsl(270 91% 65%)",
            600: "hsl(271 81% 56%)",
            700: "hsl(272 72% 47%)",
            800: "hsl(272 69% 38%)",
            900: "hsl(273 69% 32%)",
            950: "hsl(274 87% 21%)",
          },
          blue: {
            50: "hsl(213 100% 97%)",
            100: "hsl(214 95% 93%)",
            200: "hsl(213 97% 87%)",
            300: "hsl(212 96% 78%)",
            400: "hsl(213 94% 68%)",
            500: "hsl(217 91% 60%)",
            600: "hsl(221 83% 53%)",
            700: "hsl(224 76% 48%)",
            800: "hsl(226 71% 40%)",
            900: "hsl(224 64% 33%)",
            950: "hsl(226 55% 21%)",
          },
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: {
            height: "0",
          },
          to: {
            height: "var(--radix-accordion-content-height)",
          },
        },
        "accordion-up": {
          from: {
            height: "var(--radix-accordion-content-height)",
          },
          to: {
            height: "0",
          },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
