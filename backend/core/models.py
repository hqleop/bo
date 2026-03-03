from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models, transaction
from django.db.models import Max


class UserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Email-as-username user.
    """

    username = None  # remove username field
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True, default="")
    middle_name = models.CharField(max_length=150, blank=True, default="")
    avatar = models.FileField(upload_to="avatars/%Y/%m/", blank=True, null=True)
    registration_step = models.PositiveSmallIntegerField(default=4, db_index=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:  # pragma: no cover
        return self.email


class Company(models.Model):
    class SubjectType(models.TextChoices):
        FOP_RESIDENT = "fop_resident", "ФОП (Резидент)"
        LEGAL_RESIDENT = "legal_resident", "Юридична особа (Резидент)"
        NON_RESIDENT = "non_resident", "Не резидент"
        INDIVIDUAL = "individual", "Фізична особа"

    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        INACTIVE = "inactive", "Неактивна"

    edrpou = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    goal_tenders = models.BooleanField(default=False)
    goal_participation = models.BooleanField(default=False)
    subject_type = models.CharField(
        max_length=32,
        choices=SubjectType.choices,
        default=SubjectType.LEGAL_RESIDENT,
    )
    registration_country = models.CharField(max_length=50, blank=True, default="")
    company_address = models.CharField(max_length=500, blank=True, default="")
    identity_document = models.FileField(
        upload_to="company_registration_docs/%Y/%m/",
        blank=True,
        null=True,
    )
    agree_trade_rules = models.BooleanField(default=False)
    agree_privacy_policy = models.BooleanField(default=False)
    agree_participation_visibility = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    # CPV-категорії, закріплені за компанією
    cpv_categories = models.ManyToManyField(
        "CpvDictionary",
        related_name="companies_by_cpvs",
        blank=True,
        help_text="CPV-категорії, закріплені за компанією",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.edrpou})"


class CompanySupplier(models.Model):
    """
    Зв'язок «наша компанія — контрагент».
    Контрагент: створений вручну або підтвердив участь у тендері (закупівля/продаж).
    """

    class Source(models.TextChoices):
        MANUAL = "manual", "Додано вручну"
        PARTICIPATION = "participation", "Участь у тендері"

    owner_company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="supplier_relations",
        help_text="Компанія, для якої ведеться список контрагентів",
    )
    supplier_company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="as_supplier_for",
        help_text="Компанія-контрагент",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Контрагент компанії"
        verbose_name_plural = "Контрагенти компанії"
        unique_together = (("owner_company", "supplier_company"),)
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.owner_company_id} → {self.supplier_company.name}"


class Permission(models.Model):
    """
    Global permission catalog for menu/modules (MVP).
    """

    code = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)

    def __str__(self) -> str:  # pragma: no cover
        return self.code


class Role(models.Model):
    """
    Company-scoped role.
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=100)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        unique_together = (("company", "name"),)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.company_id}:{self.name}"


class CompanyUser(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Очікує"
        APPROVED = "approved", "Підтверджено"
        REJECTED = "rejected", "Відхилено"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="members")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invited_memberships"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "company"),)


