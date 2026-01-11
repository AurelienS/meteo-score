import type { Component } from 'solid-js';

/**
 * About page component.
 * Displays methodology and project information.
 */
const About: Component = () => {
  return (
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">
        About MétéoScore
      </h1>
      <div class="bg-white rounded-lg shadow-md p-6 space-y-4">
        <section>
          <h2 class="text-xl font-semibold text-gray-800 mb-2">Project Overview</h2>
          <p class="text-gray-600">
            MétéoScore is a weather forecast accuracy comparison platform designed for paragliding pilots.
            We collect forecasts from multiple weather models and compare them against actual observations
            to help pilots make informed decisions.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-semibold text-gray-800 mb-2">Methodology</h2>
          <p class="text-gray-600">
            Our accuracy metrics are calculated by comparing forecast values against observations
            from official weather stations. We compute deviations for key parameters including
            wind speed, wind direction, and temperature.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-semibold text-gray-800 mb-2">Data Sources</h2>
          <p class="text-gray-600">
            We aggregate data from multiple forecast models including AROME and Meteo-Parapente,
            validated against observations from ROMMA and FFVL beacon networks.
          </p>
        </section>
      </div>
    </div>
  );
};

export default About;
