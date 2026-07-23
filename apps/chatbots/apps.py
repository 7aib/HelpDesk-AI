"""
Chatbots app for HelpDesk-AI.
Handles chatbot creation and management.
"""

from django.apps import AppConfig


class ChatbotsConfig(AppConfig):
    """Configuration for the chatbots app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chatbots"
    verbose_name = "Chatbots"