class Notification(models.Model):
    """
    In-app notifications (MVP).
    """

    class Type(models.TextChoices):
        MEMBERSHIP_REQUEST = "membership_request", "Запит на приєднання"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=64, choices=Type.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    is_read = models.BooleanField(default=False)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Branch(models.Model):
    """
    Філіал компанії (дерево).
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Філіал"
        verbose_name_plural = "Філіали"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    """
    Підрозділ (дерево, належить філіалу).
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="departments")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Підрозділ"
        verbose_name_plural = "Підрозділи"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class BranchUser(models.Model):
    """
    Зв'язок користувача з філіалом.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="branches")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("branch", "user"),)
        verbose_name = "Користувач філіалу"
        verbose_name_plural = "Користувачі філіалів"

    def __str__(self) -> str:
        return f"{self.user.email} - {self.branch.name}"


class DepartmentUser(models.Model):
    """
    Зв'язок користувача з підрозділом.
    """

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="departments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("department", "user"),)
        verbose_name = "Користувач підрозділу"
        verbose_name_plural = "Користувачі підрозділів"

    def __str__(self) -> str:
        return f"{self.user.email} - {self.department.name}"


class CpvDictionary(models.Model):
    """
    Довідник CPV-кодів (імпортований у таблицю cpv_dictionary).
    """

    cpv_parent_code = models.CharField(max_length=50)
    cpv_level_code = models.CharField(max_length=50)
    cpv_code = models.CharField(max_length=50)
    name_ua = models.TextField(blank=True, default="")
    name_en = models.TextField(blank=True, default="")

    class Meta:
        db_table = "cpv_dictionary"
        managed = False  # таблиця створюється скриптом імпорту, Django її не змінює
        ordering = ["cpv_code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.cpv_code} - {self.name_ua}"


class CountryBusinessNumber(models.Model):
    country_code = models.CharField(max_length=20, blank=True, default="")
    number_code = models.CharField(max_length=50, primary_key=True)
    number_name = models.CharField(max_length=255)

    class Meta:
        db_table = "countrybusinessnumber"
        managed = False
        ordering = ["number_name", "number_code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.number_name} ({self.number_code})"


class Category(models.Model):
    """
    Категорія компанії (дерево).
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="categories")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    cpvs = models.ManyToManyField(
        CpvDictionary,
        related_name="categories",
        blank=True,
        help_text="CPV-коди, прив'язані до категорії",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"
        ordering = ["name"]
        unique_together = (("company", "name"),)

    def __str__(self) -> str:
        return self.name


class CategoryUser(models.Model):
    """
    Зв'язок користувача з категорією.
    """

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("category", "user"),)
        verbose_name = "Користувач категорії"
        verbose_name_plural = "Користувачі категорій"

    def __str__(self) -> str:
        return f"{self.user.email} - {self.category.name}"


class ExpenseArticle(models.Model):
    """
    Стаття витрат (дерево всередині компанії).
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="expense_articles")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, default="")
    year_start = models.PositiveIntegerField()
    year_end = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Стаття витрат"
        verbose_name_plural = "Статті витрат"
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class ExpenseArticleUser(models.Model):
    """
    Прив'язка користувачів до статті витрат.
    """

    expense = models.ForeignKey(ExpenseArticle, on_delete=models.CASCADE, related_name="users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expense_articles")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("expense", "user"),)
        verbose_name = "Користувач статті витрат"
        verbose_name_plural = "Користувачі статей витрат"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user.email} - {self.expense.name}"


class UnitOfMeasure(models.Model):
    """
    Довідник одиниць виміру. Спільний для всіх компаній (company=null);
    наповнюється через БД. Історично можуть бути одиниці з прив'язкою до компанії.
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="units_of_measure", null=True, blank=True
    )
    name_ua = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True, default="")
    short_name_ua = models.CharField(max_length=50, blank=True, default="")
    short_name_en = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Одиниця виміру"
        verbose_name_plural = "Одиниці виміру"
        ordering = ["name_ua"]
        constraints = [
            models.UniqueConstraint(
                fields=["name_ua"],
                condition=models.Q(company__isnull=True),
                name="core_unitofmeasure_shared_name_unique",
            ),
            models.UniqueConstraint(
                fields=["company", "name_ua"],
                condition=models.Q(company__isnull=False),
                name="core_unitofmeasure_company_name_unique",
            ),
        ]

    @property
    def display_short_ua(self) -> str:
        """Коротка назва для відображення в номенклатурах (short_name_ua або name_ua)."""
        return (self.short_name_ua or self.name_ua or "").strip()

    def __str__(self) -> str:  # pragma: no cover
        return self.name_ua


