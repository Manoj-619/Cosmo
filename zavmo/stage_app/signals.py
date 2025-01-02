# NOTE: This will automatically create all the stage models for the user when a new user is created.

import logging
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from .models import FourDSequence, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, TNAassessment
import json

logger = logging.getLogger(__name__)

@receiver(post_save, sender=FourDSequence)
def create_stage_models(sender, instance, created, **kwargs):
    """Create the 4D stage models when a new sequence is created."""
    DiscoverStage.objects.create(user=instance.user, sequence=instance)
    DiscussStage.objects.create(user=instance.user, sequence=instance)
    DeliverStage.objects.create(user=instance.user, sequence=instance)
    DemonstrateStage.objects.create(user=instance.user, sequence=instance)
    logger.info(f"4d sequence created for user {instance.user.username}")