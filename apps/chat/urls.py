"""
URL configuration for HelpDesk-AI chat app.
"""

from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    # Chat interface
    path("<uuid:chatbot_id>/", views.ChatView.as_view(), name="chat"),
    # Conversation
    path(
        "conversation/<uuid:conversation_id>/",
        views.ConversationView.as_view(),
        name="conversation",
    ),
    path(
        "conversation/<uuid:pk>/delete/",
        views.ConversationDeleteView.as_view(),
        name="conversation-delete",
    ),
    path(
        "conversation/<uuid:pk>/rename/",
        views.ConversationRenameView.as_view(),
        name="conversation-rename",
    ),
    # Messages
    path(
        "<uuid:chatbot_id>/send/",
        views.Send_messageView.as_view(),
        name="send-message",
    ),
    # Streaming
    path(
        "<uuid:chatbot_id>/stream/",
        views.ChatStreamView.as_view(),
        name="stream",
    ),
]
