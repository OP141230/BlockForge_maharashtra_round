/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:             "#EEF2F7",
        "sidebar-bg":   "#F0F4FA",
        panel:          "rgba(255,255,255,0.92)",
        "panel-raised": "#FFFFFF",
        "panel-border": "rgba(220,228,242,0.9)",
        border:         "#DDE3EE",
        "border-strong":"#C8D0E0",
        "text-primary": "#1A2236",
        "text-muted":   "#6B7A99",
        "text-faint":   "#9BA8BF",
        primary:        "#3B82F6",
        intel:          "#7C5CFF",
        success:        "#22C55E",
        warning:        "#F59E0B",
        danger:         "#EF4444",
        "sidebar-active":"#E8EEFF",
      },
      boxShadow: {
        card:        "0 2px 12px rgba(26,34,54,0.06)",
        panel:       "0 8px 32px rgba(26,34,54,0.10)",
        "glow-amber":"0 0 28px rgba(245,158,11,0.50)",
        "glow-red":  "0 0 20px rgba(239,68,68,0.40)",
        "glow-blue": "0 0 20px rgba(59,130,246,0.35)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      borderRadius: {
        "2xl": "16px",
        "3xl": "20px",
      },
    },
  },
  plugins: [],
};
