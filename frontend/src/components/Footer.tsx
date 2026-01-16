import type { Component } from 'solid-js';

/** GitHub repository URL for the project */
const GITHUB_URL = 'https://github.com/AurelienS/meteo-score';

/** Current year (computed once at module load) */
const CURRENT_YEAR = new Date().getFullYear();

/**
 * Footer component.
 * Displays copyright information and links to project resources.
 */
const Footer: Component = () => {

  return (
    <footer class="bg-white border-t border-gray-200 shadow-sm mt-12">
      <div class="container mx-auto px-4 py-6">
        <div class="flex flex-col md:flex-row items-center justify-between gap-4">
          <p class="text-sm text-gray-500 text-center md:text-left">
            MétéoScore - Open Source Weather Forecast Accuracy Platform
          </p>
          <div class="flex items-center gap-4">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              class="text-sm text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="View MétéoScore source code on GitHub"
            >
              View on GitHub
            </a>
            <span class="text-sm text-gray-400">
              © {CURRENT_YEAR}
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
