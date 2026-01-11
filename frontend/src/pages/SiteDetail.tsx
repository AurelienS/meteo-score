import type { Component } from 'solid-js';
import { useParams } from '@solidjs/router';

/**
 * Site detail page component.
 * Displays individual site information with route parameter.
 */
const SiteDetail: Component = () => {
  const params = useParams();

  return (
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">
        Site Details
      </h1>
      <div class="bg-white rounded-lg shadow-md p-6">
        <p class="text-gray-600 mb-4">
          Viewing site with ID: <span class="font-mono font-bold text-blue-600">{params.id}</span>
        </p>
        <p class="text-gray-500 text-sm">
          Model comparison and accuracy metrics will be displayed here.
        </p>
      </div>
    </div>
  );
};

export default SiteDetail;
