from django.apps import AppConfig


class StageAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stage_app"

    def ready(self):
        import stage_app.signals  # Import the signals module