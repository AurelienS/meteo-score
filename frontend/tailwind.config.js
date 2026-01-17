/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist Sans', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        // Custom color palette for MétéoScore
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        // Theme-aware colors using CSS variables
        theme: {
          bg: {
            primary: 'var(--color-bg-primary)',
            secondary: 'var(--color-bg-secondary)',
            tertiary: 'var(--color-bg-tertiary)',
          },
          text: {
            primary: 'var(--color-text-primary)',
            secondary: 'var(--color-text-secondary)',
            tertiary: 'var(--color-text-tertiary)',
            muted: 'var(--color-text-muted)',
          },
          border: {
            primary: 'var(--color-border-primary)',
            secondary: 'var(--color-border-secondary)',
          },
        },
        // Semantic status colors with theme support
        status: {
          success: {
            bg: 'var(--color-status-success-bg)',
            text: 'var(--color-status-success-text)',
            border: 'var(--color-status-success-border)',
          },
          warning: {
            bg: 'var(--color-status-warning-bg)',
            text: 'var(--color-status-warning-text)',
            border: 'var(--color-status-warning-border)',
          },
          error: {
            bg: 'var(--color-status-error-bg)',
            text: 'var(--color-status-error-text)',
            border: 'var(--color-status-error-border)',
          },
        },
      },
    },
  },
  plugins: [],
}
