"""
Base models for HelpDesk-AI.
Provides abstract base classes with common functionality.
"""

import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model with created/updated timestamps.
    
    Provides automatic timestamp management for all models
    that inherit from this class.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated.",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self.id})"


class SoftDeleteModel(models.Model):
    """
    Abstract base model with soft delete functionality.
    
    Records are not physically deleted but marked as deleted
    with a timestamp.
    """

    is_deleted = models.BooleanField(
        default=False,
        help_text="Whether this record has been soft deleted.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this record was soft deleted.",
    )

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        """Mark this record as deleted."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """
    Abstract base model with timestamps and soft delete.
    
    Combines TimeStampedModel and SoftDeleteModel for
    complete audit trail functionality.
    """

    class Meta(TimeStampedModel.Meta):
        abstract = True
