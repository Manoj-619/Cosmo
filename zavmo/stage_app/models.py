from django.db import models
from django.contrib.auth.models import User

class Org(models.Model):
    org_id   = models.CharField(max_length=50, primary_key=True)
    org_name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.org_name


class Profile(models.Model):
    class Stage(models.IntegerChoices):
        PROFILE = 1, 'Profile'
        DISCOVER = 2, 'Discover'
        DISCUSS = 3, 'Discuss'
        DELIVER = 4, 'Deliver'
        DEMONSTRATE = 5, 'Demonstrate'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', primary_key=True)
    stage = models.PositiveSmallIntegerField(choices=Stage.choices, default=Stage.PROFILE)
    org = models.ForeignKey(Org, on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')

    def increment_stage(self):
        """Increment the current stage to the next stage in the sequence."""
        if self.stage < max(self.Stage.values):
            self.stage += 1
            self.save()

    def __str__(self):
        return f"{self.user.username} - Stage: {self.get_stage_display()}"


class ProfileStage(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_stage')
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)    
    current_role   = models.CharField(max_length=200)
    hobbies        = models.TextField()
    learning_goals = models.JSONField(default=list)  # List of learning goals
    available_study_time = models.CharField(max_length=100)

    def __str__(self):
        return f"Profile Stage - {self.user.username}"


class DiscoverStage(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discover_stage')
    learning_goals   = models.JSONField(default=list)  # List of dicts: {'topic': 'string', 'reason': 'string'}
    related_interests = models.JSONField(default=list)  # List of strings
    motivation = models.TextField()
    potential_applications = models.JSONField(default=list)  # List of strings
    current_knowledge_level = models.CharField(max_length=200)

    def __str__(self):
        return f"Discover Stage - {self.user.username}"


class DiscussStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discuss_stage')
    content_preference = models.CharField(max_length=200)
    structure_preference = models.CharField(max_length=200)
    pacing_preference = models.CharField(max_length=200)
    neurodiversity_considerations = models.TextField(blank=True, null=True)
    additional_preferences = models.TextField(blank=True, null=True)
    habit_preferences = models.TextField(blank=True, null=True)
    ideal_learning_time = models.CharField(max_length=100)

    def __str__(self):
        return f"Discuss Stage - {self.user.username}"


class DeliverStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deliver_stage')
    modules = models.JSONField(default=list)  # List of dicts: {'title': 'string', 'description': 'string', 'resources': ['string'], 'activities': ['string'], 'estimated_duration': 'string'}
    timeline = models.TextField()
    milestones = models.JSONField(default=list)  # List of strings

    def __str__(self):
        return f"Deliver Stage - {self.user.username}"


class DemonstrateStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='demonstrate_stage')
    current_module = models.CharField(max_length=200)
    completed_modules = models.JSONField(default=list)  # List of strings
    understanding_level = models.CharField(max_length=200)
    next_steps = models.TextField()

    def __str__(self):
        return f"Demonstrate Stage - {self.user.username}"