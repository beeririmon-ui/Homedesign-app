// @ts-check
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import globals from 'globals';

export default tseslint.config(
  {
    ignores: [
      '**/node_modules/**',
      '**/.wrangler/**',
      '.lighthouse/**',
      '**/dist/**',
      'dist-artifact/**',
      'web/.ssr/**',
      '.generated/**',
      '.wrangler*/**',
      'prototype/**',
      'test-results/**',
      'playwright-report/**',
      'shared/src/schema/*.gen.ts',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: { globals: { ...globals.node } },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_', destructuredArrayIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': ['error', { fixStyle: 'inline-type-imports', disallowTypeAnnotations: false }],
      eqeqeq: ['error', 'smart'],
      'no-console': 'off',
    },
  },
  {
    files: ['web/src/**/*.{ts,tsx}'],
    ...jsxA11y.flatConfigs.strict,
    languageOptions: { ...jsxA11y.flatConfigs.strict.languageOptions, globals: { ...globals.browser } },
    settings: { 'jsx-a11y': { components: {} } },
    rules: {
      ...jsxA11y.flatConfigs.strict.rules,
      // Preact uses `class`, `for` and lowercase event props; the rules below assume React prop names.
      'jsx-a11y/label-has-associated-control': ['error', { assert: 'either', controlComponents: ['input'], depth: 4 }],
      'jsx-a11y/no-noninteractive-tabindex': ['error', { tags: ['h1', 'main', 'div'], roles: ['tabpanel'] }],
      // the stage pans with the pointer; every action there also has a keyboard path (buttons and the wheel)
      'jsx-a11y/no-static-element-interactions': 'off',
      'jsx-a11y/no-noninteractive-element-interactions': ['error', { handlers: ['onClick'] }],
    },
  },
  {
    files: ['api/src/**/*.ts'],
    languageOptions: { globals: { ...globals.serviceworker } },
  },
);
