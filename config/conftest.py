"""
Pytest configuration for HelpDesk-AI.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def chatbot(user):
    """Create a test chatbot."""
    from apps.chatbots.models import Chatbot

    return Chatbot.objects.create(
        owner=user,
        name="Test Chatbot",
        description="A test chatbot",
    )
