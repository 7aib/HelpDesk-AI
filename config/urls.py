"""
URL configuration for HelpDesk-AI project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Authentication
    path("accounts/", include("allauth.urls")),
    # Core apps
    path("", include("apps.accounts.urls")),
    path("chatbots/", include("apps.chatbots.urls")),
    path("knowledge/", include("apps.knowledge.urls")),
    path("documents/", include("apps.documents.urls")),
    path("chat/", include("apps.chat.urls")),
    # API
    path("api/v1/", include("apps.api.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Debug toolbar
if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
