"""
Views for HelpDesk-AI chat app.
"""

import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DeleteView, ListView, TemplateView

from apps.chatbots.models import Chatbot

from .models import Conversation, Message


class ChatView(LoginRequiredMixin, TemplateView):
    """
    Main chat interface view.
    """

    template_name = "chat/chat.html"

    def get_context_data(self, **kwargs):
        """Add chatbot and conversations to context."""
        context = super().get_context_data(**kwargs)
        context["chatbot"] = get_object_or_404(
            Chatbot,
            id=self.kwargs["chatbot_id"],
            owner=self.request.user,
        )
        context["conversations"] = Conversation.objects.filter(
            chatbot=context["chatbot"],
            user=self.request.user,
        ).order_by("-last_message_at")[:20]
        context["knowledge_base"] = context["chatbot"].knowledge_base
        kb = context["knowledge_base"]
        has_docs = kb is not None and kb.total_documents > 0
        has_qa = kb is not None and kb.qa_pairs.filter(is_active=True).exists()
        context["has_documents"] = has_docs or has_qa
        return context


class ConversationView(LoginRequiredMixin, TemplateView):
    """
    View a specific conversation.
    """

    template_name = "chat/conversation.html"

    def get_context_data(self, **kwargs):
        """Add conversation and messages to context."""
        context = super().get_context_data(**kwargs)
        conversation = get_object_or_404(
            Conversation,
            id=self.kwargs["conversation_id"],
            chatbot__owner=self.request.user,
        )
        context["conversation"] = conversation
        context["messages"] = conversation.messages.all()
        context["conversations"] = Conversation.objects.filter(
            chatbot=conversation.chatbot,
            user=self.request.user,
        ).order_by("-last_message_at")[:20]
        kb = conversation.chatbot.knowledge_base
        has_docs = kb is not None and kb.total_documents > 0
        has_qa = kb is not None and kb.qa_pairs.filter(is_active=True).exists()
        context["has_documents"] = has_docs or has_qa
        return context


class ConversationDeleteView(LoginRequiredMixin, View):
    """
    Delete a conversation via POST.
    """

    def post(self, request: HttpRequest, pk: str) -> HttpResponse:
        conversation = get_object_or_404(
            Conversation,
            id=pk,
            chatbot__owner=request.user,
        )
        chatbot_id = conversation.chatbot.id
        conversation.delete()
        return redirect(f"/chat/{chatbot_id}/")


class Send_messageView(LoginRequiredMixin, View):
    """
    View for sending messages via HTMX.
    """

    def post(self, request: HttpRequest, chatbot_id: str) -> HttpResponse:
        """Handle message sending."""
        from apps.rag.services import RAGPipeline

        chatbot = get_object_or_404(
            Chatbot,
            id=chatbot_id,
            owner=request.user,
        )

        message_content = request.POST.get("message", "").strip()
        conversation_id = request.POST.get("conversation_id")

        if not message_content:
            return HttpResponse("Message cannot be empty", status=400)

        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                id=conversation_id,
                chatbot=chatbot,
            )
        else:
            conversation = Conversation.objects.create(
                chatbot=chatbot,
                user=request.user,
                title=message_content[:50],
                session_id=str(uuid.uuid4()),
            )

        # Create user message
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=message_content,
        )

        # Get conversation history (exclude the message we just created)
        conversation_history = list(
            conversation.messages.order_by("created_at")
            .exclude(pk=user_message.pk)
            .values("role", "content")
        )

        # Check if chatbot has documents or QA pairs in its knowledge base
        kb = chatbot.knowledge_base
        has_content = kb and (kb.total_documents > 0 or kb.qa_pairs.filter(is_active=True).exists())
        if not has_content:
            assistant_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content="This chatbot does not have any documents or Q&A pairs in its knowledge base. Please add content before chatting.",
            )
            return render(
                request,
                "chat/partials/message.html",
                {"message": assistant_message, "conversation": conversation},
            )

        # Generate response
        rag_pipeline = RAGPipeline()
        result = rag_pipeline.answer_question(
            question=message_content,
            chatbot=chatbot,
            conversation_history=conversation_history,
        )

        # Create assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=result["answer"],
            metadata={
                "sources": [{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in s.items()} for s in result["sources"]],
                "model_used": result["model_used"],
            },
        )

        # Update chatbot usage
        chatbot.update_usage_stats()

        # Return response for HTMX
        response = render(
            request,
            "chat/partials/message.html",
            {
                "message": assistant_message,
                "conversation": conversation,
            },
        )
        response["X-Conversation-ID"] = str(conversation.id)
        return response


class ConversationRenameView(LoginRequiredMixin, View):
    """
    Rename a conversation via HTMX.
    """

    def post(self, request: HttpRequest, pk: str) -> HttpResponse:
        """Rename the conversation."""
        conversation = get_object_or_404(
            Conversation,
            id=pk,
            chatbot__owner=request.user,
        )

        new_title = request.POST.get("title", "").strip()
        if new_title:
            conversation.title = new_title
            conversation.save(update_fields=["title", "updated_at"])

        return HttpResponse(f'<span class="conversation-title">{conversation.title}</span>')


class ChatStreamView(LoginRequiredMixin, View):
    """
    Streaming chat response using Server-Sent Events.
    """

    def post(self, request: HttpRequest, chatbot_id: str) -> HttpResponse:
        """Handle streaming message sending."""
        import queue
        import threading

        from apps.rag.services import OllamaService, RAGPipeline

        chatbot = get_object_or_404(
            Chatbot,
            id=chatbot_id,
            owner=request.user,
        )

        message_content = request.POST.get("message", "").strip()
        conversation_id = request.POST.get("conversation_id")

        if not message_content:
            return HttpResponse("Message cannot be empty", status=400)

        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                id=conversation_id,
                chatbot=chatbot,
            )
        else:
            conversation = Conversation.objects.create(
                chatbot=chatbot,
                user=request.user,
                title=message_content[:50],
                session_id=str(uuid.uuid4()),
            )

        # Create user message
        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=message_content,
        )

        # Get conversation history (exclude the message we just created)
        conversation_history = list(
            conversation.messages.order_by("created_at")
            .exclude(pk=user_message.pk)
            .values("role", "content")
        )

        from apps.rag.services import stream_chat_response

        response = StreamingHttpResponse(
            stream_chat_response(
                conversation=conversation,
                chatbot=chatbot,
                message_content=message_content,
                conversation_history=conversation_history,
            ),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["X-Conversation-ID"] = str(conversation.id)

        return response