class Nomenclature(models.Model):
    """
    Номенклатура товарів/послуг компанії.
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="nomenclatures")
    name = models.CharField(max_length=255)
    unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name="nomenclatures",
        help_text="Одиниця виміру",
    )
    code = models.CharField(max_length=100, blank=True, default="", help_text="Код / артикул")
    external_number = models.CharField(max_length=100, blank=True, default="", help_text="Зовнішній номер")
    description = models.TextField(blank=True, default="")
    specification_file = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Шлях або ідентифікатор файлу специфікації (MVP: як текстове поле)",
    )
    image_file = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Шлях або ідентифікатор зображення (MVP: як текстове поле)",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nomenclatures",
        help_text="Звичайна категорія довідника",
    )
    cpv_category = models.ForeignKey(
        CpvDictionary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nomenclatures",
        help_text="CPV-категорія (зберігається для сумісності, використовуйте cpv_categories)",
    )
    cpv_categories = models.ManyToManyField(
        CpvDictionary,
        related_name="nomenclatures_by_cpvs",
        blank=True,
        help_text="CPV-категорії для прив'язки номенклатури",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Номенклатура"
        verbose_name_plural = "Номенклатура"
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Currency(models.Model):
    """
    Довідник валют (системний, спільний для всіх компаній).
    """

    code = models.CharField(max_length=10, unique=True)
    code_iso = models.CharField(max_length=3, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Валюта"
        verbose_name_plural = "Валюти"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class TenderCriterion(models.Model):
    """
    Критерій тендеру — елемент, на який відповідає учасник під час проведення.
    Типи: числовий, текстовий, файловий, булевий.
    Застосування: загальний (одне значення на весь тендер) чи індивідуальний (по кожній позиції).
    """

    class Type(models.TextChoices):
        NUMERIC = "numeric", "Числовий"
        TEXT = "text", "Текстовий"
        DATE = "date", "Дата"
        FILE = "file", "Файловий"
        BOOLEAN = "boolean", "Булевий (Так/Ні)"

    class Application(models.TextChoices):
        GENERAL = "general", "Загальний"
        INDIVIDUAL = "individual", "Індивідуальний"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="tender_criteria"
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)
    tender_type = models.CharField(
        max_length=20,
        choices=(
            ("procurement", "Procurement"),
            ("sales", "Sales"),
        ),
        default="procurement",
        help_text="Tender type for criterion dictionary: procurement or sales.",
    )
    application = models.CharField(
        max_length=20,
        choices=Application.choices,
        default=Application.INDIVIDUAL,
        help_text="Загальний — одне значення на тендер; індивідуальний — по кожній позиції.",
    )
    # Додаткові параметри за типом: range_min/range_max, numeric_choices, text_choices
    is_required = models.BooleanField(
        default=False,
        help_text="Ознака обов'язковості заповнення критерію при подачі пропозиції.",
    )
    options = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Критерій тендеру"
        verbose_name_plural = "Критерії тендерів"
        ordering = ["name"]
        unique_together = (("company", "name", "type", "tender_type"),)

    def __str__(self) -> str:
        return self.name


class TenderAttribute(models.Model):
    """
    Атрибут тендера — додаткове поле для позицій (заповнює організатор).
    Підтримує текст, число або дату.
    """

    class Type(models.TextChoices):
        NUMERIC = "numeric", "Числовий"
        TEXT = "text", "Текстовий"
        DATE = "date", "Дата"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="tender_attributes"
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)
    tender_type = models.CharField(
        max_length=20,
        choices=(
            ("procurement", "Procurement"),
            ("sales", "Sales"),
        ),
        default="procurement",
        help_text="Tender type for attribute dictionary: procurement or sales.",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tender_attributes",
    )
    is_required = models.BooleanField(
        default=False,
        help_text="Ознака обов'язковості заповнення атрибута в позиції.",
    )
    options = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Атрибут тендеру"
        verbose_name_plural = "Атрибути тендерів"
        ordering = ["name"]
        unique_together = (("company", "name", "type", "tender_type"),)

    def __str__(self) -> str:
        return self.name


class ApprovalModelRole(models.Model):
    """Company-scoped role used in approval models."""

    class Application(models.TextChoices):
        PROCUREMENT = "procurement", "Тендер-Закупівля"
        SALES = "sales", "Тендер-Продаж"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="approval_model_roles"
    )
    name = models.CharField(max_length=255)
    application = models.CharField(
        max_length=20, choices=Application.choices, default=Application.PROCUREMENT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Роль моделі погодження"
        verbose_name_plural = "Ролі моделей погодження"
        ordering = ["name"]
        unique_together = (("company", "name", "application"),)

    def __str__(self) -> str:
        return self.name


class ApprovalModelRoleUser(models.Model):
    """Users assigned to model role."""

    role = models.ForeignKey(
        ApprovalModelRole, on_delete=models.CASCADE, related_name="role_users"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="approval_model_role_memberships"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Користувач ролі моделі погодження"
        verbose_name_plural = "Користувачі ролей моделей погодження"
        unique_together = (("role", "user"),)
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.role} — {self.user}"


class ApprovalRangeMatrix(models.Model):
    """Budget range matrix item used by approval models."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="approval_range_matrix_items"
    )
    budget_from = models.DecimalField(max_digits=18, decimal_places=2)
    budget_to = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="approval_range_matrix_items"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Діапазон матриці погодження"
        verbose_name_plural = "Діапазони матриці погодження"
        ordering = ["budget_from", "budget_to", "id"]

    def __str__(self) -> str:
        return f"{self.budget_from} - {self.budget_to} {self.currency.code}"


