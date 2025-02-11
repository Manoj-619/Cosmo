from django.db import models
from django.contrib.auth.models import User
import uuid

class Org(models.Model):
    org_id   = models.CharField(max_length=50, primary_key=True)
    org_name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.org_name


class NOS(models.Model):
    nos_id = models.CharField(max_length=50, primary_key=True)
    text = models.TextField()
    industry = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nos_id} - {self.industry}"

    class Meta:
        verbose_name = "NOS"
        verbose_name_plural = "NOS"

class JobDescription(models.Model):
    job_role = models.CharField(max_length=255)  # No longer unique
    description = models.TextField()
    responsibilities = models.TextField()
    nos = models.ManyToManyField('NOS', related_name='job_descriptions')
    ofqual = models.ManyToManyField('OFQUAL', related_name='job_descriptions')
    
    def __str__(self):
        return f"{self.job_role}"
    
    @property
    def summary(self):
        return f"**Role:** {self.job_role}\n\n**Purpose:** {self.description}\n\n**Responsibilities:**\n{self.responsibilities}"

    class Meta:
        verbose_name = "Job Description"
        verbose_name_plural = "Job Descriptions"

class OFQUAL(models.Model):
    ofqual_id = models.CharField(max_length=50, primary_key=True)
    level = models.PositiveIntegerField(default=1)
    text = models.TextField()
    markscheme = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return f"{self.ofqual_id} - {self.level}"
    
    class Meta:
        verbose_name = "OFQUAL"
        verbose_name_plural = "OFQUAL"


