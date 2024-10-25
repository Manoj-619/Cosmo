from django.db import models
from django.contrib.auth.models import User
import uuid

class Org(models.Model):
    org_id   = models.CharField(max_length=50, primary_key=True)
    org_name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.org_name

# NOTE: USED ONLY ONCE PER USER, DURING ONBOARDING
class UserProfile(models.Model):
    """
    Profile stage model.
    NOTE: 
    - This is not a part of the 4d sequence framework.
    - This should be used only once per user, during onboarding.
    - We don't need to connect this to 4d sequences via foreign keys because we could have multiple 4d sequences per user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_stage', verbose_name="User")
    org = models.ForeignKey(Org, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="First Name")
    last_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Last Name")
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name="Age")    
    edu_level = models.PositiveSmallIntegerField(
        choices=[
            (1, 'Primary School'),
            (2, 'Middle School'),
            (3, 'High School'),
            (4, 'Associate Degree'),
            (5, 'Bachelor\'s Degree'),
            (6, 'Master\'s Degree'),
            (7, 'PhD')
        ],
        blank=True, null=True,
        verbose_name="Education Level"
    )
    current_role = models.CharField(max_length=100, blank=True, null=True, verbose_name="Current Role")
    
    def __str__(self):
        """Get a dump of the Django model as a string."""
        return f"{self.user.email} - {self.first_name} {self.last_name} - {self.age} - {self.edu_level} - {self.current_role}"

    @property
    def edu_level_display(self):
        if self.edu_level is None:
            return None
        # Get choices from the field definition, not the value
        return dict(self._meta.get_field('edu_level').choices)[self.edu_level]
    
    def get_summary(self):
        """Get a summary of the user's profile."""
        return f"""
        **Name**: {self.first_name} {self.last_name}
        **Age**: {self.age}
        **Education Level**: {self.edu_level_display}
        **Current Role**: {self.current_role}
        """

    def is_complete(self):
        """Check if the profile is complete."""
        return self.first_name and self.last_name and self.age and self.edu_level and self.current_role


# Stage 1
class DiscoverStage(models.Model):
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discover_stage')
    sequence       = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='discover_stage')
    
    learning_goals = models.TextField(blank=True, null=True, verbose_name="Learning Goals")
    learning_goal_rationale = models.TextField(blank=True, null=True, verbose_name="Learning Goal Rationale")
    knowledge_level = models.PositiveSmallIntegerField(
        choices=[
            (1, 'Beginner'),
            (2, 'Intermediate'),
            (3, 'Advanced'),
            (4, 'Expert')
        ],
        blank=True, null=True,
        verbose_name="Knowledge Level"
    )    
    application_area = models.TextField(blank=True, null=True, verbose_name="Application Area")
    
    @property
    def knowledge_level_display(self):
        return dict(self._meta.get_field('knowledge_level').choices)[self.knowledge_level]
    
    def __str__(self):
        """Get a dump of the Django model as a string."""
        string_value = ""
        for key, value in self.__dict__.items():
            string_value += f"\n**{key.replace('_', ' ').title()}**: {value}"
        return string_value


# Stage 2
class DiscussStage(models.Model):
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discuss_stage')
    sequence = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='discuss_stage')
    
    interest_areas = models.JSONField(blank=True, null=True, verbose_name="Interest Areas")
    learning_style = models.TextField(blank=True, null=True, verbose_name="Learning Style")
    available_time = models.IntegerField(blank=True, null=True, verbose_name="Available Time (hours per week)")
    curriculum     = models.JSONField(blank=True, null=True, verbose_name="Curriculum Plan")
    
    def __str__(self):
        """Get a dump of the Django model as a string."""
        string_value = ""
        for key, value in self.__dict__.items():
            string_value += f"\n**{key.replace('_', ' ').title()}**: {value}"
        return string_value


# Stage 3
class DeliverStage(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deliver_stage')
    sequence  = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='deliver_stage')
    
    # Lessons is a list of dictionaries, each representing a lesson
    lessons    = models.JSONField(blank=True, null=True, verbose_name="Lessons")

# Stage 4
class DemonstrateStage(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demonstrate_stage')
    sequence  = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='demonstrate_stage')
    
    # Evaluations is a list of dictionaries, each representing an evaluation
    evaluations = models.JSONField(blank=True, null=True, verbose_name="Evaluations")
    understanding_levels = models.PositiveSmallIntegerField(
        choices=[
            (1, 'Beginner'),
            (2, 'Intermediate'),
            (3, 'Advanced'),
            (4, 'Expert')
        ],
        blank=True, null=True,
        verbose_name="Understanding Level"
    )
    feedback_summary = models.TextField(blank=True, null=True, verbose_name="Feedback Summary")
    
    @property
    def understanding_level_display(self):
        if self.understanding_level is None:
            return None
        return dict(self.understanding_level.choices)[self.understanding_level]


class FourDSequence(models.Model):
    class Stage(models.IntegerChoices):
        DISCOVER = 1, 'discover'
        DISCUSS = 2, 'discuss'
        DELIVER = 3, 'deliver'
        DEMONSTRATE = 4, 'demonstrate'
        COMPLETED = 5, 'completed'
    
    # Use an automatically generated UUID for the id
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='four_d_sequences')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_stage = models.PositiveSmallIntegerField(choices=Stage.choices, default=Stage.DISCOVER)


    @property
    def stage_display(self):
        return dict(self.Stage.choices)[self.current_stage]
    
    def advance_stage(self):
        """
        Advance to the next stage after updating the current stage.
        """
        # Check if the current stage is less than COMPLETED
        if self.current_stage < self.Stage.COMPLETED:
            # Increment the stage to the next one
            self.current_stage += 1
            self.save()
        else:
            raise ValueError("The sequence is already completed and cannot be advanced.")
        
    def __str__(self):
        """Get a dump of the Django model as a string."""
        string_value = ""
        for key, value in self.__dict__.items():
            string_value += f"\n**{key.replace('_', ' ').title()}**: {value}"
        return string_value