class ApprovalModel(models.Model):
    """Approval model for tenders."""

    class Application(models.TextChoices):
        PROCUREMENT = "procurement", "Тендер-Закупівля"
        SALES = "sales", "Тендер-Продаж"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="approval_models"
    )
    name = models.CharField(max_length=255)
    application = models.CharField(
        max_length=20, choices=Application.choices, default=Application.PROCUREMENT
    )
    categories = models.ManyToManyField(
        Category, related_name="approval_models", blank=True
    )
    ranges = models.ManyToManyField(
        ApprovalRangeMatrix, related_name="approval_models", blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Модель погодження"
        verbose_name_plural = "Моделі погодження"
        ordering = ["name"]
        unique_together = (("company", "name", "application"),)

    def __str__(self) -> str:
        return self.name


class ApprovalModelStep(models.Model):
    """Ordered role rows in approval model table."""

    class DecisionRule(models.TextChoices):
        ONE_OF = "one_of", "Один зі"
        ALL = "all", "Усі"

    model = models.ForeignKey(
        ApprovalModel, on_delete=models.CASCADE, related_name="steps"
    )
    role = models.ForeignKey(
        ApprovalModelRole, on_delete=models.PROTECT, related_name="model_steps"
    )
    order = models.PositiveIntegerField(default=1)
    preparation_rule = models.CharField(
        max_length=20, choices=DecisionRule.choices, default=DecisionRule.ONE_OF
    )
    approval_rule = models.CharField(
        max_length=20, choices=DecisionRule.choices, default=DecisionRule.ONE_OF
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Крок моделі погодження"
        verbose_name_plural = "Кроки моделі погодження"
        ordering = ["order", "id"]
        unique_together = (("model", "role", "order"),)

    def __str__(self) -> str:
        return f"{self.model} [{self.order}] — {self.role}"


class ProcurementTender(models.Model):
    """
    Тендер на закупівлю. Етапи: паспорт → підготовка → прийом пропозицій → вибір рішення → затвердження → завершений.
    """

    class Stage(models.TextChoices):
        PASSPORT = "passport", "Паспорт тендера"
        PREPARATION = "preparation", "Підготовка процедури"
        ACCEPTANCE = "acceptance", "Прийом пропозицій"
        DECISION = "decision", "Вибір рішення"
        APPROVAL = "approval", "Затвердження"
        COMPLETED = "completed", "Завершений"

    class ConductType(models.TextChoices):
        REGISTRATION = "registration", "Реєстрація закупівлі"
        RFX = "rfx", "Збір пропозицій (RFx)"
        ONLINE_AUCTION = "online_auction", "Онлайн торги"

    class PublicationType(models.TextChoices):
        OPEN = "open", "Відкрита процедура"
        CLOSED = "closed", "Закрита процедура"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="procurement_tenders"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_tours",
        help_text="Попередній тур, якщо це наступний тур того ж тендера",
    )
    tour_number = models.PositiveIntegerField(default=1)
    number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Порядковий номер тендера в компанії (присвоюється при першому збереженні)",
    )
    name = models.CharField(max_length=500)
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.PASSPORT
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_tenders",
    )
    cpv_category = models.ForeignKey(
        CpvDictionary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_tenders",
        help_text="Зберігається для сумісності, використовуйте cpv_categories",
    )
    cpv_categories = models.ManyToManyField(
        CpvDictionary,
        related_name="procurement_tenders_by_cpvs",
        blank=True,
        help_text="CPV-категорії тендера",
    )
    expense_article = models.ForeignKey(
        ExpenseArticle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_tenders",
    )
    estimated_budget = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_tenders",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_tenders",
    )
    conduct_type = models.CharField(
        max_length=20,
        choices=ConductType.choices,
        default=ConductType.RFX,
    )
    publication_type = models.CharField(
        max_length=20,
        choices=PublicationType.choices,
        default=PublicationType.OPEN,
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="procurement_tenders",
    )
    general_terms = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_procurement_tenders",
    )
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approval_model = models.ForeignKey(
        ApprovalModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_tenders",
    )

    class Meta:
        verbose_name = "Тендер на закупівлю"
        verbose_name_plural = "Тендери на закупівлю"
        ordering = ["-created_at"]
        unique_together = (("company", "number", "tour_number"),)

    def save(self, *args, **kwargs):
        if not self.pk and self.company_id and self.number is None:
            with transaction.atomic():
                Company.objects.select_for_update().get(id=self.company_id)
                if self.parent_id:
                    self.number = self.parent.number
                else:
                    agg = ProcurementTender.objects.filter(
                        company_id=self.company_id
                    ).aggregate(Max("number"))
                    self.number = (agg["number__max"] or 0) + 1
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    # Параметри цінового критерія (для процедури реєстрації та інших)
    price_criterion_vat = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Наприклад: with_vat, without_vat",
    )
    price_criterion_delivery = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Наприклад: with_delivery, without_delivery",
    )
    tender_criteria = models.ManyToManyField(
        TenderCriterion,
        related_name="procurement_tenders",
        blank=True,
        help_text="Критерії тендера (крім ціни)",
    )
    tender_attributes = models.ManyToManyField(
        TenderAttribute,
        related_name="procurement_tenders",
        blank=True,
        help_text="Атрибути тендера для позицій",
    )

    def __str__(self) -> str:
        return f"#{self.number or '?'} {self.name}"


