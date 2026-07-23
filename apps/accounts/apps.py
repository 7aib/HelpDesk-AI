"""
Accounts app for HelpDesk-AI.
Handles user authentication and profile management.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the accounts app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self) -> None:
        """Import signal handlers when the app is ready."""
        import apps.accounts.signals  # noqa: F401
