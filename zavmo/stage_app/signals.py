# NOTE: This will automatically create all the stage models for the user when a new user is created.

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from .models import Profile, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage

User = get_user_model()


logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        ProfileStage.objects.create(user=instance)
        DiscoverStage.objects.create(user=instance)
        DiscussStage.objects.create(user=instance)
        DeliverStage.objects.create(user=instance)
        DemonstrateStage.objects.create(user=instance)
        logger.info(f"Profile created for user {instance.username}")
    else:
        logger.info(f"Profile updated for user {instance.username}")