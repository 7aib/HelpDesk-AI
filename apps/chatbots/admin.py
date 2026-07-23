"""
Admin configuration for HelpDesk-AI chatbots app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Chatbot


@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    """Admin for Chatbot model."""

    list_display = [
        "name",
        "owner",
        "status",
        "llm_model",
        "embedding_model",
        "document_count",
        "total_conversations",
        "last_used_at",
        "created_at",
    ]
    list_filter = [
        "status",
        "llm_model",
        "embedding_model",
    ]
    search_fields = [
        "name",
        "description",
        "owner__username",
    ]
    readonly_fields = [
        "id",
        "slug",
        "total_conversations",
        "total_messages",
        "last_used_at",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    def document_count(self, obj):
        """Display document count."""
        return obj.document_count

    document_count.short_description = "Documents"
