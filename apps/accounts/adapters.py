"""
Allauth adapter for HelpDesk-AI.
Customizes allauth behavior for user registration.
"""

from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    """
    Custom Allauth adapter for HelpDesk-AI.
    
    Handles user registration customization and email settings.
    """

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """
        Determine if registration is open.
        
        Args:
            request: The HTTP request.
            
        Returns:
            True if signup is open, False otherwise.
        """
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def save_user(
        self,
        request: HttpRequest,
        user: Any,
        form: Any,
        commit: bool = True,
    ) -> Any:
        """
        Save a new user instance.
        
        Args:
            request: The HTTP request.
            user: The user instance.
            form: The registration form.
            commit: Whether to save to database.
            
        Returns:
            The saved user instance.
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Set default values
        if not user.timezone:
            user.timezone = "UTC"
        
        if commit:
            user.save()
        
        return user

    def get_login_redirect_url(self, request: HttpRequest) -> str:
        """
        Get the URL to redirect to after login.
        
        Args:
            request: The HTTP request.
            
        Returns:
            The redirect URL.
        """
        return settings.LOGIN_REDIRECT_URL

    def get_signup_redirect_url(self, request: HttpRequest) -> str:
        """
        Get the URL to redirect to after signup.
        
        Args:
            request: The HTTP request.
            
        Returns:
            The redirect URL.
        """
        return settings.LOGIN_REDIRECT_URL
