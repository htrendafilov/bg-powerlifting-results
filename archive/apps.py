from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archive"
    verbose_name = "Архив"

    def ready(self):
        from archive.search import connect

        connect()
