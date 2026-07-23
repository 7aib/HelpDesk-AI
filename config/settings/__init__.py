"""
Settings module for HelpDesk-AI project.
"""

import os

# Get the environment from DJANGO_ENV or default to development
DJANGO_ENV = os.getenv("DJANGO_ENV", "development")

if DJANGO_ENV == "production":
    from .production import *  # noqa: F401, F403
elif DJANGO_ENV == "development":
    from .development import *  # noqa: F401, F403
else:
    from .base import *  # noqa: F401, F403
