"""
Serializers for HelpDesk-AI knowledge API.
"""

from rest_framework import serializers

from .models import KnowledgeBase, QAPair


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """
    Serializer for KnowledgeBase model.
    """

    chatbot_name = serializers.CharField(source="chatbot.name", read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = [
            "id",
            "chatbot",
            "chatbot_name",
            "name",
            "description",
            "total_documents",
            "total_chunks",
            "total_tokens",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_documents",
            "total_chunks",
            "total_tokens",
            "created_at",
            "updated_at",
        ]


class QAPairSerializer(serializers.ModelSerializer):
    """
    Serializer for QAPair model.
    """

    class Meta:
        model = QAPair
        fields = [
            "id",
            "knowledge_base",
            "question",
            "answer",
            "category",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class QAPairListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing Q&A pairs.
    """

    class Meta:
        model = QAPair
        fields = [
            "id",
            "question",
            "answer",
            "category",
            "is_active",
            "created_at",
        ]
