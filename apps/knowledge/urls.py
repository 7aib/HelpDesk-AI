"""
URL configuration for HelpDesk-AI knowledge app.
"""

from django.urls import path

from . import views

app_name = "knowledge"

urlpatterns = [
    # Knowledge Base
    path("<uuid:pk>/", views.KnowledgeBaseDetailView.as_view(), name="detail"),
    # Q&A Pairs
    path(
        "<uuid:kb_id>/qa/",
        views.QAPairListView.as_view(),
        name="qa_list",
    ),
    path(
        "<uuid:kb_id>/qa/create/",
        views.QAPairCreateView.as_view(),
        name="qa_create",
    ),
    path(
        "qa/<uuid:pk>/edit/",
        views.QAPairUpdateView.as_view(),
        name="qa_update",
    ),
    path(
        "qa/<uuid:pk>/delete/",
        views.QAPairDeleteView.as_view(),
        name="qa_delete",
    ),
]
