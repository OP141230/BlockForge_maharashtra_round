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
        bg: "#F4F7FC",
        sidebar: "#FFFFFF",
        panel: "rgba(255, 255, 255, 0.85)",
        "panel-border": "rgba(226, 232, 240, 0.8)",
        "text-primary": "#0F172A",
        "text-muted": "#64748B",
        primary: "#3B82F6",
        intel: "#7C5CFF",
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(31, 38, 135, 0.07)",
        "glow-amber": "0 0 25px rgba(245, 158, 11, 0.45)",
        "glow-red": "0 0 25px rgba(239, 68, 68, 0.35)",
        "glow-blue": "0 0 25px rgba(59, 130, 246, 0.35)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
