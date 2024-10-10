from django.db import models
from django.contrib.auth.models import User

class Org(models.Model):
    org_id   = models.CharField(max_length=50, primary_key=True)
    org_name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.org_name


class LearnerJourney(models.Model):
    class Stage(models.IntegerChoices):
        PROFILE = 1, 'profile'
        DISCOVER = 2, 'discover'
        DISCUSS = 3, 'discuss'
        DELIVER = 4, 'deliver'
        DEMONSTRATE = 5, 'demonstrate'

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='learner_journey', primary_key=True)
    stage = models.PositiveSmallIntegerField(
        choices=Stage.choices, default=Stage.PROFILE)
    org = models.ForeignKey(Org, on_delete=models.SET_NULL,
                            null=True, blank=True, related_name='learner_journeys')

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
    first_name   = models.CharField(max_length=100, blank=True, null=True)
    last_name    = models.CharField(max_length=100, blank=True, null=True)
    age          = models.PositiveIntegerField(null=True, blank=True)    
    edu_level    = models.PositiveSmallIntegerField(choices=[
        (1, 'Primary School'),
        (2, 'Middle School'),
        (3, 'High School'),
        (4, 'Associate Degree'),
        (5, 'Bachelor\'s Degree'),
        (6, 'Master\'s Degree'),
        (7, 'PhD')
    ], blank=True, null=True)
    current_role = models.CharField(max_length=100, blank=True, null=True)

# Stage 2 or (1st D)
class DiscoverStage(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discover_stage')
    learning_goals   = models.JSONField(default=list)  # List of dicts: {'topic': 'string', 'reason': 'string'}
    # Something to capture about why the learning goals were chosen, like importance, relevance, etc
    learning_goal_rationale = models.TextField(blank=True, null=True)
    # self assessed knowledge level on a scale of 1-5
    knowledge_level = models.PositiveSmallIntegerField(choices=[
        (1, 'Beginner'),
        (2, 'Intermediate'),
        (3, 'Advanced'),
        (4, 'Expert')
    ], blank=True, null=True)    
    # How does the learner want to apply the knowledge
    application_area = models.TextField(blank=True, null=True)

# Stage 3 or (2nd D)
class DiscussStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discuss_stage')
    learning_objective = models.TextField(blank=True, null=True)
    

# Stage 4 or (3rd D)
class DeliverStage(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deliver_stage')
    modules    = models.JSONField(default=list) 
    timeline   = models.TextField(blank=True, null=True)

# Stage 5 or (4th D)
class DemonstrateStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='demonstrate_stage')
    current_module = models.CharField(max_length=200, blank=True, null=True)
    completed_modules = models.JSONField(default=list)  # List of strings
    understanding_level = models.CharField(max_length=200, blank=True, null=True) # For example: "Basic Understanding", "Intermediate", "Advanced"