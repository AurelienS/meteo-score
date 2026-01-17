import { createContext, useContext, createSignal, onMount, type ParentComponent, type Accessor } from 'solid-js';

type Theme = 'light' | 'dark';

interface ThemeContextValue {
  theme: Accessor<Theme>;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue>();

const STORAGE_KEY = 'meteo-score-theme';

/**
 * Get the initial theme from localStorage or system preference.
 * This is also used in the inline script in index.html to prevent FOUC.
 */
function getInitialTheme(): Theme {
  // Check localStorage first
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }
    // Fall back to system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
  }
  return 'light';
}

/**
 * Apply theme class to document root.
 */
function applyTheme(theme: Theme): void {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }
}

/**
 * ThemeProvider component that manages theme state and provides context.
 */
export const ThemeProvider: ParentComponent = (props) => {
  const [theme, setThemeSignal] = createSignal<Theme>(getInitialTheme());

  // Apply theme on mount and when it changes
  onMount(() => {
    applyTheme(theme());
  });

  const setTheme = (newTheme: Theme): void => {
    setThemeSignal(newTheme);
    applyTheme(newTheme);
    localStorage.setItem(STORAGE_KEY, newTheme);
  };

  const toggleTheme = (): void => {
    const newTheme = theme() === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
  };

  // Listen for system preference changes
  onMount(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent): void => {
      // Only auto-switch if user hasn't set a preference
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };
    mediaQuery.addEventListener('change', handleChange);
    // Cleanup not needed in Solid.js for this use case
  });

  const value: ThemeContextValue = {
    theme,
    toggleTheme,
    setTheme,
  };

  return (
    <ThemeContext.Provider value={value}>
      {props.children}
    </ThemeContext.Provider>
  );
};

/**
 * Hook to access theme context.
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export type { Theme };
