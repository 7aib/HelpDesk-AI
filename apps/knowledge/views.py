"""
Views for HelpDesk-AI knowledge app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .models import KnowledgeBase, QAPair


class KnowledgeBaseDetailView(LoginRequiredMixin, TemplateView):
    """
    View knowledge base details with QA pairs.
    """

    template_name = "knowledge/knowledge_base_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["knowledge_base"] = get_object_or_404(
            KnowledgeBase,
            id=self.kwargs["pk"],
            chatbot__owner=self.request.user,
        )
        kb = context["knowledge_base"]
        context["qa_pairs"] = kb.qa_pairs.filter(is_active=True).order_by("-created_at")[:20]
        context["total_qa_pairs"] = kb.qa_pairs.filter(is_active=True).count()
        context["chatbot"] = kb.chatbot
        context["documents"] = kb.documents.filter(is_deleted=False).order_by("-created_at")[:10]
        return context


class KnowledgeBaseUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edit knowledge base name and description.
    """

    model = KnowledgeBase
    template_name = "knowledge/knowledge_base_edit.html"
    fields = ["name", "description"]

    def get_queryset(self):
        return KnowledgeBase.objects.filter(
            chatbot__owner=self.request.user,
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Knowledge base updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("knowledge:detail", kwargs={"pk": self.object.pk})


class QAPairListView(LoginRequiredMixin, ListView):
    """
    List Q&A pairs for a knowledge base.
    """

    model = QAPair
    template_name = "knowledge/qa_pair_list.html"
    context_object_name = "qa_pairs"
    paginate_by = 20

    def get_queryset(self):
        self.knowledge_base = get_object_or_404(
            KnowledgeBase,
            id=self.kwargs["kb_id"],
            chatbot__owner=self.request.user,
        )
        return QAPair.objects.filter(
            knowledge_base=self.knowledge_base,
            is_active=True,
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["knowledge_base"] = self.knowledge_base
        context["chatbot"] = self.knowledge_base.chatbot
        return context


class QAPairCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new Q&A pair.
    """

    model = QAPair
    template_name = "knowledge/qa_pair_form.html"
    fields = ["question", "answer", "category"]

    def form_valid(self, form):
        knowledge_base = get_object_or_404(
            KnowledgeBase,
            id=self.kwargs["kb_id"],
            chatbot__owner=self.request.user,
        )
        form.instance.knowledge_base = knowledge_base
        response = super().form_valid(form)

        from apps.rag.services import EmbeddingService
        embedding_service = EmbeddingService()
        try:
            embedding = embedding_service.generate_embedding(
                form.instance.question,
                model_name=knowledge_base.chatbot.embedding_model,
            )
            form.instance.embedding = embedding
            form.instance.save(update_fields=["embedding"])
        except Exception as e:
            messages.warning(
                self.request,
                f"Q&A pair created but embedding generation failed: {e}",
            )

        messages.success(self.request, "Q&A pair created successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy(
            "knowledge:qa_list",
            kwargs={"kb_id": self.kwargs["kb_id"]},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["knowledge_base"] = get_object_or_404(
            KnowledgeBase,
            id=self.kwargs["kb_id"],
            chatbot__owner=self.request.user,
        )
        return context


class QAPairUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update a Q&A pair.
    """

    model = QAPair
    template_name = "knowledge/qa_pair_form.html"
    fields = ["question", "answer", "category", "is_active"]

    def get_queryset(self):
        return QAPair.objects.filter(
            knowledge_base__chatbot__owner=self.request.user,
        )

    def form_valid(self, form):
        if "question" in form.changed_fields:
            from apps.rag.services import EmbeddingService
            embedding_service = EmbeddingService()
            try:
                embedding = embedding_service.generate_embedding(
                    form.instance.question,
                    model_name=form.instance.knowledge_base.chatbot.embedding_model,
                )
                form.instance.embedding = embedding
            except Exception as e:
                messages.warning(
                    self.request,
                    f"Q&A pair updated but embedding regeneration failed: {e}",
                )

        response = super().form_valid(form)
        messages.success(self.request, "Q&A pair updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy(
            "knowledge:qa_list",
            kwargs={"kb_id": self.object.knowledge_base.id},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["knowledge_base"] = self.object.knowledge_base
        return context


class QAPairDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a Q&A pair.
    """

    model = QAPair
    template_name = "knowledge/qa_pair_confirm_delete.html"
    context_object_name = "qa_pair"

    def get_queryset(self):
        return QAPair.objects.filter(
            knowledge_base__chatbot__owner=self.request.user,
        )

    def form_valid(self, form):
        qa_pair = self.get_object()
        kb_id = qa_pair.knowledge_base.id
        qa_pair.delete()
        messages.success(self.request, "Q&A pair deleted successfully.")
        return redirect(
            reverse_lazy("knowledge:qa_list", kwargs={"kb_id": kb_id})
        )
