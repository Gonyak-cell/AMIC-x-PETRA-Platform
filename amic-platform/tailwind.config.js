/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        amic: {
          DEFAULT: "#0F3A32",
          50: "#EDF5F3",
          100: "#D5E8E3",
          200: "#A8D1C7",
          300: "#6BAA9B",
          400: "#3D7D6E",
          500: "#1A5A4C",
          600: "#0F3A32",
          700: "#0B2D27",
          800: "#07201C",
          900: "#041411",
        },
        accent: { DEFAULT: "#26C260", hover: "#1FAA52", light: "#E8F8ED" },
        positive: "#26C260",
        negative: "#BC2C1A",
        caution: "#EF6C00",
        "text-body": "#3D3D3D",
        "text-dark": "#1A1A1A",
        "text-secondary": "#6B7280",
        "text-muted": "#9CA3AF",
        "bg-cool": "#F7F8FA",
        "bg-light-green": "#E8F8ED",
        "table-header": "#0F3A32",
        "table-alt": "#F7F8FA",
        "gray-border": "#E5E7EB",
        "hero-dark": "#0A2B24",
        "hero-end": "#0F3A32",
        "glass-white": "rgba(255,255,255,0.06)",
        "glass-border": "rgba(255,255,255,0.08)",
        "positive-light": "#E8F8ED",
        "negative-light": "#FEF2F2",
        "caution-light": "#FFFBEB",
        "info-light": "#EFF6FF",
        "accent-hover": "#1FAA52",
        "solid-green": "#1C8F57",
      },
      fontFamily: {
        heading: [
          "'SUITE Variable'",
          "'SUITE'",
          "sans-serif",
        ],
        body: [
          "'Pretendard Variable'",
          "'Pretendard'",
          "sans-serif",
        ],
        display: [
          "'Josefin Sans'",
          "'SUITE Variable'",
          "sans-serif",
        ],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      fontSize: {
        "kpi-value": [
          "1.6875rem",
          { lineHeight: "1.2", fontWeight: "600" },
        ],
        "kpi-label": [
          "0.9375rem",
          { lineHeight: "1.4", fontWeight: "500" },
        ],
        "sub-header": ["1rem", { lineHeight: "1.5", fontWeight: "600" }],
        "body-text": [
          "0.8125rem",
          { lineHeight: "1.6", fontWeight: "400" },
        ],
        footnote: ["0.75rem", { lineHeight: "1.5", fontWeight: "400" }],
        "section-number": [
          "2rem",
          { lineHeight: "1", fontWeight: "700", letterSpacing: "-0.02em" },
        ],
        "page-title": [
          "1.75rem",
          { lineHeight: "1.25", fontWeight: "700", letterSpacing: "-0.02em" },
        ],
        "hero-title": [
          "2.5rem",
          { lineHeight: "1.15", fontWeight: "800", letterSpacing: "-0.03em" },
        ],
        "hero-subtitle": [
          "1.125rem",
          { lineHeight: "1.5", fontWeight: "400" },
        ],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(0,0,0,0.06), 0 1px 2px -1px rgba(0,0,0,0.03)",
        "card-hover":
          "0 4px 12px -2px rgba(0,0,0,0.08), 0 2px 6px -2px rgba(0,0,0,0.04)",
        elevated:
          "0 8px 24px -4px rgba(0,0,0,0.12), 0 4px 8px -4px rgba(0,0,0,0.06)",
        sidebar: "2px 0 8px -2px rgba(0,0,0,0.1)",
        "forest-card": "0 1px 3px 0 rgba(0,0,0,0.04), 0 1px 2px -1px rgba(0,0,0,0.02)",
        "forest-hover": "0 28px 48px rgba(0,0,0,0.18)",
        "forest-subtle": "0 10px 20px rgba(0,0,0,0.08)",
        "dr-sm": "0 2px 8px -2px rgba(15,58,50,0.08)",
        "dr-md":
          "0 8px 24px -4px rgba(15,58,50,0.10), 0 4px 8px -4px rgba(15,58,50,0.06)",
        "dr-lg":
          "0 16px 48px -8px rgba(15,58,50,0.14), 0 8px 16px -4px rgba(15,58,50,0.08)",
        "dr-xl":
          "0 24px 64px -12px rgba(15,58,50,0.18), 0 12px 24px -4px rgba(15,58,50,0.10)",
        "glow-green":
          "0 0 20px rgba(38,194,96,0.15), 0 8px 32px -8px rgba(38,194,96,0.20)",
        "glow-teal":
          "0 0 20px rgba(15,58,50,0.20), 0 8px 32px -8px rgba(15,58,50,0.25)",
      },
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
        26: "6.5rem",
      },
      transitionTimingFunction: {
        forest: "cubic-bezier(0.25, 0.1, 0.25, 1)",
      },
      borderRadius: {
        corporate: "6px",
        dr: "12px",
        "dr-lg": "16px",
        "dr-sm": "8px",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.5s ease-out forwards",
      },
    },
  },
  plugins: [],
};
