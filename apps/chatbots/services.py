"""
Services for HelpDesk-AI chatbots app.
Business logic for chatbot management.
"""

import logging
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .models import Chatbot

logger = logging.getLogger(__name__)

User = get_user_model()


class ChatbotService:
    """
    Service class for chatbot operations.
    
    Provides methods for creating, updating, and managing chatbots.
    """

    @staticmethod
    def create_chatbot(
        owner: User,
        name: str,
        description: str = "",
        system_prompt: str = "",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_context_length: int = 4096,
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        llm_model: str = "llama3.2",
        top_k: int = 5,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        **kwargs: Any,
    ) -> Chatbot:
        """
        Create a new chatbot.
        
        Args:
            owner: The user who owns the chatbot.
            name: Name of the chatbot.
            description: Description of the chatbot.
            system_prompt: System prompt for the LLM.
            temperature: LLM temperature.
            top_p: LLM top_p.
            max_context_length: Maximum context length.
            embedding_model: Embedding model name.
            llm_model: LLM model name.
            top_k: Number of similar chunks to retrieve.
            chunk_size: Size of text chunks.
            chunk_overlap: Overlap between chunks.
            
        Returns:
            The created Chatbot instance.
        """
        if not system_prompt:
            system_prompt = Chatbot._meta.get_field("system_prompt").default

        chatbot = Chatbot.objects.create(
            owner=owner,
            name=name,
            description=description,
            system_prompt=system_prompt,
            temperature=temperature,
            top_p=top_p,
            max_context_length=max_context_length,
            embedding_model=embedding_model,
            llm_model=llm_model,
            top_k=top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs,
        )

        # Create associated knowledge base
        from apps.knowledge.models import KnowledgeBase

        KnowledgeBase.objects.create(
            chatbot=chatbot,
            name=f"{name} Knowledge Base",
            description=f"Knowledge base for {name}",
        )

        logger.info(f"Chatbot created: {chatbot.name} (ID: {chatbot.id})")
        return chatbot

    @staticmethod
    def update_chatbot(chatbot: Chatbot, **kwargs: Any) -> Chatbot:
        """
        Update a chatbot.
        
        Args:
            chatbot: The chatbot to update.
            **kwargs: Fields to update.
            
        Returns:
            The updated Chatbot instance.
        """
        for field, value in kwargs.items():
            if hasattr(chatbot, field):
                setattr(chatbot, field, value)

        chatbot.save()
        logger.info(f"Chatbot updated: {chatbot.name} (ID: {chatbot.id})")
        return chatbot

    @staticmethod
    def delete_chatbot(chatbot: Chatbot) -> bool:
        """
        Soft delete a chatbot.
        
        Args:
            chatbot: The chatbot to delete.
            
        Returns:
            True if successful.
        """
        chatbot.soft_delete()
        logger.info(f"Chatbot deleted: {chatbot.name} (ID: {chatbot.id})")
        return True

    @staticmethod
    def get_chatbot_by_id(chatbot_id: str) -> Optional[Chatbot]:
        """
        Get a chatbot by its ID.
        
        Args:
            chatbot_id: The chatbot's UUID.
            
        Returns:
            The Chatbot instance or None.
        """
        try:
            return Chatbot.objects.get(id=chatbot_id)
        except Chatbot.DoesNotExist:
            logger.warning(f"Chatbot with ID {chatbot_id} not found.")
            return None

    @staticmethod
    def get_chatbot_by_slug(slug: str) -> Optional[Chatbot]:
        """
        Get a chatbot by its slug.
        
        Args:
            slug: The chatbot's slug.
            
        Returns:
            The Chatbot instance or None.
        """
        try:
            return Chatbot.objects.get(slug=slug)
        except Chatbot.DoesNotExist:
            logger.warning(f"Chatbot with slug {slug} not found.")
            return None

    @staticmethod
    def get_user_chatbots(
        user: User,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> QuerySet[Chatbot]:
        """
        Get all chatbots for a user.
        
        Args:
            user: The user.
            status: Filter by status.
            search: Search in name/description.
            
        Returns:
            QuerySet of chatbots.
        """
        queryset = Chatbot.objects.filter(owner=user, is_deleted=False)

        if status:
            queryset = queryset.filter(status=status)

        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        return queryset.order_by("-created_at")

    @staticmethod
    def activate_chatbot(chatbot: Chatbot) -> Chatbot:
        """
        Activate a chatbot.
        
        Args:
            chatbot: The chatbot to activate.
            
        Returns:
            The activated Chatbot.
        """
        chatbot.activate()
        return chatbot

    @staticmethod
    def deactivate_chatbot(chatbot: Chatbot) -> Chatbot:
        """
        Deactivate a chatbot.
        
        Args:
            chatbot: The chatbot to deactivate.
            
        Returns:
            The deactivated Chatbot.
        """
        chatbot.deactivate()
        return chatbot

    @staticmethod
    def duplicate_chatbot(
        original: Chatbot,
        new_owner: Optional[User] = None,
        new_name: Optional[str] = None,
    ) -> Chatbot:
        """
        Create a duplicate of a chatbot.
        
        Args:
            original: The chatbot to duplicate.
            new_owner: Optional new owner.
            new_name: Optional new name.
            
        Returns:
            The new Chatbot instance.
        """
        owner = new_owner or original.owner
        name = new_name or f"{original.name} (Copy)"

        new_chatbot = ChatbotService.create_chatbot(
            owner=owner,
            name=name,
            description=original.description,
            system_prompt=original.system_prompt,
            temperature=original.temperature,
            top_p=original.top_p,
            max_context_length=original.max_context_length,
            embedding_model=original.embedding_model,
            llm_model=original.llm_model,
            top_k=original.top_k,
            chunk_size=original.chunk_size,
            chunk_overlap=original.chunk_overlap,
        )

        logger.info(f"Chatbot duplicated: {original.name} -> {new_chatbot.name}")
        return new_chatbot
