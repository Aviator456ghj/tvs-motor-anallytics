import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef7ff",
          100: "#d9edff",
          200: "#bce0ff",
          300: "#8ecdff",
          400: "#59b1ff",
          500: "#3390ff",
          600: "#1c6fef",
          700: "#1758d1",
          800: "#1a49a8",
          900: "#1b4085",
        },
      },
    },
  },
  plugins: [],
};

export default config;
