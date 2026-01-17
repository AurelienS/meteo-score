import type { Component } from 'solid-js';
import { useI18n } from '../contexts/I18nContext';

/**
 * Language switcher component.
 * Toggles between French and English.
 */
const LanguageSwitcher: Component = () => {
  const { language, setLanguage } = useI18n();

  return (
    <div class="flex items-center text-sm font-medium">
      <button
        onClick={() => setLanguage('fr')}
        class={`px-2 py-1 rounded-l transition-colors ${
          language() === 'fr'
            ? 'bg-white/20 font-bold'
            : 'hover:bg-white/10'
        }`}
        aria-label="Français"
        aria-pressed={language() === 'fr'}
      >
        FR
      </button>
      <span class="opacity-50">|</span>
      <button
        onClick={() => setLanguage('en')}
        class={`px-2 py-1 rounded-r transition-colors ${
          language() === 'en'
            ? 'bg-white/20 font-bold'
            : 'hover:bg-white/10'
        }`}
        aria-label="English"
        aria-pressed={language() === 'en'}
      >
        EN
      </button>
    </div>
  );
};

export default LanguageSwitcher;
