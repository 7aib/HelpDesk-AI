"""
Views for HelpDesk-AI chat app.
"""

import json
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
        context["conversation"] = get_object_or_404(
            Conversation,
            id=self.kwargs["conversation_id"],
            chatbot__owner=self.request.user,
        )
        context["messages"] = context["conversation"].messages.all()
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
        return render(
            request,
            "chat/partials/message.html",
            {
                "message": assistant_message,
                "conversation": conversation,
            },
        )


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
        Message.objects.create(
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
            def error_stream():
                yield f"data: {json.dumps({'token': assistant_message.content})}\n\n"
                yield f"data: {json.dumps({'done': True, 'conversation_id': str(conversation.id)})}\n\n"

            response = StreamingHttpResponse(error_stream(), content_type="text/event-stream")
            response["Cache-Control"] = "no-cache"
            return response

        def generate():
            """Generate streaming response."""
            from apps.rag.services import EmbeddingService, VectorSearchService

            # Get similar chunks
            embedding_service = EmbeddingService()
            search_service = VectorSearchService()

            question_embedding = embedding_service.generate_embedding(
                message_content,
                model_name=chatbot.embedding_model,
            )

            similar_chunks = search_service.search_similar_chunks(
                query_embedding=question_embedding,
                chatbot_id=str(chatbot.id),
                top_k=chatbot.top_k,
            )

            # Build context
            rag = RAGPipeline()
            context = rag._build_context(similar_chunks, [])

            # Build prompt
            prompt = rag._build_prompt(
                question=message_content,
                context=context,
                conversation_history=conversation_history,
            )

            # Stream response from Ollama
            ollama = OllamaService()
            full_response = []

            try:
                url = f"{ollama.base_url}/api/generate"
                payload = {
                    "model": chatbot.llm_model,
                    "prompt": prompt,
                    "system": chatbot.system_prompt,
                    "stream": True,
                    "options": {
                        "temperature": chatbot.temperature,
                        "top_p": chatbot.top_p,
                    },
                }

                import requests
                response = requests.post(url, json=payload, stream=True, timeout=120)

                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            token = chunk["response"]
                            full_response.append(token)
                            yield f"data: {json.dumps({'token': token})}\n\n"

                # Save complete response
                complete_response = "".join(full_response)
                Message.objects.create(
                    conversation=conversation,
                    role=Message.Role.ASSISTANT,
                    content=complete_response,
                    metadata={
                        "sources": [{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in s.items()} for s in similar_chunks],
                        "model_used": chatbot.llm_model,
                    },
                )

                # Send completion event
                yield f"data: {json.dumps({'done': True, 'conversation_id': str(conversation.id)})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        response = StreamingHttpResponse(
            generate(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response
