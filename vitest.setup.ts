import '@testing-library/jest-dom/vitest';

// React 19 removed React.act from the production build.
// Set NODE_ENV=development before React loads so act is available.
// This must run before any test files import React/testing-library.
process.env.NODE_ENV = 'development';
