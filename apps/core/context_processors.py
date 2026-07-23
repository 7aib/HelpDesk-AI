"""
Context processors for HelpDesk-AI.
Provides global template context variables.
"""

from typing import Any

from django.http import HttpRequest

from apps.core.utils import get_system_stats


def global_context(request: HttpRequest) -> dict[str, Any]:
    """
    Add global context variables to all templates.
    
    Args:
        request: The HTTP request object.
        
    Returns:
        Dictionary containing global context variables.
    """
    context: dict[str, Any] = {
        "app_name": "HelpDesk AI",
        "app_version": "1.0.0",
    }

    # Add system stats for staff users
    if request.user.is_authenticated and request.user.is_staff:
        try:
            context["system_stats"] = get_system_stats()
        except Exception:
            context["system_stats"] = {}

    return context
