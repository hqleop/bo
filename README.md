# Bid Open — Система проведення тендерів (MVP)

Веб-додаток для організаторів та учасників тендерів: закупівлі та продажі в одному кабінеті з реєстрацією, правами доступу та повним циклом процедур.

---

## Технологічний стек

| Частина   | Технології |
|----------|-------------|
| **Backend** | Django 6.0, Django REST Framework, SimpleJWT, drf-spectacular |
| **Frontend** | Nuxt 4, Vue 3, Nuxt UI, Tailwind CSS |
| **БД** | MySQL (production) / SQLite (локальна розробка) |
| **API docs** | Swagger/OpenAPI (drf-spectacular) |

---

## Структура проекту

```
bo/
|-- backend/                         # Django REST API
|   |-- config/                      # Django config (settings, urls, asgi/wsgi)
|   |-- core/                        # Domain models, API, admin, migrations
|   |   |-- management/commands/
|   |   |   `-- init_permissions.py
|   |   |-- migrations/
|   |   |-- admin.py
|   |   |-- models.py
|   |   |-- serializers.py
|   |   |-- tests.py
|   |   |-- urls.py
|   |   `-- views.py
|   |-- import/                      # Utility scripts/files for CPV import
|   |-- manage.py
|   |-- requirements.txt
|   `-- README.md
|-- frontend/                        # Nuxt 4 app
|   |-- assets/css/main.css
|   |-- components/                  # Reusable UI components
|   |-- composables/                 # useAuth/useApi/use*UseCases
|   |-- core/apiClient.ts
|   |-- docs/ESLINT-ARCHITECTURE.md
|   |-- domains/                     # Feature modules (tenders/users/suppliers)
|   |-- layouts/                     # default/cabinet/site layouts
|   |-- middleware/auth.ts
|   |-- pages/
|   |   |-- index.vue
|   |   |-- login.vue
|   |   |-- register.vue
|   |   `-- cabinet/
|   |       |-- dashboard.vue
|   |       |-- participation.vue
|   |       |-- permissions.vue
|   |       |-- profile.vue
|   |       |-- roles.vue
|   |       |-- settings.vue
|   |       |-- templates.vue
|   |       |-- users.vue
|   |       |-- reference/           # attributes/branches/categories/...
|   |       |-- suppliers/           # index + [id]
|   |       `-- tenders/             # index/[id]/create/sales/proposals
|   |-- plugins/
|   |-- shared/api/apiClient.ts
|   |-- app.vue
|   |-- nuxt.config.ts
|   |-- package.json
|   `-- README.md
`-- README.md
```

---

## Швидкий старт

### Backend

```bash
cd backend

# Середовище та залежності
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Налаштування: скопіювати .env.example → .env (БД тощо)

# Міграції та права
python manage.py migrate
python manage.py init_permissions

# Опційно: суперкористувач для адмінки
python manage.py createsuperuser

# Запуск
python manage.py runserver
```

- API: **http://localhost:8000/api/**  
- Swagger: **http://localhost:8000/api/docs/**  
- Django Admin: **http://localhost:8000/admin/**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- Додаток: **http://localhost:3000**  
- Змінна середовища для API: `NUXT_PUBLIC_API_BASE` (за замовчуванням `http://localhost:8000/api`)

---

## Основні функції

### Реєстрація та автентифікація

- **Реєстрація (2 кроки):** створення користувача (ПІБ, телефон, email, пароль) → нова компанія (ЄДРПОУ, назва, цілі) або приєднання до існуючої (запит на підтвердження адміністратором).
- **Вхід:** JWT (access + refresh).
- **Профіль:** редагування даних, аватар, зміна пароля.
- Відновлення пароля: endpoints є, відправка email не реалізована.

### Кабінет

- Меню формується згідно з модулями: Аналітика, Участь в тендерах, Продажі, Закупівлі, Контрагенти, Довідники, Моделі погодження, Налаштування.
- Доступ до розділів може керуватися правами (ролі та permissions).
- Сповіщення в шапці кабінету; профіль та вихід.

### Тендери

