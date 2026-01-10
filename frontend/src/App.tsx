import type { Component } from 'solid-js';

const App: Component = () => {
  return (
    <div class="min-h-screen bg-gray-50">
      <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">Meteo Score</h1>
        <p class="text-sm">Meteorological Forecast Scoring System</p>
      </header>
      <main class="container mx-auto p-4">
        <div class="bg-white rounded-lg shadow p-6 mt-4">
          <h2 class="text-xl font-semibold mb-2">Welcome to Meteo Score</h2>
          <p class="text-gray-600">
            The application structure has been initialized successfully.
          </p>
        </div>
      </main>
    </div>
  );
};

export default App;
