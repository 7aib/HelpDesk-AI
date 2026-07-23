"""
Serializers for HelpDesk-AI chat API.
"""

from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model.
    """

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "role",
            "content",
            "metadata",
            "tokens_used",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MessageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing messages.
    """

    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation model.
    """

    message_count = serializers.ReadOnlyField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "chatbot",
            "user",
            "title",
            "session_id",
            "is_active",
            "message_count",
            "last_message_at",
            "last_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "session_id",
            "message_count",
            "last_message_at",
            "created_at",
            "updated_at",
        ]

    def get_last_message(self, obj: Conversation) -> dict | None:
        """Get the last message in the conversation."""
        last_msg = obj.messages.order_by("-created_at").first()
        if last_msg:
            return {
                "content": last_msg.content[:100],
                "role": last_msg.role,
                "created_at": last_msg.created_at,
            }
        return None


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing conversations.
    """

    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "message_count",
            "last_message_at",
            "last_message",
            "created_at",
        ]

    def get_last_message(self, obj: Conversation) -> dict | None:
        """Get the last message in the conversation."""
        last_msg = obj.messages.order_by("-created_at").first()
        if last_msg:
            return {
                "content": last_msg.content[:100],
                "role": last_msg.role,
            }
        return None


class ChatRequestSerializer(serializers.Serializer):
    """
    Serializer for chat request.
    """

    chatbot_id = serializers.UUIDField(required=True)
    message = serializers.CharField(required=True, min_length=1)
    conversation_id = serializers.UUIDField(required=False)


class ChatResponseSerializer(serializers.Serializer):
    """
    Serializer for chat response.
    """

    conversation_id = serializers.UUIDField()
    message = MessageSerializer()
