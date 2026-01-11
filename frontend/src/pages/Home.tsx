import type { Component } from 'solid-js';

/**
 * Home page component.
 * Displays main landing page with placeholder content.
 */
const Home: Component = () => {
  return (
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">
        MétéoScore - Home
      </h1>
      <div class="bg-white rounded-lg shadow-md p-6">
        <p class="text-gray-600 mb-4">
          Compare weather forecast accuracy across different models for paragliding sites.
        </p>
        <p class="text-gray-500 text-sm">
          Select a site to view detailed forecast comparisons and accuracy metrics.
        </p>
      </div>
    </div>
  );
};

export default Home;
