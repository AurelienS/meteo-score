import type { Component, JSX } from 'solid-js';
import { ErrorBoundary } from 'solid-js';
import { Route, Router, A } from '@solidjs/router';

import Navigation from './components/Navigation';
import Home from './pages/Home';
import SiteDetail from './pages/SiteDetail';
import About from './pages/About';

/**
 * Error fallback component for unhandled errors.
 */
function ErrorFallback(props: { error: Error; reset: () => void }): JSX.Element {
  return (
    <div class="min-h-screen flex items-center justify-center bg-red-50">
      <div class="bg-white p-8 rounded-lg shadow-lg max-w-md">
        <h1 class="text-2xl font-bold text-red-600 mb-4">Something went wrong</h1>
        <p class="text-gray-600 mb-4">{props.error.message}</p>
        <button
          onClick={() => props.reset()}
          class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

/**
 * Layout component wrapping all pages with navigation.
 */
function Layout(props: { children?: JSX.Element }): JSX.Element {
  return (
    <div class="min-h-screen bg-gray-50">
      <Navigation />
      <main>{props.children}</main>
    </div>
  );
}

/**
 * 404 Not Found page component.
 */
function NotFound(): JSX.Element {
  return (
    <div class="container mx-auto px-4 py-16 text-center">
      <h1 class="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <h2 class="text-2xl font-semibold text-gray-700 mb-4">Page Not Found</h2>
      <p class="text-gray-600 mb-8">The page you're looking for doesn't exist.</p>
      <A
        href="/"
        class="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
      >
        Go Home
      </A>
    </div>
  );
}

/**
 * Root application component with routing configuration.
 */
const App: Component = () => {
  return (
    <ErrorBoundary fallback={(err, reset) => <ErrorFallback error={err} reset={reset} />}>
      <Router root={Layout}>
        <Route path="/" component={Home} />
        <Route path="/sites/:id" component={SiteDetail} />
        <Route path="/about" component={About} />
        <Route path="*" component={NotFound} />
      </Router>
    </ErrorBoundary>
  );
};

export default App;
