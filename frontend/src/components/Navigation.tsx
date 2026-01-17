import { createSignal, type Component } from 'solid-js';
import { Show } from 'solid-js';
import { A } from '@solidjs/router';
import ThemeToggle from './ThemeToggle';
import LanguageSwitcher from './LanguageSwitcher';
import { useI18n } from '../contexts/I18nContext';

/**
 * Navigation header component.
 * Provides responsive navigation with links to main pages.
 * Includes mobile hamburger menu for smaller screens.
 * Includes theme toggle for dark/light mode.
 * Includes language switcher for FR/EN.
 */
const Navigation: Component = () => {
  const [isMenuOpen, setIsMenuOpen] = createSignal(false);
  const { t } = useI18n();

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen());

  return (
    <nav
      class="sticky top-0 z-50 shadow-md transition-colors"
      style={{
        "background-color": "var(--color-nav-bg)",
        "color": "var(--color-nav-text)",
      }}
    >
      <div class="container mx-auto px-4">
        <div class="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <A href="/" class="flex items-center space-x-2 hover:opacity-90 transition-opacity">
            <span class="text-2xl font-bold">{t('brand')}</span>
          </A>

          {/* Desktop Navigation Links */}
          <div class="hidden md:flex items-center space-x-6">
            <A
              href="/"
              class="hover:opacity-80 transition-opacity font-medium"
              activeClass="underline underline-offset-4"
              end
            >
              {t('nav.home')}
            </A>
            <A
              href="/methodology"
              class="hover:opacity-80 transition-opacity font-medium"
              activeClass="underline underline-offset-4"
            >
              {t('nav.methodology')}
            </A>
            <LanguageSwitcher />
            <ThemeToggle />
          </div>

          {/* Mobile: Language + Theme Toggle + Hamburger */}
          <div class="md:hidden flex items-center space-x-2">
            <LanguageSwitcher />
            <ThemeToggle />
            <button
              class="p-2 rounded hover:bg-white/10 transition-colors"
              onClick={toggleMenu}
              aria-label={isMenuOpen() ? 'Close menu' : 'Open menu'}
              aria-expanded={isMenuOpen()}
            >
              <Show
                when={isMenuOpen()}
                fallback={
                  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                }
              >
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Show>
            </button>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        <Show when={isMenuOpen()}>
          <div
            class="md:hidden pb-4 border-t transition-colors"
            style={{ "border-color": "var(--color-border)" }}
          >
            <div class="flex flex-col space-y-2 pt-4">
              <A
                href="/"
                class="px-2 py-2 rounded hover:bg-white/10 transition-colors font-medium"
                activeClass="bg-white/10"
                onClick={() => setIsMenuOpen(false)}
                end
              >
                {t('nav.home')}
              </A>
              <A
                href="/methodology"
                class="px-2 py-2 rounded hover:bg-white/10 transition-colors font-medium"
                activeClass="bg-white/10"
                onClick={() => setIsMenuOpen(false)}
              >
                {t('nav.methodology')}
              </A>
            </div>
          </div>
        </Show>
      </div>
    </nav>
  );
};

export default Navigation;
