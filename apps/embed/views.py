"""
Public embed views for HelpDesk-AI chatbot widget.
"""

import json
import uuid

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.chatbots.models import Chatbot

from apps.chat.models import Conversation, Message


class EmbedWidgetView(View):
    """
    Serves the standalone chat widget UI inside an iframe.
    No login required. Identified by chatbot slug.
    """

    @method_decorator(xframe_options_exempt)
    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        chatbot = get_object_or_404(
            Chatbot,
            slug=slug,
            status=Chatbot.Status.ACTIVE,
            allow_embed=True,
        )

        kb = chatbot.knowledge_base
        has_content = kb and (
            kb.total_documents > 0
            or kb.qa_pairs.filter(is_active=True).exists()
        )

        # Get or create conversation via cookie
        cookie_name = f"embed_{chatbot.slug}"
        session_id = request.COOKIES.get(cookie_name)

        conversation = None
        messages = []
        if session_id:
            conversation = (
                Conversation.objects.filter(session_id=session_id, chatbot=chatbot)
                .first()
            )
            if conversation:
                messages = list(conversation.messages.all())

        if not conversation:
            conversation = Conversation.objects.create(
                chatbot=chatbot,
                user=None,
                title="Embed Chat",
                session_id=str(uuid.uuid4()),
            )

        context = {
            "chatbot": chatbot,
            "conversation": conversation,
            "messages": messages,
            "has_content": has_content,
        }

        response = render(request, "embed/widget.html", context)
        response.set_cookie(
            cookie_name,
            str(conversation.session_id),
            max_age=60 * 60 * 24 * 30,
            samesite="Lax",
        )
        return response


@method_decorator([csrf_exempt, xframe_options_exempt], name="dispatch")
class EmbedSendView(View):
    """
    Public API endpoint for sending messages from the embed widget.
    No login required. Uses chatbot slug for identification.
    """

    def post(self, request: HttpRequest, slug: str) -> JsonResponse:
        chatbot = get_object_or_404(
            Chatbot,
            slug=slug,
            status=Chatbot.Status.ACTIVE,
            allow_embed=True,
        )

        message_content = request.POST.get("message", "").strip()
        conversation_id = request.POST.get("conversation_id")

        if not message_content:
            return JsonResponse({"error": "Message cannot be empty"}, status=400)

        # Get conversation
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                id=conversation_id,
                chatbot=chatbot,
            )
        else:
            conversation = Conversation.objects.create(
                chatbot=chatbot,
                user=None,
                title=message_content[:50],
                session_id=str(uuid.uuid4()),
            )

        # Create user message
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=message_content,
        )

        # Get conversation history
        conversation_history = list(
            conversation.messages.order_by("created_at")
            .values("role", "content")
        )

        # Check for content
        kb = chatbot.knowledge_base
        has_content = kb and (
            kb.total_documents > 0
            or kb.qa_pairs.filter(is_active=True).exists()
        )

        if not has_content:
            assistant_content = (
                "This chatbot does not have any knowledge base content yet. "
                "Please ask the administrator to add documents or Q&A pairs."
            )
        else:
            from apps.rag.services import RAGPipeline

            rag_pipeline = RAGPipeline()
            result = rag_pipeline.answer_question(
                question=message_content,
                chatbot=chatbot,
                conversation_history=conversation_history,
            )
            assistant_content = result["answer"]

        # Create assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=assistant_content,
            metadata={
                "model_used": chatbot.llm_model,
            },
        )

        # Update stats
        conversation.message_count = conversation.messages.count()
        conversation.last_message_at = assistant_message.created_at
        conversation.save(update_fields=["message_count", "last_message_at"])
        chatbot.update_usage_stats()

        return JsonResponse({
            "answer": assistant_content,
            "conversation_id": str(conversation.id),
        })


