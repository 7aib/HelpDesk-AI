"""
Utility functions for HelpDesk-AI core app.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import slugify

logger = logging.getLogger(__name__)


def generate_unique_slug(instance: Any, title: str, slug_field: str = "slug") -> str:
    """
    Generate a unique slug for a model instance.
    
    Args:
        instance: The model instance.
        title: The title to slugify.
        slug_field: The name of the slug field.
        
    Returns:
        A unique slug string.
    """
    slug = slugify(title)
    if not slug:
        slug = str(uuid.uuid4())[:8]
    
    # Check for existing slugs
    model_class = instance.__class__
    unique_slug = slug
    counter = 1
    
    while model_class.objects.filter(**{slug_field: unique_slug}).exclude(
        pk=instance.pk
    ).exists():
        unique_slug = f"{slug}-{counter}"
        counter += 1
    
    return unique_slug


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.
    
    Args:
        filename: The filename to extract extension from.
        
    Returns:
        The file extension (lowercase, without dot).
    """
    return Path(filename).suffix.lstrip(".").lower()


def validate_file_type(
    file: UploadedFile,
    allowed_extensions: list[str],
) -> bool:
    """
    Validate that a file has an allowed extension.
    
    Args:
        file: The uploaded file.
        allowed_extensions: List of allowed extensions.
        
    Returns:
        True if file type is allowed, False otherwise.
    """
    extension = get_file_extension(file.name)
    return extension in allowed_extensions


def get_file_size_display(size_bytes: int) -> str:
    """
    Convert file size in bytes to human readable format.
    
    Args:
        size_bytes: File size in bytes.
        
    Returns:
        Human readable file size string.
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_system_stats() -> dict[str, Any]:
    """
    Get system statistics for the dashboard.
    
    Returns:
        Dictionary containing system statistics.
    """
    from apps.chatbots.models import Chatbot
    from apps.chat.models import Conversation, Message
    from apps.documents.models import Document, DocumentChunk
    from apps.knowledge.models import KnowledgeBase

    stats = {
        "total_chatbots": Chatbot.objects.count(),
        "active_chatbots": Chatbot.objects.filter(is_active=True).count(),
        "total_documents": Document.objects.count(),
        "processed_documents": Document.objects.filter(status="completed").count(),
        "total_knowledge_bases": KnowledgeBase.objects.count(),
        "total_chunks": DocumentChunk.objects.count(),
        "total_conversations": Conversation.objects.count(),
        "total_messages": Message.objects.count(),
    }

    # Calculate embedding usage
    from django.db.models import Sum
    chunk_stats = DocumentChunk.objects.aggregate(
        total_tokens=Sum("token_count")
    )
    stats["total_embedding_tokens"] = chunk_stats["total_tokens"] or 0

    return stats


def get_media_file_path(instance: Any, filename: str, subfolder: str = "") -> str:
    """
    Generate a unique media file path.
    
    Args:
        instance: The model instance.
        filename: Original filename.
        subfolder: Optional subfolder within media root.
        
    Returns:
        Unique file path string.
    """
    extension = get_file_extension(filename)
    unique_filename = f"{uuid.uuid4()}.{extension}"
    
    if subfolder:
        return os.path.join(subfolder, unique_filename)
    return unique_filename
