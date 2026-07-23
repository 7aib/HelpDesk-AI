"""
Selectors for HelpDesk-AI accounts app.
Read-only queries for user data.
"""

from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

User = get_user_model()


def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Get a user by their ID.
    
    Args:
        user_id: The user's UUID.
        
    Returns:
        The user instance or None.
    """
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def get_user_by_email(email: str) -> Optional[User]:
    """
    Get a user by their email.
    
    Args:
        email: The email address.
        
    Returns:
        The user instance or None.
    """
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None


def get_user_by_username(username: str) -> Optional[User]:
    """
    Get a user by their username.
    
    Args:
        username: The username.
        
    Returns:
        The user instance or None.
    """
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def get_all_users() -> QuerySet[User]:
    """
    Get all active users.
    
    Returns:
        QuerySet of active users.
    """
    return User.objects.filter(is_active=True)


def get_users_by_company(company: str) -> QuerySet[User]:
    """
    Get all users from a specific company.
    
    Args:
        company: The company name.
        
    Returns:
        QuerySet of users from that company.
    """
    return User.objects.filter(company=company, is_active=True)


def search_users(query: str) -> QuerySet[User]:
    """
    Search users by username, email, or name.
    
    Args:
        query: The search query.
        
    Returns:
        QuerySet of matching users.
    """
    return User.objects.filter(
        Q(username__icontains=query) 
        | Q(email__icontains=query)
        | Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
    )


def get_verified_users() -> QuerySet[User]:
    """
    Get all users with verified emails.
    
    Returns:
        QuerySet of verified users.
    """
    return User.objects.filter(is_email_verified=True, is_active=True)


def get_recent_users(limit: int = 10) -> QuerySet[User]:
    """
    Get the most recently created users.
    
    Args:
        limit: The number of users to return.
        
    Returns:
        QuerySet of recent users.
    """
    return User.objects.filter(is_active=True).order_by("-created_at")[:limit]