class WidgetLoaderView(View):
    """
    Serves the widget loader JS snippet.
    GET /embed/widget.js?chatbot=<slug>&position=bottom-right
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        slug = request.GET.get("chatbot", "")
        position = request.GET.get("position", "bottom-right")

        parts = position.split("-")
        vertical = parts[0] if len(parts) > 0 else "bottom"
        horizontal = parts[1] if len(parts) > 1 else "right"

        js = (
            "(function() {\n"
            "    var SLUG = '" + slug + "';\n"
            "    var VERT = '" + vertical + "';\n"
            "    var HORIZ = '" + horizontal + "';\n"
            "    var BASE = window.location.origin;\n"
            "    var WIDGET_URL = BASE + '/embed/' + SLUG + '/';\n"
            "\n"
            "    if (!SLUG) return;\n"
            "\n"
            "    var style = document.createElement('style');\n"
            "    style.textContent = [\n"
            "        '#helpdesk-widget-btn {',\n"
            "            'position: fixed;',\n"
            "            VERT + ': 20px;',\n"
            "            HORIZ + ': 20px;',\n"
            "            'width: 60px;',\n"
            "            'height: 60px;',\n"
            "            'border-radius: 50%;',\n"
            "            'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);',\n"
            "            'color: white;',\n"
            "            'border: none;',\n"
            "            'cursor: pointer;',\n"
            "            'box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);',\n"
            "            'z-index: 99999;',\n"
            "            'display: flex;',\n"
            "            'align-items: center;',\n"
            "            'justify-content: center;',\n"
            "            'font-size: 24px;',\n"
            "            'transition: transform 0.2s, box-shadow 0.2s;',\n"
            "        '}',\n"
            "        '#helpdesk-widget-btn:hover {',\n"
            "            'transform: scale(1.1);',\n"
            "            'box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);',\n"
            "        '}',\n"
            "        '#helpdesk-widget-frame {',\n"
            "            'position: fixed;',\n"
            "            VERT + ': 90px;',\n"
            "            HORIZ + ': 20px;',\n"
            "            'width: 400px;',\n"
            "            'height: 600px;',\n"
            "            'max-height: calc(100vh - 120px);',\n"
            "            'border: none;',\n"
            "            'border-radius: 16px;',\n"
            "            'box-shadow: 0 10px 40px rgba(0,0,0,0.15);',\n"
            "            'z-index: 99998;',\n"
            "            'display: none;',\n"
            "            'overflow: hidden;',\n"
            "        '}',\n"
            "        '#helpdesk-widget-frame.open {',\n"
            "            'display: block;',\n"
            "            'animation: helpdeskSlideUp 0.3s ease;',\n"
            "        '}',\n"
            "        '@keyframes helpdeskSlideUp {',\n"
            "            'from { opacity: 0; transform: translateY(20px); }',\n"
            "            'to { opacity: 1; transform: translateY(0); }',\n"
            "        '}',\n"
            "    ].join('\\n');\n"
            "    document.head.appendChild(style);\n"
            "\n"
            "    var chatIcon = '<svg width=\"28\" height=\"28\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z\"></path></svg>';\n"
            "    var closeIcon = '<svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><line x1=\"18\" y1=\"6\" x2=\"6\" y2=\"18\"></line><line x1=\"6\" y1=\"6\" x2=\"18\" y2=\"18\"></line></svg>';\n"
            "\n"
            "    var btn = document.createElement('button');\n"
            "    btn.id = 'helpdesk-widget-btn';\n"
            "    btn.innerHTML = chatIcon;\n"
            "\n"
            "    var iframe = document.createElement('iframe');\n"
            "    iframe.id = 'helpdesk-widget-frame';\n"
            "    iframe.src = WIDGET_URL;\n"
            "\n"
            "    var open = false;\n"
            "    btn.onclick = function() {\n"
            "        open = !open;\n"
            "        if (open) {\n"
            "            iframe.classList.add('open');\n"
            "            btn.innerHTML = closeIcon;\n"
            "        } else {\n"
            "            iframe.classList.remove('open');\n"
            "            btn.innerHTML = chatIcon;\n"
            "        }\n"
            "    };\n"
            "\n"
            "    document.body.appendChild(btn);\n"
            "    document.body.appendChild(iframe);\n"
            "})();\n"
        )
        return HttpResponse(js, content_type="application/javascript")
