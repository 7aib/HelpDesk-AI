"""
Documents app for HelpDesk-AI.
Handles document upload, parsing, and processing.
"""

from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    """Configuration for the documents app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"
    verbose_name = "Documents"
