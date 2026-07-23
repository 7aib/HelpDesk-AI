"""
Admin configuration for HelpDesk-AI accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom admin for User model."""

    model = User
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "company",
        "is_staff",
        "is_active",
    ]
    list_filter = [
        "is_staff",
        "is_active",
        "is_email_verified",
    ]
    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
    ]
    ordering = ["-created_at"]

    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional Info",
            {
                "fields": (
                    "avatar",
                    "bio",
                    "company",
                    "job_title",
                    "phone",
                    "timezone",
                    "is_email_verified",
                    "last_login_ip",
                ),
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Additional Info",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "company",
                ),
            },
        ),
    )
