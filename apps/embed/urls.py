from django.urls import path

from . import views

app_name = "embed"

urlpatterns = [
    path(
        "widget.js",
        views.WidgetLoaderView.as_view(),
        name="widget-loader",
    ),
    path(
        "test/",
        views.EmbedTestView.as_view(),
        name="test",
    ),
    path(
        "<uuid:pk>/",
        views.EmbedWidgetView.as_view(),
        name="widget",
    ),
    path(
        "<uuid:pk>/send/",
        views.EmbedSendView.as_view(),
        name="send",
    ),
]
