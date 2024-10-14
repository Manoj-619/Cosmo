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


    def __str__(self):
        return f"{self.user.username} - Stage: {self.get_stage_display()}"


# Stage 1 or (0th D)
class ProfileStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_stage', verbose_name="User")
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

# Stage 2 or (1st D)
class DiscoverStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discover_stage', verbose_name="User")
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

# Stage 3 or (2nd D)
class DiscussStage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='discuss_stage', verbose_name="User")
    lesson_plan = models.TextField(blank=True, null=True, verbose_name="Lesson Plan")
    interest_areas = models.TextField(blank=True, null=True, verbose_name="Interest Areas") 
    learning_style = models.TextField(blank=True, null=True, verbose_name="Learning Style")
    goals_alignment = models.TextField(blank=True, null=True, verbose_name="Goals Alignment")
    
    def reset(self):
        self.lesson_plan = ''
        self.interest_areas = ''
        self.learning_style = ''
        self.goals_alignment = ''
        self.save()

# Stage 4 or (3rd D)
class DeliverStage(models.Model):
    user      = models.OneToOneField(User, on_delete=models.CASCADE, related_name='deliver_stage', verbose_name="User")
    modules   = models.TextField(blank=True, null=True, verbose_name="Modules")
    timeline  = models.TextField(blank=True, null=True, verbose_name="Timeline")
    resources = models.TextField(blank=True, null=True, verbose_name="Resources")
    
    def reset(self):
        self.modules = ''
        self.timeline = ''
        self.resources = ''
        self.save()

# Stage 5 or (4th D)
class DemonstrateStage(models.Model):
    user                = models.OneToOneField(User, on_delete=models.CASCADE, related_name='demonstrate_stage', verbose_name="User")
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

