# Bid Open - Backend (MVP)

Django REST API для системи проведення тендерів.

## Технології

- Django 6.0
- Django REST Framework
- SimpleJWT (JWT автентифікація)
- drf-spectacular (Swagger/OpenAPI документація)
- MySQL (через PyMySQL) або SQLite для локальної розробки

## Швидкий старт

### 1. Встановлення залежностей

```bash
# Створити venv (якщо ще не створено)
python -m venv .venv

# Активувати venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Встановити залежності
pip install -r requirements.txt
```

### 2. Налаштування бази даних

Скопіюйте `.env.example` в `.env` та налаштуйте параметри:

```bash
cp .env.example .env
```

Відредагуйте `.env`:
- `DB_ENGINE=mysql` для MySQL або залиште порожнім для SQLite (dev)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` для MySQL

### 3. Міграції

```bash
python manage.py migrate
```

### 4. Ініціалізація permissions

```bash
python manage.py init_permissions
```

### 5. Створення суперкористувача (опціонально)

```bash
python manage.py createsuperuser
```

### 6. Запуск сервера

```bash
python manage.py runserver
```

API буде доступне на `http://localhost:8000/api/`
Swagger документація: `http://localhost:8000/api/docs/`

## API Endpoints

### Автентифікація
- `POST /api/auth/login/` - Вхід (отримати JWT токени)
- `POST /api/auth/refresh/` - Оновити access token
- `GET /api/auth/me/` - Поточний користувач (з правами та членствами)
- `POST /api/auth/password-reset/` - Запит на відновлення пароля
- `POST /api/auth/password-reset/confirm/` - Підтвердження відновлення
- `POST /api/auth/password-change/` - Зміна пароля (автентифікований)

### Реєстрація
- `POST /api/registration/step1/` - Крок 1: Створення користувача
- `POST /api/registration/step2/new/` - Крок 2: Створення нової компанії
- `POST /api/registration/step2/existing/` - Крок 2: Приєднання до існуючої компанії

### Компанії
- `GET /api/companies/` - Список активних компаній
- `GET /api/companies/{id}/` - Деталі компанії

### Членства (CompanyUser)
- `GET /api/memberships/` - Список членств (для адміністраторів)
- `POST /api/memberships/` - Додати користувача до компанії
- `POST /api/memberships/{id}/approve/` - Підтвердити запит
- `POST /api/memberships/{id}/reject/` - Відхилити запит

### Ролі
- `GET /api/roles/` - Список ролей компанії
- `POST /api/roles/` - Створити роль
- `PUT/PATCH /api/roles/{id}/` - Оновити роль
- `DELETE /api/roles/{id}/` - Видалити роль

### Права доступу
- `GET /api/permissions/` - Каталог прав доступу

### Сповіщення
- `GET /api/notifications/` - Список сповіщень користувача
- `POST /api/notifications/{id}/mark_read/` - Позначити як прочитане
- `POST /api/notifications/mark_all_read/` - Позначити всі як прочитані

## Структура проекту

```
backend/
├── config/          # Django settings
├── core/            # Основні моделі та API
│   ├── models.py    # User, Company, CompanyUser, Role, Permission, Notification
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── management/commands/
│       └── init_permissions.py
├── manage.py
└── requirements.txt
```

## Моделі

- **User** - Користувач (email як username)
- **Company** - Компанія (ЄДРПОУ, назва, статус активності, цілі)
- **CompanyUser** - Членство користувача в компанії (роль, статус: pending/approved/rejected)
- **Role** - Роль в компанії (з правами доступу)
- **Permission** - Каталог прав доступу (для меню/модулів)
- **Notification** - Сповіщення в кабінеті

## Розробка

### Створення міграцій

```bash
python manage.py makemigrations
python manage.py migrate
```

### Django Admin

Адмінка доступна на `http://localhost:8000/admin/` (після створення superuser)

### Тестування API

Використовуйте Swagger UI (`/api/docs/`) або будь-який REST клієнт (Postman, Insomnia).

## Примітки MVP

- Email-верифікація не реалізована
- Відновлення пароля через email поки не працює (тільки endpoints)
- Бізнес-логіка тендерів винесена за межі MVP
- Audit logs не реалізовані
