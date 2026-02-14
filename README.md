# Bid Open - Система для проведення тендерів (MVP)

Повна система для організаторів та учасників тендерів, виконана у функціональності одного кабінету.

## Технологічний стек

- **Backend**: Django 6.0 + Django REST Framework + SimpleJWT
- **Frontend**: Nuxt 4 + Nuxt UI
- **Database**: MySQL (з підтримкою SQLite для локальної розробки)
- **API Documentation**: Swagger/OpenAPI (drf-spectacular)

## Структура проекту

```
bo/
├── backend/          # Django REST API
│   ├── config/      # Django settings
│   ├── core/        # Основні моделі та API
│   └── manage.py
└── frontend/         # Nuxt 4 кабінет
    ├── layouts/     # Шаблони (site/cabinet)
    ├── pages/       # Сторінки
    └── composables/ # Логіка (auth, API)
```

## Швидкий старт

### Backend

```bash
cd backend

# Створити venv та встановити залежності
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Налаштувати .env (скопіювати з .env.example)
# Встановити параметри БД

# Міграції
python manage.py migrate

# Ініціалізація permissions
python manage.py init_permissions

# Створити superuser (опціонально)
python manage.py createsuperuser

# Запуск
python manage.py runserver
```

API: `http://localhost:8000/api/`
Swagger: `http://localhost:8000/api/docs/`

### Frontend

```bash
cd frontend

# Встановити залежності
npm install

# Запуск
npm run dev
```

Додаток: `http://localhost:3000`

## Основні функції MVP

### Реєстрація (2 кроки)

1. **Крок 1**: Створення користувача (ПІБ, телефон, email, пароль)
2. **Крок 2**: 
   - Нова компанія (ЄДРПОУ, назва, цілі) → користувач стає адміністратором
   - Існуюча компанія → запит на приєднання → адміністратор підтверджує

### Автентифікація

- JWT токени (access + refresh)
- Відновлення пароля (endpoints готові, email поки не відправляється)

### Кабінет

- **Адміністратор компанії**: повний доступ до всіх модулів
- **Користувач**: права визначаються адміністратором
- Меню формується на основі permissions користувача
- Сповіщення в кабінеті (in-app)

### Модулі (доступ керується permissions)

- Загальна аналітика
- Тендери / Створення тендерів / Журнал тендерів
- Участь в тендерах / Журнал участі
- Контрагенти
- Довідник (Номенклатури, Категорії, Статті витрат, Філіали)
- Шаблони
- Налаштування
- Користувачі / Ролі / Права доступу

## API Endpoints

Детальна документація доступна в Swagger UI: `http://localhost:8000/api/docs/`

### Основні групи endpoints:

- `/api/auth/` - Автентифікація (login, refresh, me, password reset)
- `/api/registration/` - Реєстрація (step1, step2/new, step2/existing)
- `/api/companies/` - Компанії
- `/api/memberships/` - Членства (approve/reject)
- `/api/roles/` - Ролі
- `/api/permissions/` - Права доступу
- `/api/notifications/` - Сповіщення

## Моделі даних

- **User** - Користувач (email як username)
- **Company** - Компанія (ЄДРПОУ, назва, статус активності)
- **CompanyUser** - Членство (роль, статус: pending/approved/rejected)
- **Role** - Роль в компанії (з правами доступу)
- **Permission** - Каталог прав доступу
- **Notification** - Сповіщення в кабінеті

## Примітки MVP

- Email-верифікація не реалізована
- Відновлення пароля через email поки не працює (тільки endpoints)
- Бізнес-логіка тендерів винесена за межі MVP
- Audit logs не реалізовані
- SSO/2FA не потрібні

## Розробка

### Backend

- Створення міграцій: `python manage.py makemigrations`
- Застосування міграцій: `python manage.py migrate`
- Django Admin: `http://localhost:8000/admin/`

### Frontend

- Додавання сторінок: створіть файл у `pages/cabinet/`
- Меню автоматично формується на основі permissions

## Ліцензія

MVP версія для внутрішнього використання.
