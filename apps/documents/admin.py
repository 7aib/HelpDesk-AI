"""
Admin configuration for HelpDesk-AI documents app.
"""

from django.contrib import admin

from .models import Document, DocumentProcessLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for Document model."""

    list_display = [
        "title",
        "knowledge_base",
        "document_type",
        "status",
        "file_size_display",
        "chunk_count",
        "processed_at",
        "created_at",
    ]
    list_filter = [
        "document_type",
        "status",
    ]
    search_fields = [
        "title",
        "knowledge_base__name",
    ]
    readonly_fields = [
        "id",
        "file_size",
        "page_count",
        "chunk_count",
        "error_message",
        "processed_at",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]

    def file_size_display(self, obj):
        """Display file size."""
        return obj.file_size_display

    file_size_display.short_description = "Size"


@admin.register(DocumentProcessLog)
class DocumentProcessLogAdmin(admin.ModelAdmin):
    """Admin for DocumentProcessLog model."""

    list_display = [
        "document",
        "event",
        "status",
        "duration",
        "created_at",
    ]
    list_filter = [
        "event",
        "status",
    ]
    search_fields = [
        "document__title",
        "message",
    ]
    readonly_fields = [
        "id",
        "duration",
        "created_at",
    ]
    ordering = ["-created_at"]
