import { createSignal, type Component } from 'solid-js';
import { Show } from 'solid-js';
import { A } from '@solidjs/router';

/**
 * Navigation header component.
 * Provides responsive navigation with links to main pages.
 * Includes mobile hamburger menu for smaller screens.
 */
const Navigation: Component = () => {
  const [isMenuOpen, setIsMenuOpen] = createSignal(false);

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen());

  return (
    <nav class="bg-blue-600 text-white sticky top-0 z-50 shadow-md">
      <div class="container mx-auto px-4">
        <div class="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <A href="/" class="flex items-center space-x-2 hover:opacity-90 transition-opacity">
            <span class="text-2xl font-bold">MétéoScore</span>
          </A>

          {/* Desktop Navigation Links */}
          <div class="hidden md:flex items-center space-x-6">
            <A
              href="/"
              class="hover:text-blue-200 transition-colors font-medium"
              activeClass="text-blue-200 underline underline-offset-4"
              end
            >
              Home
            </A>
            <A
              href="/methodology"
              class="hover:text-blue-200 transition-colors font-medium"
              activeClass="text-blue-200 underline underline-offset-4"
            >
              Methodology
            </A>
          </div>

          {/* Mobile Hamburger Button */}
          <button
            class="md:hidden p-2 rounded hover:bg-blue-700 transition-colors"
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

        {/* Mobile Menu Dropdown */}
        <Show when={isMenuOpen()}>
          <div class="md:hidden pb-4 border-t border-blue-500">
            <div class="flex flex-col space-y-2 pt-4">
              <A
                href="/"
                class="px-2 py-2 rounded hover:bg-blue-700 transition-colors font-medium"
                activeClass="bg-blue-700"
                onClick={() => setIsMenuOpen(false)}
                end
              >
                Home
              </A>
              <A
                href="/methodology"
                class="px-2 py-2 rounded hover:bg-blue-700 transition-colors font-medium"
                activeClass="bg-blue-700"
                onClick={() => setIsMenuOpen(false)}
              >
                Methodology
              </A>
            </div>
          </div>
        </Show>
      </div>
    </nav>
  );
};

export default Navigation;
