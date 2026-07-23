"""
Views for HelpDesk-AI documents app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView

from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeBase

from .models import Document
from .tasks import process_document_task


class DocumentListView(LoginRequiredMixin, ListView):
    """
    List documents for a knowledge base.
    """

    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"
    paginate_by = 20

    def get_queryset(self):
        """Filter by knowledge base."""
        self.knowledge_base = get_object_or_404(
            KnowledgeBase,
            id=self.kwargs["kb_id"],
            chatbot__owner=self.request.user,
        )
        return Document.objects.filter(
            knowledge_base=self.knowledge_base,
            is_deleted=False,
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        """Add knowledge base to context."""
        context = super().get_context_data(**kwargs)
        context["knowledge_base"] = self.knowledge_base
        context["chatbot"] = self.knowledge_base.chatbot
        return context


class DocumentUploadView(LoginRequiredMixin, CreateView):
    """
    Upload a document to a knowledge base.
    """

    model = Document
    template_name = "documents/document_upload.html"
    fields = ["title", "file"]

    def form_valid(self, form):
        """Set knowledge base and trigger processing."""
        knowledge_base = get_object_or_404(
            KnowledgeBase,
            id=self.kwargs["kb_id"],
            chatbot__owner=self.request.user,
        )
        
        form.instance.knowledge_base = knowledge_base
        
        # Determine document type from file extension
        file = form.cleaned_data["file"]
        ext = file.name.split(".")[-1].lower()
        
        type_map = {
            "pdf": "pdf",
            "docx": "docx",
            "doc": "docx",
            "txt": "txt",
            "md": "md",
            "markdown": "md",
        }
        
        form.instance.document_type = type_map.get(ext, "txt")
        form.instance.file_size = file.size
        
        response = super().form_valid(form)
        
        # Trigger async processing
        process_document_task.delay(str(self.object.id))
        
        messages.success(
            self.request,
            f"Document '{self.object.title}' uploaded and processing started.",
        )
        
        return response

    def get_success_url(self):
        """Redirect to document list."""
        return reverse_lazy(
            "documents:list",
            kwargs={"kb_id": self.kwargs["kb_id"]},
        )


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a document.
    """

    model = Document
    template_name = "documents/document_confirm_delete.html"
    context_object_name = "document"

    def get_queryset(self):
        """Filter by user's chatbots."""
        return Document.objects.filter(
            knowledge_base__chatbot__owner=self.request.user,
            is_deleted=False,
        )

    def form_valid(self, form):
        """Soft delete the document."""
        document = self.get_object()
        document.soft_delete()
        
        # Update knowledge base stats
        document.knowledge_base.update_stats()
        
        messages.success(self.request, f"Document '{document.title}' deleted.")
        return redirect(
            reverse_lazy("documents:list", kwargs={"kb_id": self.kwargs["kb_id"]})
        )


class DocumentDetailView(LoginRequiredMixin, TemplateView):
    """
    View document details and chunks.
    """

    template_name = "documents/document_detail.html"

    def get_context_data(self, **kwargs):
        """Add document to context."""
        context = super().get_context_data(**kwargs)
        document = get_object_or_404(
            Document,
            id=self.kwargs["pk"],
            knowledge_base__chatbot__owner=self.request.user,
            is_deleted=False,
        )
        context["document"] = document
        context["chunks"] = document.chunks.all()[:20]
        return context