class UserProfile(models.Model):
    """Profile stage model.
    # NOTE: USED ONLY ONCE PER USER, DURING ONBOARDING
    
    This is not a part of the 4d sequence framework. Should be used only once per user, during onboarding.
    We don't need to connect this to 4d sequences via foreign keys because we could have multiple 4d sequences per user.
    """
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_stage', verbose_name="User")
    org             = models.ForeignKey(Org, on_delete=models.SET_NULL, null=True, blank=True)
    # Saved information (Already known to us)
    first_name      = models.CharField(max_length=100, blank=True, null=True, verbose_name="First Name")
    last_name       = models.CharField(max_length=100, blank=True, null=True, verbose_name="Last Name")
    
    current_role    = models.CharField(max_length=100, blank=True, null=True, verbose_name="Current Role")
    current_industry = models.CharField(max_length=100, blank=True, null=True, verbose_name="Current Industry")
    years_of_experience = models.PositiveIntegerField(
        blank=True, null=True,
        verbose_name="Years of experience"
    )

    # NOTE: Job information (TO BE COLLECTED)
    job_duration    = models.PositiveIntegerField(null=True, blank=True, verbose_name="Job Duration")
    manager         = models.CharField(max_length=100, blank=True, null=True, verbose_name="Manager")
    department      = models.CharField(max_length=100, blank=True, null=True, verbose_name="Department")
    job_description = models.ForeignKey(JobDescription, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Job Description")

    def save(self, *args, **kwargs):
        """Override save to automatically link to JobDescription when current_role is set"""
        if self.current_role and not self.job_description:
            try:
                self.job_description = JobDescription.objects.get(job_role__iexact=self.current_role)
            except JobDescription.DoesNotExist:
                pass  # If no matching job description found, continue without linking
        super().save(*args, **kwargs)

    def get_nos(self):
        """Get the NOS associated with the user's job description"""
        if self.job_description:
            # Return all NOS objects related to the job description
            return self.job_description.nos.all()
        return NOS.objects.none()  # Return empty queryset if no job description

    def get_ofqual(self):
        """Get the OFQUAL standard associated with the user's job description"""
        if self.job_description:
            return self.job_description.ofqual.all()
        return OFQUAL.objects.none()
    
    def __str__(self):
        """Get a dump of the Django model as a string."""
        return f"{self.user.email} - Profile"

    
    def get_summary(self):
        """Get a summary of the user's profile."""
        return f"""
        **Name**: {self.first_name} {self.last_name}
        **Current Role**: {self.current_role}
        **Current Industry**: {self.current_industry}
        **Years of experience**: {self.years_of_experience}
        **Job Duration**: {self.job_duration}
        **Manager**: {self.manager}
        **Department**: {self.department}
        """

    def check_complete(self):
        """Check if the profile is complete."""
        required_fields = {
            'first_name': 'First name is required',
            'last_name': 'Last name is required',
            'current_role': 'Current role is required',
            'current_industry': 'Current industry is required',
            'years_of_experience': 'Years of experience is required',
            'job_duration': 'Job duration is required',
            'manager': 'Manager is required',
            'department': 'Department is required',
        }

        for field, message in required_fields.items():
            if not getattr(self, field):
                return False, message
        
        return True, None


class TNAassessment(models.Model):
    
    class Meta:
        verbose_name_plural = "TNA Assessments"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tna_assessments')
    assessment_area = models.CharField(max_length=255, default=None, null=True)
    criterias       = models.JSONField(default=list, blank=True, null=True, verbose_name="Bloom's Taxonomy Criteria")
    user_assessed_knowledge_level = models.PositiveSmallIntegerField(
        choices=[
            (1, 'Novice (Basic awareness)'),
            (2, 'Advanced Beginner (Limited practical application)'),
            (3, 'Competent (Independent application)'),
            (4, 'Proficient (Deep understanding)'),
            (5, 'Expert (Strategic application)'),
            (6, 'Master (Industry leading)'),
            (7, 'Thought Leader (Setting industry standards)')
        ],
        blank=True, null=True
    )
    zavmo_assessed_knowledge_level = models.PositiveSmallIntegerField(
        choices=[
            (1, 'Novice (Basic awareness)'),
            (2, 'Advanced Beginner (Limited practical application)'),
            (3, 'Competent (Independent application)'),
            (4, 'Proficient (Deep understanding)'),
            (5, 'Expert (Strategic application)'),
            (6, 'Master (Industry leading)'),
            (7, 'Thought Leader (Setting industry standards)')
        ],
        blank=True, null=True
    )
    evidence_of_assessment = models.TextField(blank=True, null=True, verbose_name="Evidence of Assessment")
    # type = models.CharField(max_length=50, blank=True, null=True, verbose_name="Type")
    sequence = models.ForeignKey(
        'FourDSequence',
        on_delete=models.CASCADE,
        related_name='tna_assessments'
    )
    raw_ofqual_text = models.TextField(blank=True, null=True, verbose_name="Raw Ofqual Text")
    knowledge_gaps = models.TextField(blank=True, null=True, verbose_name="Knowledge Gaps")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    nos_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="NOS ID")
    status = models.CharField(
        max_length=20,
        choices=[
            ('To Assess', 'To Assess'),
            ('In Progress', 'In Progress'),
            ('Completed', 'Completed')
        ],
        default='To Assess'
    )
    finalized_blooms_taxonomy_level = models.CharField(max_length=20, blank=True, null=True, verbose_name="Finalized Bloom's Taxonomy Level")
    def __str__(self):
        return f"User {self.user.email} - Sequence {self.sequence.id} - TNA Assessment - Assessment Area: {self.assessment_area}"
    
    def check_complete(self):
        if not self.status:
            return False, f"NOS Assessment Area: {self.assessment_area} is not assessed yet."
        return True, None

    def get_summary(self):
        all_assessments = TNAassessment.objects.filter(user__email=self.user.email, sequence_id=self.sequence.id)
        return "\n\n".join([f"""
        **Assessment Area**: {s.assessment_area}
        **Status**: {s.status}
        **Evidence of Assessment**: {s.evidence_of_assessment}
        """ for s in all_assessments])
    
    def get_assessment_areas_info(self):
        """Get NOS Assessment Areas detailed information"""
        all_assessments = TNAassessment.objects.filter(user__email=self.user.email, sequence_id=self.sequence.id)
        number_of_assessments_for_current_4D_sequence = len(all_assessments)
        assessment_areas_with_nos_ids = [f"Assessment Area: {assessment.assessment_area} (NOS ID: {assessment.nos_id})" for assessment in all_assessments]
        areas_list = '\n- '.join(assessment_areas_with_nos_ids)
        
        return f"""Total NOS Areas: {all_assessments}
        Number of NOS Areas to complete in current 4D Sequence: {number_of_assessments_for_current_4D_sequence}
        NOS Assessment Areas for current 4D Sequence to be presented:
        - {areas_list}

        Presenting NOS Areas:

        |       **Assessments For Training Needs Analysis**      |   **NOS ID**  |
        |--------------------------------------------------------|---------------|
        |              [Assessment Area 1]                       |    [NOS ID]   |
        |              [Assessment Area 2]                       |    [NOS ID]   |
        
        """

# Stage 1
class DiscoverStage(models.Model):
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discover_stage')
    sequence       = models.OneToOneField('FourDSequence', 
                                          on_delete=models.CASCADE, 
                                          db_column='sequence_id',
                                          related_name='discover_stage')
    
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

    def __str__(self):
        return f"User {self.user.email} - Sequence {self.sequence.id} - Discover Stage"
    
    @property
    def knowledge_level_display(self):
        if self.knowledge_level is None:
            return "Unknown"
        return dict(self._meta.get_field('knowledge_level').choices)[self.knowledge_level]
    
    def get_summary(self):
        """Get a summary of the user's profile."""
        return f"""  
        **Learning Goals**: {self.learning_goals}
        **Learning Goal Rationale**: {self.learning_goal_rationale}
        **Knowledge Level**: {self.knowledge_level_display}
        **Application Area**: {self.application_area}
        """

    def check_complete(self):
        if not self.learning_goals:
            return False, "Learning goals are required"
        if not self.learning_goal_rationale:
            return False, "Learning goal rationale is required"
        if not self.knowledge_level:
            return False, "Knowledge level is required"
        if not self.application_area:
            return False, "Application area is required"
        return True, None

# TODO: Remove interest_areas

