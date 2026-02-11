from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


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

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:  # pragma: no cover
        return self.email


class Company(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        INACTIVE = "inactive", "Неактивна"

    edrpou = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    goal_tenders = models.BooleanField(default=False)
    goal_participation = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.edrpou})"


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