class ProcurementTenderCriterion(models.Model):
    """Tender-scoped criterion snapshot for procurement tenders."""

    tender = models.ForeignKey(
        ProcurementTender,
        on_delete=models.CASCADE,
        related_name="criteria_items",
    )
    reference_criterion = models.ForeignKey(
        TenderCriterion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="procurement_tender_snapshots",
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TenderCriterion.Type.choices)
    application = models.CharField(
        max_length=20,
        choices=TenderCriterion.Application.choices,
        default=TenderCriterion.Application.INDIVIDUAL,
    )
    is_required = models.BooleanField(default=False)
    options = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Критерій тендера на закупівлю (знімок)"
        verbose_name_plural = "Критерії тендера на закупівлю (знімки)"
        ordering = ["id"]
        unique_together = (("tender", "reference_criterion"),)

    def __str__(self) -> str:
        return f"{self.tender} — {self.name}"


class ProcurementTenderPosition(models.Model):
    """
    Позиція тендера на закупівлю.
    name та unit_name — знімок на момент додавання; зміни в довіднику номенклатури їх не змінюють.
    nomenclature_id — зв'язок з довідником (для історії/аналогій).
    """

    tender = models.ForeignKey(
        ProcurementTender,
        on_delete=models.CASCADE,
        related_name="positions",
    )
    nomenclature = models.ForeignKey(
        Nomenclature,
        on_delete=models.PROTECT,
        related_name="procurement_tender_positions",
        help_text="Зв'язок з довідником; відображення в тендері йде з name/unit_name",
    )
    name = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Назва позиції (знімок з номенклатури на момент додавання)",
    )
    unit_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Одиниця виміру (знімок)",
    )
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, default=1,
    )
    description = models.TextField(blank=True, default="")
    attribute_values = models.JSONField(default=dict, blank=True)
    start_price = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Стартова ціна для класичних торгів.",
    )
    min_bid_step = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Мінімальний крок ставки для класичних торгів.",
    )
    max_bid_step = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Максимальний крок ставки для класичних торгів.",
    )
    winner_proposal = models.ForeignKey(
        "TenderProposal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_positions",
        help_text="Переможець по цій позиції (після фіксації рішення)",
    )

    class Meta:
        verbose_name = "Позиція тендера на закупівлю"
        verbose_name_plural = "Позиції тендера на закупівлю"
        ordering = ["id"]
        unique_together = (("tender", "nomenclature"),)

    def __str__(self) -> str:
        return f"{self.tender} — {self.name or self.nomenclature.name}"


