/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        amic: {
          DEFAULT: "#0F3A32",
          50: "#E8F5E9",
          100: "#F1F8E9",
          200: "#C8E6C9",
          300: "#A5D6A7",
          400: "#66BB6A",
          500: "#26C260",
          600: "#0F3A32",
          700: "#0B2D27",
          800: "#07201C",
          900: "#041411",
        },
        accent: { DEFAULT: "#26C260", hover: "#1FAA52" },
        positive: "#26C260",
        negative: "#BC2C1A",
        caution: "#EF6C00",
        "text-body": "#3D3D3D",
        "text-dark": "#212121",
        "text-secondary": "#777777",
        "bg-cool": "#F4F6F8",
        "bg-light-green": "#E8F5E9",
        "table-header": "#0F3A32",
        "table-alt": "#F4F6F8",
        "gray-border": "#E0E0E0",
      },
      fontFamily: {
        heading: [
          "'Inter'",
          "'Pretendard'",
          "'Noto Sans KR'",
          "sans-serif",
        ],
        body: [
          "'Pretendard'",
          "'Inter'",
          "'Noto Sans KR'",
          "'Malgun Gothic'",
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
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(0,0,0,0.08), 0 1px 2px -1px rgba(0,0,0,0.04)",
        "card-hover":
          "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.06)",
      },
    },
  },
  plugins: [],
};
