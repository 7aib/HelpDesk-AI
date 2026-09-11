"""
Lower default temperature/top_p to reduce hallucination in RAG answers.

Existing chatbots still using the old defaults (0.7/0.9) are also updated.
"""

from django.db import migrations, models


def update_existing_chatbot_defaults(apps, schema_editor):
    Chatbot = apps.get_model("chatbots", "Chatbot")
    Chatbot.objects.filter(
        temperature__gte=0.69,
        temperature__lte=0.71,
    ).update(temperature=0.2)
    Chatbot.objects.filter(
        top_p__gte=0.89,
        top_p__lte=0.91,
    ).update(top_p=0.5)


def reverse(apps, schema_editor):
    Chatbot = apps.get_model("chatbots", "Chatbot")
    Chatbot.objects.filter(
        temperature__gte=0.19,
        temperature__lte=0.21,
    ).update(temperature=0.7)
    Chatbot.objects.filter(
        top_p__gte=0.49,
        top_p__lte=0.51,
    ).update(top_p=0.9)


class Migration(migrations.Migration):

    dependencies = [
        ("chatbots", "0003_chatbot_ui_customization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatbot",
            name="temperature",
            field=models.FloatField(
                default=0.2,
                help_text="Temperature for LLM generation (0.0 to 2.0).",
            ),
        ),
        migrations.AlterField(
            model_name="chatbot",
            name="top_p",
            field=models.FloatField(
                default=0.5,
                help_text="Top P for LLM generation (0.0 to 1.0).",
            ),
        ),
        migrations.RunPython(update_existing_chatbot_defaults, reverse),
    ]
