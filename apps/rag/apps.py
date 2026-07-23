"""
RAG app for HelpDesk-AI.
Handles embeddings, vector search, and RAG pipeline.
"""

from django.apps import AppConfig


class RAGConfig(AppConfig):
    """Configuration for the rag app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rag"
    verbose_name = "RAG"
