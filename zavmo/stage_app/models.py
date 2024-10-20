from django.db import models
from django.contrib.auth.models import User

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
    
    def reset(self):
        self.first_name = ''
        self.last_name = ''
        self.age = None
        self.edu_level = None
        self.current_role = ''
        self.save()

# Stage 1
class DiscoverStage(models.Model):
    sequence = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='discover_stage')
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
    
    def reset(self):
        self.learning_goals = ''
        self.learning_goal_rationale = ''
        self.knowledge_level = None
        self.application_area = ''
        self.save()

# Stage 2
class DiscussStage(models.Model):
    sequence = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='discuss_stage')
    interest_areas = models.TextField(blank=True, null=True, verbose_name="Interest Areas") 
    learning_style = models.TextField(blank=True, null=True, verbose_name="Learning Style")
    curriculum = models.JSONField(blank=True, null=True, verbose_name="Curriculum Plan")
    timeline  = models.TextField(blank=True, null=True, verbose_name="Timeline")
    goals_alignment = models.TextField(blank=True, null=True, verbose_name="Goals Alignment")
    
    
    def reset(self):
        self.interest_areas = ''
        self.learning_style = ''
        self.curriculum = ''
        self.timeline=''
        self.goals_alignment = ''
        self.save()
    
    # def generate_lesson_plan(self, curriculum_json): 
    #     parsed_curriculum = parse_curriculum(curriculum_json)
        
    #     if parsed_curriculum is None:
    #         raise ValueError("Failed to parse curriculum data.")
        
    #     self.curriculum_data = parsed_curriculum
    #     self.lesson_plan = f"Generated lesson plan for {parsed_curriculum['title']}"
    #     self.save()


# Stage 3
class DeliverStage(models.Model):
    sequence = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='deliver_stage')
    modules   = models.TextField(blank=True, null=True, verbose_name="Modules")
    timeline  = models.TextField(blank=True, null=True, verbose_name="Timeline")
    resources = models.TextField(blank=True, null=True, verbose_name="Resources")
    
    def reset(self):
        self.modules = ''
        self.timeline = ''
        self.resources = ''
        self.save()

# Stage 4
class DemonstrateStage(models.Model):
    sequence = models.OneToOneField('FourDSequence', on_delete=models.CASCADE, related_name='demonstrate_stage')
    topics              = models.TextField(blank=True, null=True, verbose_name="Topics")
    summary             = models.TextField(blank=True, null=True, verbose_name="Summary")
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
    feedback            = models.TextField(blank=True, null=True, verbose_name="Feedback")

    def reset(self):
        self.topics = ''
        self.summary = ''
        self.understanding_levels = None
        self.feedback = ''
        self.save()


class FourDSequence(models.Model):
    class Stage(models.IntegerChoices):
        DISCOVER = 1, 'discover'
        DISCUSS = 2, 'discuss'
        DELIVER = 3, 'deliver'
        DEMONSTRATE = 4, 'demonstrate'
        COMPLETED = 5, 'completed'
        
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='four_d_sequences')
    org = models.ForeignKey(Org, on_delete=models.SET_NULL, null=True, blank=True)
    title      = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_stage = models.PositiveSmallIntegerField(choices=Stage.choices, default=Stage.DISCOVER)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    @property
    def stage_display(self):
        return dict(self.Stage.choices)[self.current_stage]
