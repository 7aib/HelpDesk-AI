"""
URL configuration for HelpDesk-AI accounts app.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile-edit"),
    # Settings
    path("settings/", views.SettingsView.as_view(), name="settings"),
    # Account
    path("delete/", views.AccountDeleteView.as_view(), name="account-delete"),
]
