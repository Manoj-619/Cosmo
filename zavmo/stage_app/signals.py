# NOTE: This will automatically create all the stage models for the user when a new user is created.

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FourDSequence, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage

logger = logging.getLogger(__name__)

@receiver(post_save, sender=FourDSequence)
def create_stage_models(sender, instance, created, **kwargs):
    if created:
        DiscoverStage.objects.create(sequence=instance)
        DiscussStage.objects.create(sequence=instance)
        DeliverStage.objects.create(sequence=instance)
        DemonstrateStage.objects.create(sequence=instance)
        logger.info(f"4d sequence created for user {instance.user.username}")