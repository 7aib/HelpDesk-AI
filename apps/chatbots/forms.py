"""
Forms for HelpDesk-AI chatbots app.
"""

import logging

from django import forms

from .models import Chatbot

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_CHOICES = [
    ("BAAI/bge-small-en-v1.5", "BAAI/bge-small-en-v1.5"),
    ("BAAI/bge-base-en-v1.5", "BAAI/bge-base-en-v1.5"),
    ("all-MiniLM-L6-v2", "all-MiniLM-L6-v2"),
    ("all-mpnet-base-v2", "all-mpnet-base-v2"),
]


def get_ollama_model_choices():
    """Fetch available models from Ollama API."""
    try:
        import requests

        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        response.raise_for_status()
        models = response.json().get("models", [])
        if models:
            return [(m["name"], m["name"]) for m in models]
    except Exception as e:
        logger.warning(f"Could not fetch Ollama models: {e}")

    return [("llama3.2", "llama3.2 (default)")]


class ChatbotForm(forms.ModelForm):
    """Form for creating and updating chatbots with dynamic model choices."""

    class Meta:
        model = Chatbot
        fields = [
            "name",
            "description",
            "system_prompt",
            "temperature",
            "top_p",
            "max_context_length",
            "embedding_model",
            "llm_model",
            "top_k",
            "chunk_size",
            "chunk_overlap",
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        llm_choices = get_ollama_model_choices()
        self.fields["llm_model"].choices = llm_choices
        self.fields["llm_model"].widget = forms.Select(choices=llm_choices)

        embed_choices = EMBEDDING_MODEL_CHOICES
        self.fields["embedding_model"].choices = embed_choices
        self.fields["embedding_model"].widget = forms.Select(choices=embed_choices)

        self.fields["status"].choices = Chatbot.Status.choices
        self.fields["status"].widget = forms.Select(choices=Chatbot.Status.choices)
