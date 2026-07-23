"""
Views for HelpDesk-AI chatbots app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .models import Chatbot
from .selectors import get_chatbot_by_id, get_user_chatbots, search_chatbots
from .services import ChatbotService


class ChatbotListView(LoginRequiredMixin, ListView):
    """
    List all chatbots for the current user.
    """

    model = Chatbot
    template_name = "chatbots/chatbot_list.html"
    context_object_name = "chatbots"
    paginate_by = 12

    def get_queryset(self):
        """Filter chatbots by current user."""
        queryset = Chatbot.objects.filter(
            owner=self.request.user,
            is_deleted=False,
        )

        # Search
        search_query = self.request.GET.get("q")
        if search_query:
            queryset = search_chatbots(self.request.user, search_query)

        # Filter by status
        status_filter = self.request.GET.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        """Add extra context."""
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["status_filter"] = self.request.GET.get("status", "")
        return context


class ChatbotCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new chatbot.
    """

    model = Chatbot
    template_name = "chatbots/chatbot_form.html"
    fields = [
        "name",
        "description",
        "system_prompt",
        "temperature",
        "top_p",
        "max_context_length",
        "embedding_model",
        "llm_model",
        "top_k",
        "chunk_size",
        "chunk_overlap",
    ]
    success_url = reverse_lazy("chatbots:list")

    def form_valid(self, form):
        """Set the owner to the current user."""
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Chatbot '{self.object.name}' created successfully.")
        return response


class ChatbotDetailView(LoginRequiredMixin, TemplateView):
    """
    View chatbot details.
    """

    template_name = "chatbots/chatbot_detail.html"

    def get_context_data(self, **kwargs):
        """Add chatbot to context."""
        context = super().get_context_data(**kwargs)
        chatbot = get_object_or_404(
            Chatbot,
            id=self.kwargs["pk"],
            owner=self.request.user,
            is_deleted=False,
        )
        context["chatbot"] = chatbot
        context["knowledge_base"] = chatbot.knowledge_base
        return context


class ChatbotUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update a chatbot.
    """

    model = Chatbot
    template_name = "chatbots/chatbot_form.html"
    fields = [
        "name",
        "description",
        "system_prompt",
        "temperature",
        "top_p",
        "max_context_length",
        "embedding_model",
        "llm_model",
        "top_k",
        "chunk_size",
        "chunk_overlap",
        "status",
    ]

    def get_success_url(self):
        """Redirect to chatbot detail."""
        return reverse_lazy("chatbots:detail", kwargs={"pk": self.object.pk})

    def get_queryset(self):
        """Filter by current user."""
        return Chatbot.objects.filter(owner=self.request.user, is_deleted=False)

    def form_valid(self, form):
        """Add success message."""
        response = super().form_valid(form)
        messages.success(self.request, f"Chatbot '{self.object.name}' updated successfully.")
        return response


class ChatbotDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a chatbot.
    """

    model = Chatbot
    template_name = "chatbots/chatbot_confirm_delete.html"
    success_url = reverse_lazy("chatbots:list")
    context_object_name = "chatbot"

    def get_queryset(self):
        """Filter by current user."""
        return Chatbot.objects.filter(owner=self.request.user, is_deleted=False)

    def form_valid(self, form):
        """Soft delete the chatbot."""
        chatbot = self.get_object()
        ChatbotService.delete_chatbot(chatbot)
        messages.success(self.request, f"Chatbot '{chatbot.name}' deleted successfully.")
        return redirect(self.success_url)


class ChatbotToggleView(LoginRequiredMixin, View):
    """
    Toggle chatbot active status.
    """

    def post(self, request: HttpRequest, pk: str, *args, **kwargs) -> HttpResponse:
        """Toggle the chatbot's active status."""
        chatbot = get_object_or_404(
            Chatbot,
            id=pk,
            owner=request.user,
            is_deleted=False,
        )

        if chatbot.is_active:
            ChatbotService.deactivate_chatbot(chatbot)
            messages.success(request, f"Chatbot '{chatbot.name}' deactivated.")
        else:
            ChatbotService.activate_chatbot(chatbot)
            messages.success(request, f"Chatbot '{chatbot.name}' activated.")

        return redirect("chatbots:detail", pk=pk)
