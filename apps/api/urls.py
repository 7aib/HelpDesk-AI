"""
URL configuration for HelpDesk-AI API app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register(r"chatbots", views.ChatbotViewSet, basename="chatbot")
router.register(r"documents", views.DocumentViewSet, basename="document")
router.register(r"knowledge-bases", views.KnowledgeBaseViewSet, basename="knowledge-base")
router.register(r"conversations", views.ConversationViewSet, basename="conversation")

urlpatterns = [
    # Authentication
    path("auth/register/", views.RegisterAPIView.as_view(), name="register"),
    path("auth/login/", views.LoginAPIView.as_view(), name="login"),
    path("auth/logout/", views.LogoutAPIView.as_view(), name="logout"),
    path("auth/profile/", views.ProfileAPIView.as_view(), name="profile"),
    path("auth/change-password/", views.ChangePasswordAPIView.as_view(), name="change-password"),
    # Chat
    path("chat/", views.ChatAPIView.as_view(), name="chat"),
    # Health check
    path("health/", views.HealthCheckAPIView.as_view(), name="health"),
    # Router URLs
    path("", include(router.urls)),
]
