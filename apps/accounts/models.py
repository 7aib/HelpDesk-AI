"""
Custom User model for HelpDesk-AI.
Extends Django's AbstractUser with additional fields.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model for HelpDesk-AI.
    
    Extends Django's AbstractUser with additional fields
    for profile management and preferences.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this user.",
    )
    email = models.EmailField(
        unique=True,
        help_text="User's email address.",
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        help_text="User's profile avatar.",
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="User's biography.",
    )
    company = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's company name.",
    )
    job_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's job title.",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="User's phone number.",
    )
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        help_text="User's timezone.",
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Whether the user's email has been verified.",
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the last login.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this user was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this user was last updated.",
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.username

    def get_full_name(self) -> str:
        """Return the full name of the user."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    def get_initials(self) -> str:
        """Return user's initials for avatar placeholder."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    def update_last_login_ip(self, ip_address: str) -> None:
        """Update the last login IP address."""
        self.last_login_ip = ip_address
        self.save(update_fields=["last_login_ip"])

    @property
    def chatbot_count(self) -> int:
        """Return the number of chatbots owned by this user."""
        return self.chatbots.count()

    @property
    def total_documents(self) -> int:
        """Return the total number of documents uploaded by this user."""
        from apps.documents.models import Document

        return Document.objects.filter(
            knowledge_base__chatbot__owner=self
        ).count()
