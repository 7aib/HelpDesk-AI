"""
Views for HelpDesk-AI accounts app.
"""

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, UpdateView

from .forms import UserProfileForm
from .services import UserService

User = get_user_model()


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view.
    """

    template_name = "accounts/dashboard.html"
    context_object_name = "user_stats"

    def get_context_data(self, **kwargs: dict) -> dict:
        """Add user stats to context."""
        context = super().get_context_data(**kwargs)
        context["user_stats"] = UserService.get_user_stats(self.request.user)
        context["recent_chatbots"] = self.request.user.chatbots.all()[:5]
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    User profile view.
    """

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs: dict) -> dict:
        """Add user profile to context."""
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update user profile view.
    """

    model = User
    form_class = UserProfileForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        """Return the current user."""
        return self.request.user

    def form_valid(self, form):
        """Save the form and add success message."""
        response = super().form_valid(form)
        from django.contrib import messages

        messages.success(self.request, "Profile updated successfully.")
        return response


class SettingsView(LoginRequiredMixin, TemplateView):
    """
    User settings view.
    """

    template_name = "accounts/settings.html"


class AccountDeleteView(LoginRequiredMixin, View):
    """
    Delete user account view.
    """

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Show confirmation page."""
        return render(request, "accounts/account_delete_confirm.html")

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Delete the user account."""
        user = request.user
        logout(request)
        user.delete()
        return redirect("home")