class TenderProposal(models.Model):
    """Пропозиція контрагента в тендері (реєстрація: організатор заповнює від імені контрагента)."""

    tender = models.ForeignKey(
        ProcurementTender,
        on_delete=models.CASCADE,
        related_name="proposals",
    )
    supplier_company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="tender_proposals_as_supplier",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Час подачі пропозиції; null — не подано або відкликано",
    )

    class Meta:
        verbose_name = "Пропозиція в тендері"
        verbose_name_plural = "Пропозиції в тендері"
        ordering = ["id"]
        unique_together = (("tender", "supplier_company"),)

    def __str__(self) -> str:
        return f"{self.tender} — {self.supplier_company.name}"


class TenderProposalPosition(models.Model):
    """Значення по одній позиції в пропозиції (ціна + інші критерії)."""

    proposal = models.ForeignKey(
        TenderProposal,
        on_delete=models.CASCADE,
        related_name="position_values",
    )
    tender_position = models.ForeignKey(
        ProcurementTenderPosition,
        on_delete=models.CASCADE,
        related_name="proposal_values",
    )
    price = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True,
    )
    # Значення інших критеріїв: { "criterion_id": value (str/number/bool) }
    criterion_values = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Позиція пропозиції"
        verbose_name_plural = "Позиції пропозицій"
        ordering = ["tender_position_id"]
        unique_together = (("proposal", "tender_position"),)

    def __str__(self) -> str:
        return f"{self.proposal} — pos {self.tender_position_id}"


class ProcurementTenderFile(models.Model):
    """Файл, прикріплений до тендера на закупівлю."""

    tender = models.ForeignKey(
        ProcurementTender,
        on_delete=models.CASCADE,
        related_name="attached_files",
    )
    file = models.FileField(upload_to="tender_files/%Y/%m/")
    name = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    visible_to_participants = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Файл тендера"
        verbose_name_plural = "Файли тендера"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.name or self.file.name


