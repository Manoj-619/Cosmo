# NOTE: This will automatically create all the stage models for the user when a new user is created.

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage


logger = logging.getLogger(__name__)

@receiver(post_save, sender=Profile)
def create_stage_models(sender, instance, created, **kwargs):
    if created:
        ProfileStage.objects.create(user=instance.user)
        DiscoverStage.objects.create(user=instance.user)
        DiscussStage.objects.create(user=instance.user)
        DeliverStage.objects.create(user=instance.user)
        DemonstrateStage.objects.create(user=instance.user)
        logger.info(f"Stage models created for user {instance.user.username}")