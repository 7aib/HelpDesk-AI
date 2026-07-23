"""
Models for HelpDesk-AI documents app.
"""

from django.db import models

from apps.core.models import BaseModel
from apps.core.utils import get_file_size_display


class Document(BaseModel):
    """
    Document model for HelpDesk-AI.
    
    Stores uploaded documents and their processing status.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class DocumentType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"
        TXT = "txt", "Text"
        MD = "md", "Markdown"
        QA = "qa", "Q&A Pair"

    knowledge_base = models.ForeignKey(
        "knowledge.KnowledgeBase",
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="The knowledge base this document belongs to.",
    )
    title = models.CharField(
        max_length=200,
        help_text="Document title.",
    )
    file = models.FileField(
        upload_to="documents/%Y/%m/",
        null=True,
        blank=True,
        help_text="Uploaded file.",
    )
    document_type = models.CharField(
        max_length=10,
        choices=DocumentType.choices,
        help_text="Type of document.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Processing status.",
    )
    file_size = models.IntegerField(
        default=0,
        help_text="File size in bytes.",
    )
    page_count = models.IntegerField(
        default=0,
        help_text="Number of pages (for PDFs).",
    )
    chunk_count = models.IntegerField(
        default=0,
        help_text="Number of chunks created.",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if processing failed.",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the document was processed.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional document metadata.",
    )

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def file_size_display(self) -> str:
        """Get human-readable file size."""
        return get_file_size_display(self.file_size)

    @property
    def is_processed(self) -> bool:
        """Check if document has been processed."""
        return self.status == self.Status.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if document processing failed."""
        return self.status == self.Status.FAILED

    def mark_processing(self):
        """Mark document as being processed."""
        self.status = self.Status.PROCESSING
        self.save(update_fields=["status", "updated_at"])

    def mark_completed(self, chunk_count: int):
        """Mark document as completed."""
        from django.utils import timezone

        self.status = self.Status.COMPLETED
        self.chunk_count = chunk_count
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "chunk_count", "processed_at", "updated_at"])

    def mark_failed(self, error_message: str):
        """Mark document as failed."""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])


class DocumentProcessLog(BaseModel):
    """
    Log for document processing events.
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="process_logs",
        help_text="The document this log belongs to.",
    )
    event = models.CharField(
        max_length=50,
        help_text="Event type (e.g., 'upload', 'extract', 'chunk', 'embed').",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("started", "Started"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        help_text="Event status.",
    )
    message = models.TextField(
        blank=True,
        help_text="Log message.",
    )
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration in seconds.",
    )

    class Meta:
        verbose_name = "Document Process Log"
        verbose_name_plural = "Document Process Logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event} - {self.document.title}"