class SalesTender(models.Model):
    """
    Тендер на продаж. Та сама структура та етапи, що й закупівля.
    Відмінність: переможець рекомендується за найбільшою ціною за позицію.
    """

    class Stage(models.TextChoices):
        PASSPORT = "passport", "Паспорт тендера"
        PREPARATION = "preparation", "Підготовка процедури"
        ACCEPTANCE = "acceptance", "Прийом пропозицій"
        DECISION = "decision", "Вибір рішення"
        APPROVAL = "approval", "Затвердження"
        COMPLETED = "completed", "Завершений"

    class ConductType(models.TextChoices):
        REGISTRATION = "registration", "Реєстрація продажу"
        RFX = "rfx", "Збір пропозицій (RFx)"
        ONLINE_AUCTION = "online_auction", "Онлайн торги"

    class PublicationType(models.TextChoices):
        OPEN = "open", "Відкрита процедура"
        CLOSED = "closed", "Закрита процедура"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="sales_tenders"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_tours",
        help_text="Попередній тур, якщо це наступний тур того ж тендера",
    )
    tour_number = models.PositiveIntegerField(default=1)
    number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Порядковий номер тендера в компанії (присвоюється при першому збереженні)",
    )
    name = models.CharField(max_length=500)
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.PASSPORT
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_tenders",
    )
    cpv_category = models.ForeignKey(
        CpvDictionary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_tenders",
        help_text="Зберігається для сумісності, використовуйте cpv_categories",
    )
    cpv_categories = models.ManyToManyField(
        CpvDictionary,
        related_name="sales_tenders_by_cpvs",
        blank=True,
        help_text="CPV-категорії тендера",
    )
    expense_article = models.ForeignKey(
        ExpenseArticle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_tenders",
    )
    estimated_budget = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_tenders",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_tenders",
    )
    conduct_type = models.CharField(
        max_length=20,
        choices=ConductType.choices,
        default=ConductType.RFX,
    )
    publication_type = models.CharField(
        max_length=20,
        choices=PublicationType.choices,
        default=PublicationType.OPEN,
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="sales_tenders",
    )
    general_terms = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sales_tenders",
    )
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approval_model = models.ForeignKey(
        ApprovalModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_tenders",
    )

    price_criterion_vat = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Наприклад: with_vat, without_vat",
    )
    price_criterion_delivery = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Наприклад: with_delivery, without_delivery",
    )
    tender_criteria = models.ManyToManyField(
        TenderCriterion,
        related_name="sales_tenders",
        blank=True,
        help_text="Критерії тендера (крім ціни)",
    )
    tender_attributes = models.ManyToManyField(
        TenderAttribute,
        related_name="sales_tenders",
        blank=True,
        help_text="Атрибути тендера для позицій",
    )

    class Meta:
        verbose_name = "Тендер на продаж"
        verbose_name_plural = "Тендери на продаж"
        ordering = ["-created_at"]
        unique_together = (("company", "number", "tour_number"),)

    def save(self, *args, **kwargs):
        if not self.pk and self.company_id and self.number is None:
            with transaction.atomic():
                Company.objects.select_for_update().get(id=self.company_id)
                if self.parent_id:
                    self.number = self.parent.number
                else:
                    agg = SalesTender.objects.filter(
                        company_id=self.company_id
                    ).aggregate(Max("number"))
                    self.number = (agg["number__max"] or 0) + 1
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"#{self.number or '?'} {self.name}"


class SalesTenderCriterion(models.Model):
    """Tender-scoped criterion snapshot for sales tenders."""

    tender = models.ForeignKey(
        SalesTender,
        on_delete=models.CASCADE,
        related_name="criteria_items",
    )
    reference_criterion = models.ForeignKey(
        TenderCriterion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_tender_snapshots",
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TenderCriterion.Type.choices)
    application = models.CharField(
        max_length=20,
        choices=TenderCriterion.Application.choices,
        default=TenderCriterion.Application.INDIVIDUAL,
    )
    is_required = models.BooleanField(default=False)
    options = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Критерій тендера на продаж (знімок)"
        verbose_name_plural = "Критерії тендера на продаж (знімки)"
        ordering = ["id"]
        unique_together = (("tender", "reference_criterion"),)

    def __str__(self) -> str:
        return f"{self.tender} — {self.name}"


