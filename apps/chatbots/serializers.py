"""
Serializers for HelpDesk-AI chatbots API.
"""

from rest_framework import serializers

from .models import Chatbot


class ChatbotSerializer(serializers.ModelSerializer):
    """
    Serializer for Chatbot model.
    """

    owner_username = serializers.CharField(source="owner.username", read_only=True)
    document_count = serializers.ReadOnlyField()
    chunk_count = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Chatbot
        fields = [
            "id",
            "owner",
            "owner_username",
            "name",
            "slug",
            "description",
            "avatar",
            "system_prompt",
            "temperature",
            "top_p",
            "max_context_length",
            "embedding_model",
            "llm_model",
            "top_k",
            "chunk_size",
            "chunk_overlap",
            "status",
            "is_active",
            "total_conversations",
            "total_messages",
            "document_count",
            "chunk_count",
            "last_used_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "owner",
            "total_conversations",
            "total_messages",
            "last_used_at",
            "created_at",
            "updated_at",
        ]


class ChatbotCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new chatbot.
    """

    class Meta:
        model = Chatbot
        fields = [
            "name",
            "description",
            "system_prompt",
            "temperature",
            "top_p",
            "max_context_length",
            "embedding_model",
            "llm_model",
            "top_k",
            "chunk_size",
            "chunk_overlap",
        ]

    def create(self, validated_data):
        """Create a new chatbot with the current user as owner."""
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


class ChatbotUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a chatbot.
    """

    class Meta:
        model = Chatbot
        fields = [
            "name",
            "description",
            "system_prompt",
            "temperature",
            "top_p",
            "max_context_length",
            "embedding_model",
            "llm_model",
            "top_k",
            "chunk_size",
            "chunk_overlap",
            "status",
        ]


class ChatbotListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing chatbots.
    """

    is_active = serializers.ReadOnlyField()
    document_count = serializers.ReadOnlyField()

    class Meta:
        model = Chatbot
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "status",
            "is_active",
            "document_count",
            "total_conversations",
            "last_used_at",
            "created_at",
        ]
