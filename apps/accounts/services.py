"""
Services for HelpDesk-AI accounts app.
Business logic for user management.
"""

import logging
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q, QuerySet
from django.http import HttpRequest

logger = logging.getLogger(__name__)

User = get_user_model()


class UserService:
    """
    Service class for user-related operations.
    
    Provides methods for user management and profile operations.
    """

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """
        Get a user by their ID.
        
        Args:
            user_id: The user's UUID.
            
        Returns:
            The user instance or None if not found.
        """
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"User with ID {user_id} not found.")
            return None

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Get a user by their email address.
        
        Args:
            email: The user's email.
            
        Returns:
            The user instance or None if not found.
        """
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"User with email {email} not found.")
            return None

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """
        Get a user by their username.
        
        Args:
            username: The username.
            
        Returns:
            The user instance or None if not found.
        """
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning(f"User with username {username} not found.")
            return None

    @staticmethod
    def update_user_profile(user: User, **kwargs: Any) -> User:
        """
        Update user profile fields.
        
        Args:
            user: The user instance to update.
            **kwargs: Fields to update.
            
        Returns:
            The updated user instance.
        """
        for field, value in kwargs.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.save()
        logger.info(f"User profile updated for {user.username}.")
        return user

    @staticmethod
    def get_user_stats(user: User) -> dict[str, Any]:
        """
        Get statistics for a user.
        
        Args:
            user: The user instance.
            
        Returns:
            Dictionary containing user statistics.
        """
        from apps.chatbots.models import Chatbot
        from apps.documents.models import Document

        stats = {
            "chatbot_count": Chatbot.objects.filter(owner=user).count(),
            "document_count": Document.objects.filter(
                knowledge_base__chatbot__owner=user
            ).count(),
            "is_email_verified": user.is_email_verified,
            "member_since": user.created_at,
        }
        return stats

    @staticmethod
    def search_users(query: str) -> QuerySet[User]:
        """
        Search users by username or email.
        
        Args:
            query: The search query.
            
        Returns:
            QuerySet of matching users.
        """
        return User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )

    @staticmethod
    def deactivate_user(user: User) -> User:
        """
        Deactivate a user account.
        
        Args:
            user: The user to deactivate.
            
        Returns:
            The deactivated user instance.
        """
        user.is_active = False
        user.save(update_fields=["is_active"])
        logger.info(f"User {user.username} deactivated.")
        return user

    @staticmethod
    def activate_user(user: User) -> User:
        """
        Activate a user account.
        
        Args:
            user: The user to activate.
            
        Returns:
            The activated user instance.
        """
        user.is_active = True
        user.save(update_fields=["is_active"])
        logger.info(f"User {user.username} activated.")
        return user


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows login with email.
    """

    def authenticate(
        self,
        request: HttpRequest,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[User]:
        """
        Authenticate a user by email or username.
        
        Args:
            request: The HTTP request.
            username: The email or username.
            password: The password.
            
        Returns:
            The authenticated user or None.
        """
        if username is None:
            return None
        
        # Try to get user by email first
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Try by username
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