class SalesTenderPosition(models.Model):
    """
    Позиція тендера на продаж.
    name та unit_name — знімок на момент додавання; зміни в довіднику номенклатури їх не змінюють.
    """

    tender = models.ForeignKey(
        SalesTender,
        on_delete=models.CASCADE,
        related_name="positions",
    )
    nomenclature = models.ForeignKey(
        Nomenclature,
        on_delete=models.PROTECT,
        related_name="sales_tender_positions",
    )
    name = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Назва позиції (знімок з номенклатури на момент додавання)",
    )
    unit_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Одиниця виміру (знімок)",
    )
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, default=1,
    )
    description = models.TextField(blank=True, default="")
    attribute_values = models.JSONField(default=dict, blank=True)
    start_price = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Стартова ціна для класичних торгів.",
    )
    min_bid_step = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Мінімальний крок ставки для класичних торгів.",
    )
    max_bid_step = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Максимальний крок ставки для класичних торгів.",
    )
    winner_proposal = models.ForeignKey(
        "SalesTenderProposal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_positions",
        help_text="Переможець по цій позиції (після фіксації рішення)",
    )

    class Meta:
        verbose_name = "Позиція тендера на продаж"
        verbose_name_plural = "Позиції тендера на продаж"
        ordering = ["id"]
        unique_together = (("tender", "nomenclature"),)

    def __str__(self) -> str:
        return f"{self.tender} — {self.nomenclature.name}"


class SalesTenderProposal(models.Model):
    """Пропозиція контрагента в тендері на продаж."""

    tender = models.ForeignKey(
        SalesTender,
        on_delete=models.CASCADE,
        related_name="proposals",
    )
    supplier_company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="sales_tender_proposals_as_supplier",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Час подачі пропозиції; null — не подано або відкликано",
    )

    class Meta:
        verbose_name = "Пропозиція в тендері на продаж"
        verbose_name_plural = "Пропозиції в тендері на продаж"
        ordering = ["id"]
        unique_together = (("tender", "supplier_company"),)

    def __str__(self) -> str:
        return f"{self.tender} — {self.supplier_company.name}"


class SalesTenderProposalPosition(models.Model):
    """Значення по одній позиції в пропозиції тендера на продаж."""

    proposal = models.ForeignKey(
        SalesTenderProposal,
        on_delete=models.CASCADE,
        related_name="position_values",
    )
    tender_position = models.ForeignKey(
        SalesTenderPosition,
        on_delete=models.CASCADE,
        related_name="proposal_values",
    )
    price = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True,
    )
    criterion_values = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Позиція пропозиції (продаж)"
        verbose_name_plural = "Позиції пропозицій (продаж)"
        ordering = ["tender_position_id"]
        unique_together = (("proposal", "tender_position"),)

    def __str__(self) -> str:
        return f"{self.proposal} — pos {self.tender_position_id}"


class SalesTenderFile(models.Model):
    """Файл, прикріплений до тендера на продаж."""

    tender = models.ForeignKey(
        SalesTender,
        on_delete=models.CASCADE,
        related_name="attached_files",
    )
    file = models.FileField(upload_to="sales_tender_files/%Y/%m/")
    name = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    visible_to_participants = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Файл тендера на продаж"
        verbose_name_plural = "Файли тендера на продаж"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.name or self.file.name


class TenderApprovalJournal(models.Model):
    """Approval journal entries for procurement and sales tenders."""

    class Action(models.TextChoices):
        SAVED = "saved", "Збережено"
        PUBLISHED = "published", "Опубліковано"
        APPROVED = "approved", "Погоджено"
        REJECTED = "rejected", "Скасовано"

    procurement_tender = models.ForeignKey(
        ProcurementTender,
        on_delete=models.CASCADE,
        related_name="approval_journal_entries",
        null=True,
        blank=True,
    )
    sales_tender = models.ForeignKey(
        SalesTender,
        on_delete=models.CASCADE,
        related_name="approval_journal_entries",
        null=True,
        blank=True,
    )
    stage = models.CharField(max_length=20, blank=True, default="")
    action = models.CharField(max_length=20, choices=Action.choices)
    comment = models.TextField(blank=True, default="")
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Запис журналу погодження"
        verbose_name_plural = "Журнал погодження"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        tender_ref = self.procurement_tender_id or self.sales_tender_id or "?"
        return f"Tender {tender_ref} {self.action} at {self.created_at}"
