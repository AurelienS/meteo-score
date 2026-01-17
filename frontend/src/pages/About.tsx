import type { Component } from 'solid-js';
import { useI18n } from '../contexts/I18nContext';

/**
 * About/Methodology page component.
 * Displays comprehensive methodology documentation including:
 * - How MétéoScore works
 * - Metrics explained (MAE, Bias)
 * - Data sources (forecast models, observation networks)
 * - Data collection process
 * - Confidence levels
 * - Limitations
 * - Open source information
 */
const About: Component = () => {
  const { t } = useI18n();

  return (
    <div class="container mx-auto px-4 py-8">
      <div class="max-w-4xl mx-auto">
        {/* Page Title */}
        <h1 class="text-3xl md:text-4xl font-bold text-theme-text-primary mb-6">
          {t('methodology.title')}
        </h1>

        {/* How MétéoScore Works */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mb-4">
            {t('methodology.howItWorks')}
          </h2>
          <p class="text-theme-text-secondary leading-relaxed mb-4">
            {t('methodology.howItWorksDesc')}
          </p>
        </section>

        {/* Metrics Explained */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mt-8 mb-4">
            {t('methodology.metricsExplained')}
          </h2>

          {/* MAE */}
          <h3 class="text-xl font-medium text-theme-text-secondary mt-6 mb-3">
            {t('methodology.mae')}
          </h3>
          <div class="bg-theme-bg-tertiary p-4 rounded-lg my-4 font-mono text-sm text-theme-text-primary">
            {t('methodology.maeFormula')}
          </div>
          <p class="text-theme-text-secondary leading-relaxed mb-4">
            {t('methodology.maeDesc')}
          </p>

          {/* Bias */}
          <h3 class="text-xl font-medium text-theme-text-secondary mt-6 mb-3">
            {t('methodology.biasTitle')}
          </h3>
          <div class="bg-theme-bg-tertiary p-4 rounded-lg my-4 font-mono text-sm text-theme-text-primary">
            {t('methodology.biasFormula')}
          </div>
          <ul class="list-disc list-outside text-theme-text-secondary space-y-2 mb-4 ml-6">
            <li>
              <strong>{t('methodology.positiveBias')}</strong>{' '}
              {t('methodology.positiveBiasDesc')}
            </li>
            <li>
              <strong>{t('methodology.negativeBias')}</strong>{' '}
              {t('methodology.negativeBiasDesc')}
            </li>
            <li>
              <strong>{t('methodology.zeroBias')}</strong>{' '}
              {t('methodology.zeroBiasDesc')}
            </li>
          </ul>
        </section>

        {/* Data Sources */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mt-8 mb-4">
            {t('methodology.dataSources')}
          </h2>

          <h3 class="text-xl font-medium text-theme-text-secondary mt-6 mb-3">
            {t('methodology.forecastModels')}
          </h3>
          <ul class="list-disc list-outside text-theme-text-secondary space-y-2 mb-4 ml-6">
            <li>
              <strong>AROME</strong> - {t('methodology.aromeDesc').replace('AROME - ', '')}
            </li>
            <li>
              <strong>Meteo-Parapente</strong> - {t('methodology.meteoParapenteDesc').replace('Meteo-Parapente - ', '')}
            </li>
          </ul>

          <h3 class="text-xl font-medium text-theme-text-secondary mt-6 mb-3">
            {t('methodology.observationNetworks')}
          </h3>
          <ul class="list-disc list-outside text-theme-text-secondary space-y-2 mb-4 ml-6">
            <li>
              <strong>ROMMA</strong> - {t('methodology.rommaDesc').replace('ROMMA - ', '')}
            </li>
            <li>
              <strong>FFVL</strong> - {t('methodology.ffvlDesc').replace('FFVL - ', '')}
            </li>
          </ul>
        </section>

        {/* Data Collection Process */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mt-8 mb-4">
            {t('methodology.dataCollection')}
          </h2>
          <ol class="list-decimal list-outside text-theme-text-secondary space-y-2 mb-4 ml-6">
            <li>{t('methodology.dataCollectionStep1')}</li>
            <li>{t('methodology.dataCollectionStep2')}</li>
            <li>{t('methodology.dataCollectionStep3')}</li>
            <li>{t('methodology.dataCollectionStep4')}</li>
            <li>{t('methodology.dataCollectionStep5')}</li>
          </ol>
        </section>

        {/* Confidence Levels */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mt-8 mb-4">
            {t('methodology.confidenceLevels')}
          </h2>
          <p class="text-theme-text-secondary leading-relaxed mb-4">
            {t('methodology.confidenceLevelsDesc')}
          </p>
          <div class="overflow-x-auto">
            <table class="min-w-full border border-theme-border-primary my-4">
              <thead>
                <tr class="bg-theme-bg-tertiary">
                  <th class="border border-theme-border-primary px-4 py-3 text-left font-semibold text-theme-text-secondary">
                    {t('methodology.levelColumn')}
                  </th>
                  <th class="border border-theme-border-primary px-4 py-3 text-left font-semibold text-theme-text-secondary">
                    {t('methodology.daysColumn')}
                  </th>
                  <th class="border border-theme-border-primary px-4 py-3 text-left font-semibold text-theme-text-secondary">
                    {t('methodology.interpretationColumn')}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">
                    <span class="inline-flex items-center">
                      <span class="mr-2">&#x2705;</span> {t('methodology.validated')}
                    </span>
                  </td>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">{t('methodology.validatedDays')}</td>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">
                    {t('methodology.validatedDesc')}
                  </td>
                </tr>
                <tr class="bg-theme-bg-tertiary">
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">
                    <span class="inline-flex items-center">
                      <span class="mr-2">&#x1F536;</span> {t('methodology.preliminary')}
                    </span>
                  </td>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">{t('methodology.preliminaryDays')}</td>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">
                    {t('methodology.preliminaryDesc')}
                  </td>
                </tr>
                <tr>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">
                    <span class="inline-flex items-center">
                      <span class="mr-2">&#x26A0;&#xFE0F;</span> {t('methodology.insufficient')}
                    </span>
                  </td>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">{t('methodology.insufficientDays')}</td>
                  <td class="border border-theme-border-primary px-4 py-3 text-theme-text-secondary">
                    {t('methodology.insufficientDesc')}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Limitations */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mt-8 mb-4">
            {t('methodology.limitations')}
          </h2>
          <ul class="list-disc list-outside text-theme-text-secondary space-y-2 mb-4 ml-6">
            <li>
              <strong>{t('methodology.limitationPastPerf')}</strong>{' '}
              {t('methodology.limitationPastPerfDesc')}
            </li>
            <li>
              <strong>{t('methodology.limitationSiteSpecific')}</strong>{' '}
              {t('methodology.limitationSiteSpecificDesc')}
            </li>
            <li>
              <strong>{t('methodology.limitationExtremeEvents')}</strong>{' '}
              {t('methodology.limitationExtremeEventsDesc')}
            </li>
            <li>
              <strong>{t('methodology.limitationMeasurement')}</strong>{' '}
              {t('methodology.limitationMeasurementDesc')}
            </li>
          </ul>
        </section>

        {/* Transparency & Open Source */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mt-8 mb-4">
            {t('methodology.transparency')}
          </h2>
          <p class="text-theme-text-secondary leading-relaxed mb-4">
            {t('methodology.transparencyDesc')}
          </p>
          <ul class="list-disc list-outside text-theme-text-secondary space-y-2 mb-4 ml-6">
            <li>
              <a
                href="https://github.com/AurelienS/meteo-score"
                class="text-primary-500 hover:text-primary-600 hover:underline focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded inline-flex items-center gap-1"
                target="_blank"
                rel="noopener noreferrer"
              >
                {t('methodology.githubRepo')}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
              {' '}- {t('methodology.sourceCodeDesc')}
            </li>
            <li>
              <a
                href="https://github.com/AurelienS/meteo-score/blob/main/docs/METHODOLOGY.md"
                class="text-primary-500 hover:text-primary-600 hover:underline focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded inline-flex items-center gap-1"
                target="_blank"
                rel="noopener noreferrer"
              >
                {t('methodology.technicalDocs')}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
              {' '}- {t('methodology.detailedMethodology')}
            </li>
          </ul>
        </section>

        {/* Questions or Feedback */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-theme-text-primary mt-8 mb-4">
            {t('methodology.questions')}
          </h2>
          <p class="text-theme-text-secondary leading-relaxed mb-4">
            {t('methodology.questionsDesc')}{' '}
            <a
              href="https://github.com/AurelienS/meteo-score/issues"
              class="text-primary-500 hover:text-primary-600 hover:underline focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded inline-flex items-center gap-1"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
            {' '}{t('methodology.orContactMaintainers')}
          </p>
        </section>
      </div>
    </div>
  );
};

export default About;
