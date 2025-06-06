# NOTE: This will automatically create all the stage models for the user when a new user is created.

import logging
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.db import IntegrityError
from .models import FourDSequence, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, TNAassessment

logger = logging.getLogger(__name__)

@receiver(post_save, sender=FourDSequence)
def create_stage_models(sender, instance, created, **kwargs):
    """Create the 4D stage models when a new sequence is created."""
    if created:  # Only create stages for new sequences
        try:
            # Check each stage individually and create if missing
            if not DiscoverStage.objects.filter(sequence=instance).exists():
                DiscoverStage.objects.create(user=instance.user, sequence=instance)
                logger.info(f"DiscoverStage created for sequence {instance.id}")
            
            if not DiscussStage.objects.filter(sequence=instance).exists():
                DiscussStage.objects.create(user=instance.user, sequence=instance)
                logger.info(f"DiscussStage created for sequence {instance.id}")
            
            if not DeliverStage.objects.filter(sequence=instance).exists():
                DeliverStage.objects.create(user=instance.user, sequence=instance)
                logger.info(f"DeliverStage created for sequence {instance.id}")
            
            if not DemonstrateStage.objects.filter(sequence=instance).exists():
                DemonstrateStage.objects.create(user=instance.user, sequence=instance)
                logger.info(f"DemonstrateStage created for sequence {instance.id}")
            
        except IntegrityError as e:
            logger.error(f"IntegrityError creating stages for sequence {instance.id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating stages for sequence {instance.id}: {str(e)}")
