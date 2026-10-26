import React from 'react';
import { AppProviders } from './providers';
import { AppRouter } from './router';
import '../styles/globals.css';

/**
 * Root Application Component
 */
const App = () => {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
};

export default App;
