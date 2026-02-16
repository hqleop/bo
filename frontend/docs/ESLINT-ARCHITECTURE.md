# ESLint: правила Clean Architecture + DDD

У проєкті увімкнені архітектурні правила, які допомагають дотримуватися потоку даних та заборон.

## Єдиний apiClient

Усі HTTP-запити йдуть через **одну** точку: `core/apiClient.ts`.

- Там використовується `$fetch` (ofetch): baseURL, заголовки, refresh при 401, обробка помилок.
- `useAuth` та `useApi` лише створюють клієнт через `createApiClient(...)` і передають baseURL та callbacks (getAuthHeaders, refreshAccessToken, logout).
- У компонентах і use-cases за архітектурою не викликають `useApi`/apiClient напряму — тільки через use-case.

## Що перевіряється

### 1. Заборона прямого HTTP у UI та use-cases
- **Файли:** `pages/**`, `components/**`, `**/domains/**/use-cases/**`
- **Заборонено:** `$fetch`, `fetch(…)`, `axios`
- **Повідомлення:** використовуйте тільки apiClient через доменний api layer (Component → UseCase → Store → API → apiClient).

### 2. Заборона apiClient/useApi поза api layer
- **Файли:** ті самі (pages, components, use-cases)
- **Заборонено:** імпорт `~/composables/useApi`, `@/composables/useApi`, імпорт з `core/apiClient*`, а також виклик глобального `useApi()`.
- **Дозволено:** у `core/` та у `domains/{domain}/api/**`.

### 3. Cross-domain імпорти
- **Файли:** `**/domains/**`
- **Заборонено:** імпорт з іншого домену (наприклад, у `domains/tender` не можна імпортувати з `domains/auth`).
- **Дозволено:** імпорт з `shared`, `core` та з того ж домену.

## Як запускати

```bash
npm run lint
npm run lint:fix   # автофікс де можливо
```

## Поточна кодова база

У поточному коді сторінки та компоненти викликають `useApi()` напряму — це **порушення** цієї архітектури. Під час міграції на use-cases та api layer ці виклики потрібно замінити на виклики use-case, а HTTP залишити лише в `core/` та `domains/*/api/`.

Правила можна тимчасово вимкнути для окремого рядка або файлу (наприклад, під час поетапного рефакторингу), але краще планувати міграцію під архітектуру.

## Додавання нового домену (cross-domain)

У `eslint.config.js` у блоці `import/no-restricted-paths` додайте зону:

```js
{ target: './domains/НазваДомену/**', from: './domains', except: ['./domains/НазваДомену/**'] }
```
