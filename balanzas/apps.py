from django.apps import AppConfig


class BalanzasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'balanzas'
    verbose_name = 'Balanzas'

    def ready(self):
        from . import signals  # noqa: F401  (registra las señales)
