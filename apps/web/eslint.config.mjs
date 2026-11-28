import nextCoreWebVitals from 'eslint-config-next/core-web-vitals';
import nextTypescript from 'eslint-config-next/typescript';

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: ['next-env.d.ts', 'out/', '.next/', '.next-dev/', '.impeccable/'],
  },
  {
    rules: {
      // React Compiler readiness rule (eslint-config-next 16). Every screen loads data in an
      // effect and stores the result or the error in state; the app does not use the React
      // Compiler, so this stays a warning instead of failing the lint gate.
      'react-hooks/set-state-in-effect': 'warn',
      'no-restricted-properties': [
        'error',
        {
          object: 'window',
          property: 'confirm',
          message:
            'Use confirmAction() from lib/confirm: window.confirm does not block in the desktop app.',
        },
      ],
    },
  },
];

export default config;
