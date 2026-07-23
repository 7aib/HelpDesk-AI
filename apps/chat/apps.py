"""
Chat app for HelpDesk-AI.
Handles conversations and messages.
"""

from django.apps import AppConfig


class ChatConfig(AppConfig):
    """Configuration for the chat app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"
    verbose_name = "Chat"
