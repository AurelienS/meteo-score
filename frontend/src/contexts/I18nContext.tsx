import {
  createContext,
  useContext,
  createSignal,
  onMount,
  type ParentComponent,
  type Accessor,
} from 'solid-js';

import frTranslations from '../locales/fr.json';
import enTranslations from '../locales/en.json';

type Language = 'fr' | 'en';

type TranslationValue = string | { [key: string]: TranslationValue };
type Translations = { [key: string]: TranslationValue };

interface I18nContextValue {
  language: Accessor<Language>;
  setLanguage: (lang: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue>();

const STORAGE_KEY = 'meteo-score-language';

const translations: Record<Language, Translations> = {
  fr: frTranslations,
  en: enTranslations,
};

/**
 * Detect browser language, defaulting to French.
 */
function detectBrowserLanguage(): Language {
  if (typeof navigator !== 'undefined') {
    const browserLang = navigator.language.toLowerCase();
    if (browserLang.startsWith('en')) {
      return 'en';
    }
  }
  // Default to French
  return 'fr';
}

/**
 * Get initial language from localStorage or browser detection.
 */
function getInitialLanguage(): Language {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'fr' || stored === 'en') {
      return stored;
    }
  }
  return detectBrowserLanguage();
}

/**
 * Get nested translation value by dot-separated key.
 */
function getNestedValue(obj: Translations, path: string): string | undefined {
  const keys = path.split('.');
  let current: TranslationValue | undefined = obj;

  for (const key of keys) {
    if (current === undefined || typeof current === 'string') {
      return undefined;
    }
    current = current[key];
  }

  return typeof current === 'string' ? current : undefined;
}

/**
 * I18nProvider component that manages language state and provides translations.
 */
export const I18nProvider: ParentComponent = (props) => {
  const [language, setLanguageSignal] = createSignal<Language>(getInitialLanguage());

  const setLanguage = (lang: Language): void => {
    setLanguageSignal(lang);
    localStorage.setItem(STORAGE_KEY, lang);
    // Update document lang attribute for accessibility
    if (typeof document !== 'undefined') {
      document.documentElement.lang = lang;
      // Update document title based on language
      document.title = lang === 'fr' ? 'Météo Score' : 'Meteo Score';
    }
  };

  // Set initial document language and title
  onMount(() => {
    const lang = language();
    document.documentElement.lang = lang;
    document.title = lang === 'fr' ? 'Météo Score' : 'Meteo Score';
  });

  /**
   * Translation function.
   * @param key - Dot-separated key (e.g., 'nav.home')
   * @param params - Optional parameters for interpolation (e.g., {count: 5})
   */
  const t = (key: string, params?: Record<string, string | number>): string => {
    const currentTranslations = translations[language()];
    let value = getNestedValue(currentTranslations, key);

    if (value === undefined) {
      // Fallback to French, then return key if not found
      value = getNestedValue(translations.fr, key);
      if (value === undefined) {
        console.warn(`Translation missing for key: ${key}`);
        return key;
      }
    }

    // Simple parameter interpolation: {{param}}
    if (params) {
      for (const [paramKey, paramValue] of Object.entries(params)) {
        value = value.replace(new RegExp(`{{${paramKey}}}`, 'g'), String(paramValue));
      }
    }

    return value;
  };

  const contextValue: I18nContextValue = {
    language,
    setLanguage,
    t,
  };

  return (
    <I18nContext.Provider value={contextValue}>
      {props.children}
    </I18nContext.Provider>
  );
};

/**
 * Hook to access i18n context.
 */
export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

export type { Language };
