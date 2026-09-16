from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    label = "authentication"
    verbose_name = "Authentication & Identity"

    def ready(self):
        # Register OpenAPI auth extension for ReDoc/Swagger
        from apps.authentication import schema  # noqa: F401
