"""
Admin configuration for HelpDesk-AI knowledge app.
"""

from django.contrib import admin

from .models import DocumentChunk, KnowledgeBase, QAPair


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    """Admin for KnowledgeBase model."""

    list_display = [
        "name",
        "chatbot",
        "total_documents",
        "total_chunks",
        "total_tokens",
        "created_at",
    ]
    search_fields = [
        "name",
        "chatbot__name",
    ]
    readonly_fields = [
        "id",
        "total_documents",
        "total_chunks",
        "total_tokens",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """Admin for DocumentChunk model."""

    list_display = [
        "document",
        "chunk_index",
        "page_number",
        "token_count",
        "created_at",
    ]
    list_filter = [
        "document__document_type",
    ]
    search_fields = [
        "content",
        "document__title",
    ]
    readonly_fields = [
        "id",
        "embedding",
        "chunk_index",
        "page_number",
        "token_count",
        "created_at",
    ]
    ordering = ["document", "chunk_index"]


@admin.register(QAPair)
class QAPairAdmin(admin.ModelAdmin):
    """Admin for QAPair model."""

    list_display = [
        "question",
        "knowledge_base",
        "category",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "category",
    ]
    search_fields = [
        "question",
        "answer",
    ]
    readonly_fields = [
        "id",
        "embedding",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
