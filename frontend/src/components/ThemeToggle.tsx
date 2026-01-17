import type { Component } from 'solid-js';
import { useTheme } from '../contexts/ThemeContext';

/**
 * Theme toggle button with sun/moon icons.
 * Switches between light and dark themes.
 */
const ThemeToggle: Component = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      class="p-2 rounded-lg transition-colors hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/20"
      aria-label={theme() === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
      title={theme() === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
    >
      {theme() === 'light' ? (
        // Moon icon for light mode (click to go dark)
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      ) : (
        // Sun icon for dark mode (click to go light)
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      )}
    </button>
  );
};

export default ThemeToggle;
