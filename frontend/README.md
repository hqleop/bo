# Bid Open - Frontend (MVP)

Nuxt 4 кабінет для системи проведення тендерів.

## Технології

- Nuxt 4
- Nuxt UI (Tailwind CSS + Headless UI)
- Vue 3 Composition API
- TypeScript

## Швидкий старт

### 1. Встановлення залежностей

```bash
npm install
```

### 2. Налаштування

Створіть `.env` файл (опціонально):

```env
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
```

### 3. Запуск

```bash
# Development
npm run dev

# Build
npm run build

# Preview production build
npm run preview
```

Додаток буде доступний на `http://localhost:3000`

## Структура проекту

```
frontend/
├── layouts/
│   ├── default.vue    # Router для site/cabinet
│   ├── site.vue       # Публічний сайт (header + footer)
│   └── cabinet.vue    # Кабінет (sidebar + main)
├── pages/
│   ├── index.vue      # Головна сторінка
│   ├── login.vue      # Вхід
│   ├── register.vue   # Реєстрація (2 кроки)
│   └── cabinet/       # Сторінки кабінету
│       ├── dashboard.vue
│       ├── users.vue
│       └── roles.vue
├── composables/
│   ├── useAuth.ts     # Автентифікація
│   └── useApi.ts      # API клієнт
├── middleware/
│   └── auth.ts        # Middleware для захисту кабінету
└── nuxt.config.ts
```

## Особливості MVP

- Два шаблони: публічний сайт та кабінет
- Реєстрація в 2 кроки (користувач → компанія)
- Меню кабінету формується на основі permissions користувача
- Сповіщення в кабінеті (in-app)
- JWT автентифікація

## Розробка

### Додавання нових сторінок кабінету

1. Створіть файл у `pages/cabinet/`
2. Додайте `definePageMeta` з `layout: 'cabinet'` та `middleware: 'auth'`
3. Меню автоматично оновиться на основі permissions

### Використання API

```typescript
const { fetch } = useApi()
const { data, error } = await fetch('/endpoint/', {
  method: 'POST',
  body: { ... }
})
```

### Автентифікація

```typescript
const { login, logout, isAuthenticated } = useAuth()
```
