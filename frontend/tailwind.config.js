/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Hermes official style - blue theme
        primary: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',  // Main blue
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
          900: '#1E3A8A',
        },
        // Neutral grayscale
        surface: {
          light: '#FFFFFF',
          dark: '#111827',
        },
        background: {
          light: '#F9FAFB',
          dark: '#0F172A',
        },
        // Semantic colors → CSS variables (single source of truth)
        profit:  'var(--profit)',
        loss:    'var(--loss)',
        success: 'var(--success)',
        error:   'var(--error)',
        warning: 'var(--warning)',
        accent:  'var(--accent)',
        // Dark variants for dark: prefix
        profitDark:  '#4ADE80',
        lossDark:    '#F87171',
        successDark: '#34D399',
        errorDark:   '#F87171',
        warningDark: '#FBBF24',
        accentDark:  '#60A5FA',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      screens: {
        'xs': '375px',   // iPhone SE
        'sm': '640px',   // Small phones
        'md': '768px',   // iPad portrait
        'lg': '1024px',  // iPad landscape / small laptops
        'xl': '1280px',  // MacBook Air size
        '2xl': '1536px', // Large screens
      },
      spacing: {
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
      },
    },
  },
  plugins: [],
}