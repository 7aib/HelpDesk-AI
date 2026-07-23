"""
Models for HelpDesk-AI chat app.
"""

from django.db import models

from apps.core.models import BaseModel


class Conversation(BaseModel):
    """
    Conversation model for HelpDesk-AI.
    
    Stores chat sessions between users and chatbots.
    """

    chatbot = models.ForeignKey(
        "chatbots.Chatbot",
        on_delete=models.CASCADE,
        related_name="conversations",
        help_text="The chatbot in this conversation.",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
        help_text="The user (if authenticated).",
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Conversation title.",
    )
    session_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique session identifier.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the conversation is active.",
    )
    message_count = models.IntegerField(
        default=0,
        help_text="Number of messages in this conversation.",
    )
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last message.",
    )

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-last_message_at"]

    def __str__(self) -> str:
        return f"{self.title or self.session_id}"

    def update_message_count(self):
        """Update the message count."""
        self.message_count = self.messages.count()
        self.save(update_fields=["message_count", "updated_at"])


class Message(BaseModel):
    """
    Message model for HelpDesk-AI.
    
    Stores individual messages within a conversation.
    """

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="The conversation this message belongs to.",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        help_text="Message role (user, assistant, or system).",
    )
    content = models.TextField(
        help_text="Message content.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional message metadata (sources, model used, etc.).",
    )
    tokens_used = models.IntegerField(
        default=0,
        help_text="Number of tokens used in this message.",
    )

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:50]}..."

    def save(self, *args, **kwargs):
        """Save the message and update conversation."""
        super().save(*args, **kwargs)
        # Update conversation
        conversation = self.conversation
        conversation.last_message_at = self.created_at
        conversation.update_message_count()

    @property
    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == self.Role.USER

    @property
    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == self.Role.ASSISTANT

    @property
    def sources(self) -> list[dict]:
        """Get sources from message metadata."""
        return self.metadata.get("sources", [])
