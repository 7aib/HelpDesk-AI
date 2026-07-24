"""
Celery configuration for HelpDesk-AI.
"""

import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Create the Celery app
app = Celery("helpdesk")

# Read config from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
