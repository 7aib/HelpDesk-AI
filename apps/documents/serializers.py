"""
Serializers for HelpDesk-AI documents API.
"""

from rest_framework import serializers

from .models import Document, DocumentProcessLog


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for Document model.
    """

    file_size_display = serializers.ReadOnlyField()
    is_processed = serializers.ReadOnlyField()
    is_failed = serializers.ReadOnlyField()
    knowledge_base_name = serializers.CharField(
        source="knowledge_base.name",
        read_only=True,
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "knowledge_base",
            "knowledge_base_name",
            "title",
            "file",
            "document_type",
            "status",
            "file_size",
            "file_size_display",
            "page_count",
            "chunk_count",
            "error_message",
            "processed_at",
            "is_processed",
            "is_failed",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "file_size",
            "page_count",
            "chunk_count",
            "error_message",
            "processed_at",
            "created_at",
            "updated_at",
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing documents.
    """

    file_size_display = serializers.ReadOnlyField()
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "document_type",
            "status",
            "status_display",
            "file_size",
            "file_size_display",
            "chunk_count",
            "created_at",
        ]


class DocumentProcessLogSerializer(serializers.ModelSerializer):
    """
    Serializer for DocumentProcessLog model.
    """

    class Meta:
        model = DocumentProcessLog
        fields = [
            "id",
            "document",
            "event",
            "status",
            "message",
            "duration",
            "created_at",
        ]
