"""Root URL configuration — everything is delegated to the chatbot app."""

from django.urls import include, path

urlpatterns = [
    path("", include("chatbot.urls")),
]
