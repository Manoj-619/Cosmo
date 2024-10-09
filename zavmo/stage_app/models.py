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

    user  = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', primary_key=True)
    stage = models.PositiveSmallIntegerField(choices=Stage.choices, default=Stage.PROFILE)
    org   = models.ForeignKey(Org, on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')

    def increment_stage(self):
        """Increment the current stage to the next stage in the sequence."""
        if self.stage < max(self.Stage.values):
            self.stage += 1
            self.save()

    def __str__(self):
        return f"{self.user.username} - Stage: {self.get_stage_display()}"

# Stage 1 or (0th D)
class ProfileStage(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_stage')
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    age          = models.PositiveIntegerField()
    edu_level    = models.PositiveSmallIntegerField(choices=[
        (1, 'Primary School'),
        (2, 'Middle School'),
        (3, 'High School'),
        (4, 'Associate Degree'),
        (5, 'Bachelor\'s Degree'),
        (6, 'Master\'s Degree'),
        (7, 'PhD')
    ])

# Stage 2 or (1st D)
class DiscoverStage(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discover_stage')
    learning_goals   = models.JSONField(default=list)  # List of dicts: {'topic': 'string', 'reason': 'string'}

# Stage 3 or (2nd D)
class DiscussStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discuss_stage')
    content_preference   = models.CharField(max_length=200) # For example: "Textbooks", "Videos", "Interactive Content"
    structure_preference = models.CharField(max_length=200) # For example: "Sequential", "Hierarchical", "Flexible"
    pacing_preference     = models.CharField(max_length=200) # For example: "Fast-paced", "Slow-paced", "Adaptive"
    neurodiversity_considerations = models.TextField(blank=True, null=True) # For example: "Visual Aids", "Break Time", "Small Group Activities"

# Stage 4 or (3rd D)
class DeliverStage(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deliver_stage')
    modules    = models.JSONField(default=list)  # List of dicts: {'title': 'string', 'description': 'string', 'resources': ['string']}
    timeline   = models.TextField()

# Stage 5 or (4th D)
class DemonstrateStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='demonstrate_stage')
    current_module = models.CharField(max_length=200)
    completed_modules = models.JSONField(default=list)  # List of strings
    understanding_level = models.CharField(max_length=200) # For example: "Basic Understanding", "Intermediate", "Advanced"