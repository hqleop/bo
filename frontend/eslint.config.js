import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'
import importPlugin from 'eslint-plugin-import'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * Clean Architecture + DDD — ESLint rules
 *
 * 1. Заборона прямого fetch/$fetch/axios у компонентах та use-cases (тільки api layer).
 * 2. Заборона імпорту apiClient/useApi за межами api layer та core.
 * 3. Заборона cross-domain імпортів (domains/X не імпортує з domains/Y).
 */

const restrictedFetchMessage =
  'Використовуйте тільки apiClient через доменний api layer. Component → UseCase → Store → API → apiClient. Заборонено $fetch/fetch/axios у компонентах та use-cases.'

const restrictedApiClientMessage =
  'apiClient та useApi дозволені тільки в core/ та в domains/{domain}/api/. У компонентах та use-cases викликайте use-case, не API напряму.'

// Nuxt auto-imports (globals) — щоб не лагав no-undef
const nuxtGlobals = {
  useApi: 'readonly',
  useAuth: 'readonly',
  useRuntimeConfig: 'readonly',
  useRoute: 'readonly',
  useRouter: 'readonly',
  useFetch: 'readonly',
  useAsyncData: 'readonly',
  navigateTo: 'readonly',
  definePageMeta: 'readonly',
  ref: 'readonly',
  computed: 'readonly',
  reactive: 'readonly',
  onMounted: 'readonly',
  watch: 'readonly',
  nextTick: 'readonly'
}

export default tseslint.config(
  { ignores: ['**/node_modules/**', '**/.nuxt/**', '**/.output/**', '**/dist/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  { languageOptions: { globals: { ...nuxtGlobals } } },
  // Vue SFC: TypeScript у <script setup>
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: ['.vue']
      }
    }
  },
  // ——— Заборона fetch/$fetch/axios у pages, components, use-cases ———
  {
    files: ['pages/**/*.{ts,vue}', 'components/**/*.{ts,vue}', '**/domains/**/use-cases/**/*.ts'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: 'CallExpression[callee.name="$fetch"]',
          message: restrictedFetchMessage
        },
        {
          selector: 'CallExpression[callee.name="fetch"]',
          message: restrictedFetchMessage
        },
        {
          selector: 'CallExpression[callee.object.name="axios"]',
          message: restrictedFetchMessage
        },
        {
          selector: 'CallExpression[callee.property.name="get"][callee.object.name="axios"]',
          message: restrictedFetchMessage
        },
        {
          selector: 'CallExpression[callee.property.name="post"][callee.object.name="axios"]',
          message: restrictedFetchMessage
        },
        {
          selector: 'CallExpression[callee.property.name="put"][callee.object.name="axios"]',
          message: restrictedFetchMessage
        },
        {
          selector: 'CallExpression[callee.property.name="patch"][callee.object.name="axios"]',
          message: restrictedFetchMessage
        },
        {
          selector: 'CallExpression[callee.property.name="delete"][callee.object.name="axios"]',
          message: restrictedFetchMessage
        }
      ],
      'no-restricted-imports': [
        'error',
        {
          paths: [
            { name: '~/composables/useApi', message: restrictedApiClientMessage },
            { name: '@/composables/useApi', message: restrictedApiClientMessage },
            { name: '#imports', importNames: ['$fetch'], message: restrictedFetchMessage }
          ],
          patterns: [
            {
              group: ['**/core/apiClient*', '**/core/**/apiClient*'],
              message: restrictedApiClientMessage
            }
          ]
        }
      ],
      // Заборона виклику useApi() у компонентах (навіть як auto-import)
      'no-restricted-globals': [
        'error',
        { name: 'useApi', message: restrictedApiClientMessage }
      ]
    }
  },
  // ——— Cross-domain: у domains/* заборонено імпорт з інших доменів ———
  {
    files: ['**/domains/**/*.{ts,vue}'],
    plugins: { import: importPlugin },
    rules: {
      'import/no-restricted-paths': [
        'error',
        {
          zones: [
            // Кожен домен може імпортувати тільки shared, core та себе. Додайте зону для кожного домену.
            { target: './domains/auth/**', from: './domains', except: ['./domains/auth/**'] },
            { target: './domains/tender/**', from: './domains', except: ['./domains/tender/**'] },
            { target: './domains/nomenclature/**', from: './domains', except: ['./domains/nomenclature/**'] },
            { target: './domains/budget/**', from: './domains', except: ['./domains/budget/**'] }
          ],
          basePath: __dirname
        }
      ]
    }
  }
)
