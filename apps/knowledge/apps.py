"""
Knowledge app for HelpDesk-AI.
Handles knowledge base management.
"""

from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    """Configuration for the knowledge app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.knowledge"
    verbose_name = "Knowledge"
