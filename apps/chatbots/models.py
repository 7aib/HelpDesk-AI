"""
Models for HelpDesk-AI chatbots app.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Chatbot(BaseModel):
    """
    Chatbot model for HelpDesk-AI.
    
    Each chatbot has its own knowledge base, configuration,
    and conversation history.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DRAFT = "draft", "Draft"

    # Basic information
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chatbots",
        help_text="The user who owns this chatbot.",
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the chatbot.",
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        help_text="URL-friendly identifier.",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the chatbot's purpose.",
    )
    avatar = models.ImageField(
        upload_to="chatbot_avatars/",
        null=True,
        blank=True,
        help_text="Chatbot avatar image.",
    )

    # Configuration
    system_prompt = models.TextField(
        default="You are a helpful customer support assistant. Answer questions only based on the provided context. If you don't know the answer based on the context, say 'I don't know based on the provided knowledge.'",
        help_text="System prompt for the LLM.",
    )
    temperature = models.FloatField(
        default=0.7,
        help_text="Temperature for LLM generation (0.0 to 2.0).",
    )
    top_p = models.FloatField(
        default=0.9,
        help_text="Top P for LLM generation (0.0 to 1.0).",
    )
    max_context_length = models.IntegerField(
        default=4096,
        help_text="Maximum context length for the LLM.",
    )
    embedding_model = models.CharField(
        max_length=100,
        default="BAAI/bge-small-en-v1.5",
        help_text="Embedding model to use.",
    )
    llm_model = models.CharField(
        max_length=100,
        default="llama3.2",
        help_text="LLM model to use.",
    )
    top_k = models.IntegerField(
        default=5,
        help_text="Number of similar chunks to retrieve.",
    )

    # Chunking settings
    chunk_size = models.IntegerField(
        default=500,
        help_text="Size of text chunks for embedding.",
    )
    chunk_overlap = models.IntegerField(
        default=50,
        help_text="Overlap between chunks.",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Current status of the chatbot.",
    )

    # Statistics
    total_conversations = models.IntegerField(
        default=0,
        help_text="Total number of conversations.",
    )
    total_messages = models.IntegerField(
        default=0,
        help_text="Total number of messages.",
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the chatbot was last used.",
    )

    class Meta:
        verbose_name = "Chatbot"
        verbose_name_plural = "Chatbots"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Save the chatbot instance."""
        from apps.core.utils import generate_unique_slug

        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        """Check if the chatbot is active."""
        return self.status == self.Status.ACTIVE

    def activate(self):
        """Activate the chatbot."""
        self.status = self.Status.ACTIVE
        self.save(update_fields=["status", "updated_at"])

    def deactivate(self):
        """Deactivate the chatbot."""
        self.status = self.Status.INACTIVE
        self.save(update_fields=["status", "updated_at"])

    def update_usage_stats(self):
        """Update conversation and message statistics."""
        self.total_conversations = self.conversations.count()
        self.total_messages = sum(
            conv.messages.count() for conv in self.conversations.all()
        )
        self.last_used_at = timezone.now()
        self.save(update_fields=["total_conversations", "total_messages", "last_used_at"])

    @property
    def knowledge_base(self):
        """Get the knowledge base for this chatbot."""
        return self.knowledge_bases.first()

    @property
    def document_count(self) -> int:
        """Get the number of documents in the knowledge base."""
        from apps.documents.models import Document

        return Document.objects.filter(
            knowledge_base__chatbot=self,
            status="completed",
        ).count()

    @property
    def chunk_count(self) -> int:
        """Get the total number of chunks in the knowledge base."""
        from apps.documents.models import DocumentChunk

        return DocumentChunk.objects.filter(
            document__knowledge_base__chatbot=self,
        ).count()