# Stage 2
class DiscussStage(models.Model):
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discuss_stage')
    sequence = models.OneToOneField('FourDSequence', 
                                    on_delete=models.CASCADE, 
                                    db_column='sequence_id',
                                    related_name='discuss_stage')
    
    interest_areas = models.JSONField(blank=True, null=True, verbose_name="Interest Areas")
    learning_style = models.TextField(blank=True, null=True, verbose_name="Learning Style")
    timeline =  models.IntegerField(blank=True, null=True, verbose_name="Available Time (hours per week)")
    curriculum     = models.JSONField(blank=True, null=True, verbose_name="Curriculum Plan")
    
    def __str__(self):
        return f"User {self.user.email} - Sequence {self.sequence.id} - Discuss Stage"
    
    def check_complete(self):
        if not self.learning_style:
            return False, "Learning style is required"
        if not self.timeline:
            return False, "Timeline is required"
        if not self.curriculum:
            return False, "Curriculum is required"
        return True, None
    
    def get_summary(self):
        """Get a summary of the user's profile."""
        return f"""
        **Interest Areas**: {self.interest_areas}
        **Learning Style**: {self.learning_style}
        **Available Time (hours per week)**: {self.timeline}
        **Curriculum**:
        {self.curriculum}
        """

# Stage 3
class DeliverStage(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deliver_stage')
    sequence  = models.OneToOneField('FourDSequence', 
                                     on_delete=models.CASCADE, 
                                     db_column='sequence_id',
                                     related_name='deliver_stage')
    
    # Lessons is a list of dictionaries, each representing a lesson
    lessons     = models.JSONField(default=list, blank=True, null=True, verbose_name="Lessons")
    is_complete = models.BooleanField(default=False, verbose_name="Is Complete")
    
    def __str__(self):
        return f"User {self.user.email} - Sequence {self.sequence.id} - Deliver Stage"
        
    def get_summary(self):
        """Get a summary of the user's profile."""
        summary = ""
        lessons = getattr(self, 'lessons', [])
        if lessons:
            for l, lesson in enumerate(lessons):
                summary += f"**Lesson {l+1}**: {lesson}\n"
        return summary.strip()
    
# Stage 4
class DemonstrateStage(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demonstrate_stage')
    sequence  = models.OneToOneField('FourDSequence', 
                                     on_delete=models.CASCADE, 
                                     db_column='sequence_id',
                                     related_name='demonstrate_stage')
    
    # Evaluations is a list of dictionaries, each representing an evaluation
    evaluations = models.JSONField(default=list, blank=True, null=True, verbose_name="Evaluations")
    understanding_level = models.PositiveSmallIntegerField(
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
    
    def __str__(self):
        return f"User {self.user.email} - Sequence {self.sequence.id} - Demonstrate Stage"
    
    @property
    def understanding_level_display(self):
        if self.understanding_level is None:
            return 'Unknown'
        return dict(self._meta.get_field('understanding_level').choices)[self.understanding_level]

    def check_complete(self):
        if not self.evaluations:
            return False, "Evaluations are required"
        if not self.understanding_level:
            return False, "Understanding levels are required"
        if not self.feedback_summary:
            return False, "Feedback summary is required"
        return True, None

    def get_summary(self):
        """Get a summary of the user's profile."""
        summary = ""
        if self.evaluations:  # Check if evaluations exists and is not None
            for evaluation in self.evaluations:
                summary += f"**Evaluation**: {evaluation}\n"
        summary += f"**Understanding Level**: {self.understanding_level_display}\n"
        summary += f"**Feedback Summary**: {self.feedback_summary}\n"
        return summary.strip()

class FourDSequence(models.Model):
    class Stage(models.IntegerChoices):
        DISCOVER = 1, 'discover'
        DISCUSS = 2, 'discuss'
        DELIVER = 3, 'deliver'
        DEMONSTRATE = 4, 'demonstrate'
        COMPLETED = 5, 'completed'
    
    # Use an automatically generated UUID for the id
    id = models.UUIDField(primary_key=True, 
                          default=uuid.uuid4, 
                          editable=False)
    assessments = models.ManyToManyField(TNAassessment, 
                                       related_name='sequences', 
                                       blank=True)
    user        = models.ForeignKey(User, 
                                    on_delete=models.CASCADE, 
                                    related_name='four_d_sequences')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_stage = models.PositiveSmallIntegerField(
        choices=Stage.choices, 
        default=Stage.DISCOVER
    )

    def __str__(self):
        return f"Sequence {self.id} - {self.stage_display}"

    @property
    def uuid_str(self):
        """Return the UUID as a string."""
        return str(self.id)

    @property
    def stage_display(self):
        return dict(self.Stage.choices)[self.current_stage]

    def update_stage(self, stage_name):
        """
        Update stage using stage name, not id.
        Stage names should be: 'discover', 'discuss', 'deliver', 'demonstrate', 'completed'
        """
        stage_dict = {name.lower(): value for value, name in self.Stage.choices}
        if stage_name.lower() in stage_dict:
            self.current_stage = stage_dict[stage_name.lower()]
            self.save()
        else:
            valid_stages = list(stage_dict.keys())
            raise ValueError(f"Invalid stage name: {stage_name}. Valid stages are: {valid_stages}")
