"""
Models for HelpDesk-AI knowledge app.
"""

from django.db import models
from pgvector.django import VectorField

from apps.core.models import BaseModel


class KnowledgeBase(BaseModel):
    """
    Knowledge base model for HelpDesk-AI.
    
    Each chatbot has an associated knowledge base that contains
    documents and their embeddings.
    """

    chatbot = models.OneToOneField(
        "chatbots.Chatbot",
        on_delete=models.CASCADE,
        related_name="knowledge_bases",
        help_text="The chatbot this knowledge base belongs to.",
    )
    name = models.CharField(
        max_length=200,
        help_text="Name of the knowledge base.",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the knowledge base.",
    )
    total_documents = models.IntegerField(
        default=0,
        help_text="Total number of documents.",
    )
    total_chunks = models.IntegerField(
        default=0,
        help_text="Total number of chunks.",
    )
    total_tokens = models.IntegerField(
        default=0,
        help_text="Total number of tokens.",
    )

    class Meta:
        verbose_name = "Knowledge Base"
        verbose_name_plural = "Knowledge Bases"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def update_stats(self):
        """Update knowledge base statistics."""
        self.total_documents = self.documents.count()
        from django.db.models import Sum

        chunk_stats = DocumentChunk.objects.filter(
            document__knowledge_base=self
        ).aggregate(
            total_chunks=models.Count("id"),
            total_tokens=Sum("token_count"),
        )
        self.total_chunks = chunk_stats["total_chunks"] or 0
        self.total_tokens = chunk_stats["total_tokens"] or 0
        self.save(update_fields=["total_documents", "total_chunks", "total_tokens"])


class DocumentChunk(BaseModel):
    """
    Document chunk model for HelpDesk-AI.
    
    Stores individual chunks of documents with their embeddings
    for vector search.
    """

    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="chunks",
        help_text="The document this chunk belongs to.",
    )
    content = models.TextField(
        help_text="The text content of the chunk.",
    )
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="Vector embedding of the chunk content.",
    )
    chunk_index = models.IntegerField(
        help_text="Index of this chunk in the document.",
    )
    page_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Page number for PDF documents.",
    )
    token_count = models.IntegerField(
        default=0,
        help_text="Number of tokens in this chunk.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata for the chunk.",
    )

    class Meta:
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        ordering = ["document", "chunk_index"]

    def __str__(self) -> str:
        return f"Chunk {self.chunk_index} of {self.document}"


class QAPair(BaseModel):
    """
    Question-Answer pair for manual knowledge entry.
    """

    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="qa_pairs",
        help_text="The knowledge base this QA pair belongs to.",
    )
    question = models.TextField(
        help_text="The question.",
    )
    answer = models.TextField(
        help_text="The answer.",
    )
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="Vector embedding of the question.",
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional category for the QA pair.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this QA pair is active.",
    )

    class Meta:
        verbose_name = "QA Pair"
        verbose_name_plural = "QA Pairs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Q: {self.question[:50]}..."
