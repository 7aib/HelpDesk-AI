"""
URL configuration for HelpDesk-AI documents app.
"""

from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    # Document CRUD
    path(
        "knowledge-base/<uuid:kb_id>/",
        views.DocumentListView.as_view(),
        name="list",
    ),
    path(
        "knowledge-base/<uuid:kb_id>/upload/",
        views.DocumentUploadView.as_view(),
        name="upload",
    ),
    path("<uuid:pk>/", views.DocumentDetailView.as_view(), name="detail"),
    path(
        "<uuid:pk>/delete/<uuid:kb_id>/",
        views.DocumentDeleteView.as_view(),
        name="delete",
    ),
]
