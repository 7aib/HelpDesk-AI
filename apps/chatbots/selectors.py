"""
Selectors for HelpDesk-AI chatbots app.
Read-only queries for chatbot data.
"""

from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .models import Chatbot

User = get_user_model()


def get_chatbot_by_id(chatbot_id: str) -> Optional[Chatbot]:
    """
    Get a chatbot by its ID.
    
    Args:
        chatbot_id: The chatbot's UUID.
        
    Returns:
        The Chatbot instance or None.
    """
    try:
        return Chatbot.objects.get(id=chatbot_id, is_deleted=False)
    except Chatbot.DoesNotExist:
        return None


def get_chatbot_by_slug(slug: str) -> Optional[Chatbot]:
    """
    Get a chatbot by its slug.
    
    Args:
        slug: The chatbot's slug.
        
    Returns:
        The Chatbot instance or None.
    """
    try:
        return Chatbot.objects.get(slug=slug, is_deleted=False)
    except Chatbot.DoesNotExist:
        return None


def get_user_chatbots(user: User) -> QuerySet[Chatbot]:
    """
    Get all chatbots for a user.
    
    Args:
        user: The user.
        
    Returns:
        QuerySet of chatbots.
    """
    return Chatbot.objects.filter(owner=user, is_deleted=False).order_by("-created_at")


def get_active_chatbots(user: User) -> QuerySet[Chatbot]:
    """
    Get all active chatbots for a user.
    
    Args:
        user: The user.
        
    Returns:
        QuerySet of active chatbots.
    """
    return Chatbot.objects.filter(
        owner=user,
        status=Chatbot.Status.ACTIVE,
        is_deleted=False,
    ).order_by("-created_at")


def get_chatbots_by_status(
    user: User,
    status: str,
) -> QuerySet[Chatbot]:
    """
    Get chatbots filtered by status.
    
    Args:
        user: The user.
        status: The status to filter by.
        
    Returns:
        QuerySet of chatbots.
    """
    return Chatbot.objects.filter(
        owner=user,
        status=status,
        is_deleted=False,
    ).order_by("-created_at")


def search_chatbots(
    user: User,
    query: str,
) -> QuerySet[Chatbot]:
    """
    Search chatbots by name or description.
    
    Args:
        user: The user.
        query: The search query.
        
    Returns:
        QuerySet of matching chatbots.
    """
    from django.db.models import Q

    return Chatbot.objects.filter(
        owner=user,
        is_deleted=False,
    ).filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ).order_by("-created_at")


def get_recent_chatbots(user: User, limit: int = 5) -> QuerySet[Chatbot]:
    """
    Get the most recently used chatbots.
    
    Args:
        user: The user.
        limit: The number of chatbots to return.
        
    Returns:
        QuerySet of recent chatbots.
    """
    return Chatbot.objects.filter(
        owner=user,
        is_deleted=False,
    ).exclude(
        last_used_at__isnull=True,
    ).order_by("-last_used_at")[:limit]


def get_chatbot_stats(user: User) -> dict:
    """
    Get statistics for a user's chatbots.
    
    Args:
        user: The user.
        
    Returns:
        Dictionary containing chatbot statistics.
    """
    from django.db.models import Sum

    user_chatbots = Chatbot.objects.filter(owner=user, is_deleted=False)

    stats = {
        "total": user_chatbots.count(),
        "active": user_chatbots.filter(status=Chatbot.Status.ACTIVE).count(),
        "inactive": user_chatbots.filter(status=Chatbot.Status.INACTIVE).count(),
        "draft": user_chatbots.filter(status=Chatbot.Status.DRAFT).count(),
        "total_conversations": user_chatbots.aggregate(
            total=Sum("total_conversations")
        )["total"]
        or 0,
        "total_messages": user_chatbots.aggregate(
            total=Sum("total_messages")
        )["total"]
        or 0,
    }

    return stats