- **Закупівлі:** створення процедури (паспорт → підготовка → прийом пропозицій → рішення → затвердження), позиції номенклатури, критерії, цінові параметри (ПДВ, доставка), пропозиції контрагентів, файли.
- **Продажі:** аналогічна схема (тендери на продаж, переможець за найвищою ціною).
- Режими проведення: реєстраційна процедура та інші (RFQ тощо).
- Сторінки: журнал закупівель/продажів, створення, картка тендера `[id]`, подача пропозицій `[id]/proposals` (закупівлі та продажі).

### Довідники та налаштування

- **Довідники:** номенклатури, категорії (з CPV), статті витрат, філіали/підрозділи, критерії тендерів, атрибути.
- **Контрагенти:** список контрагентів компанії (додавання вручну або з участі в тендерах).
- **Налаштування:** користувачі, ролі, права доступу, системні налаштування.

---

## API (основні групи)

| Група | Endpoints |
|-------|-----------|
| **Автентифікація** | `POST /api/auth/login/`, `POST /api/auth/refresh/`, `GET /api/auth/me/`, `POST /api/auth/me/avatar/`, password-reset, password-change |
| **Реєстрація** | `POST /api/registration/step1/`, `step2/new/`, `step2/existing/` |
| **Компанії** | `GET /api/companies/`, `GET /api/companies/{id}/` |
| **Членства** | `GET|POST /api/memberships/`, `POST /api/memberships/{id}/approve|reject/` |
| **Ролі та права** | `GET|POST|PUT|DELETE /api/roles/`, `GET /api/permissions/` |
| **Сповіщення** | `GET /api/notifications/`, `POST .../mark_read/`, `mark_all_read/` |
| **Довідники** | `categories`, `expenses`, `branches`, `departments`, `nomenclatures`, `units`, `currencies`, `tender-criteria` |
| **CPV** | `GET /api/cpv/tree/`, `GET /api/cpv/children/` |
| **Тендери** | `GET|POST|PATCH|... /api/procurement-tenders/`, `.../sales-tenders/` (включно з вкладками proposals, positions, files) |

Повний перелік та схеми — у Swagger: **http://localhost:8000/api/docs/**.

---

## Основні моделі даних

- **User** — користувач (email як логін, ПІБ, телефон, аватар).
- **Company** — компанія (ЄДРПОУ, назва, цілі, статус).
- **CompanyUser** — членство (роль, статус: pending/approved/rejected).
- **CompanySupplier** — зв’язок компанія ↔ контрагент.
- **Role**, **Permission** — ролі та каталог прав.
- **Notification** — сповіщення в кабінеті.
- **Branch**, **Department**, **Category**, **ExpenseArticle**, **Nomenclature**, **UnitOfMeasure**, **Currency**, **TenderCriterion** — довідники.
- **ProcurementTender**, позиції, пропозиції, файли — закупівлі.
- **SalesTender**, позиції, пропозиції, файли — продажі.

---

## Примітки MVP

- Email-верифікація не реалізована.
- Відновлення пароля через email не відправляється (лише API).
- Audit logs та SSO/2FA не передбачені.
- Меню кабінету тимчасово без фільтрації по permissions (усі пункти видимі після входу).

---

## Розробка

- **Міграції (backend):** `python manage.py makemigrations` → `python manage.py migrate`
- **Нові сторінки (frontend):** додати `.vue` у `pages/cabinet/` або відповідну підтеку; маршрути генеруються автоматично.
- Кабінет зібрано з `routeRules: { '/cabinet/**': { ssr: false } }` (SPA без SSR для уникнення розбіжностей стану авторизації).

Ліцензія: MVP для внутрішнього використання.


---

## Рекомендації щодо кодування тексту

- Зберігати всі текстові файли у `UTF-8` (без `BOM`).
- Для `*.vue`, `*.ts`, `*.js`, `*.md` не використовувати масові автоконвертації кодування.
- Вносити кириличні правки лише точково (`apply_patch`/IDE), без глобальних replace.
- Перед commit перевіряти артефакти mojibake: `Р`, `С`, `вЂ`, `В«`, `В»`, `????`.
- Для Git рекомендовано `*.vue text eol=lf` та `*.md text eol=lf` у `.gitattributes`.
- Якщо з'явився зламаний текст, виправляти його ручно в конкретних рядках, а не перекодовувати файл цілком.
