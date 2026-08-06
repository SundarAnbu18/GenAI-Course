"""URLs for the chatbot app."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat, name="chat"),
    path("api/ask/", views.ask_api, name="ask_api"),
    path("api/health/", views.health, name="health"),
]
