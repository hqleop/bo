from django.core.management.base import BaseCommand
from core.models import Permission

# Permission codes matching menu items from ТЗ
PERMISSIONS = [
    ("dashboard.view", "Загальна аналітика"),
    ("tenders.view", "Тендери"),
    ("tenders.create", "Створення тендерів"),
    ("tenders.participate", "Участь в тендерах"),
    ("tenders.journal.view", "Журнал тендерів"),
    ("participation.view", "Участь в тендерах"),
    ("participation.journal.view", "Журнал участі"),
    ("suppliers.view", "Контрагенти"),
    ("reference.view", "Довідник"),
    ("nomenclature.view", "Номенклатури"),
    ("categories.view", "Категорії"),
    ("expenses.view", "Статті витрат"),
    ("branches.view", "Філіали підрозділи"),
    ("templates.view", "Шаблони"),
    ("settings.view", "Налаштування"),
    ("users.manage", "Користувачі"),
    ("permissions.manage", "Права доступу"),
    ("roles.manage", "Ролі"),
]


class Command(BaseCommand):
    help = "Initialize permission catalog"

    def handle(self, *args, **options):
        created_count = 0
        for code, label in PERMISSIONS:
            permission, created = Permission.objects.get_or_create(code=code, defaults={"label": label})
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created permission: {code}"))
            else:
                # Update label if changed
                if permission.label != label:
                    permission.label = label
                    permission.save()
                    self.stdout.write(self.style.WARNING(f"Updated permission: {code}"))

        self.stdout.write(self.style.SUCCESS(f"\nInitialized {created_count} new permissions. Total: {Permission.objects.count()}"))
