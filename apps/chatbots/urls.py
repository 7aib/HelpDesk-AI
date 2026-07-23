"""
URL configuration for HelpDesk-AI chatbots app.
"""

from django.urls import path

from . import views

app_name = "chatbots"

urlpatterns = [
    # Chatbot CRUD
    path("", views.ChatbotListView.as_view(), name="list"),
    path("create/", views.ChatbotCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.ChatbotDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.ChatbotUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.ChatbotDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/toggle/", views.ChatbotToggleView.as_view(), name="toggle"),
]
