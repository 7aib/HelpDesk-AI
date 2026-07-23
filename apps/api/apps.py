"""
API app for HelpDesk-AI.
REST API endpoints for all apps.
"""

from django.apps import AppConfig


class APIConfig(AppConfig):
    """Configuration for the api app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    verbose_name = "API"
