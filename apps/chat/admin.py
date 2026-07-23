"""
Admin configuration for HelpDesk-AI chat app.
"""

from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin for Conversation model."""

    list_display = [
        "title",
        "chatbot",
        "user",
        "message_count",
        "last_message_at",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
    ]
    search_fields = [
        "title",
        "chatbot__name",
        "user__username",
    ]
    readonly_fields = [
        "id",
        "session_id",
        "message_count",
        "last_message_at",
        "created_at",
        "updated_at",
    ]
    ordering = ["-last_message_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin for Message model."""

    list_display = [
        "conversation",
        "role",
        "content_preview",
        "tokens_used",
        "created_at",
    ]
    list_filter = [
        "role",
    ]
    search_fields = [
        "content",
        "conversation__title",
    ]
    readonly_fields = [
        "id",
        "tokens_used",
        "metadata",
        "created_at",
    ]
    ordering = ["created_at"]

    def content_preview(self, obj):
        """Display content preview."""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content"
