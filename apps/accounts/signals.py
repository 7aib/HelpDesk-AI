"""
Signals for HelpDesk-AI accounts app.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def user_post_save(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    Handle post-save signals for User model.
    
    Creates initial settings or performs other actions after user creation.
    """
    if created:
        logger.info(f"New user created: {instance.username}")
        
        # Send welcome email (if configured)
        # TODO: Implement welcome email
        
        # Create default chatbot settings
        # This will be implemented when the chatbots app is created
