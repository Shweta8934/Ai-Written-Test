# recruitment/models.py
from django.db import models
from django.conf import settings
from app.models import QuestionPaper 
from user_tests.models import TestRegistration 
class JobPost(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Closed', 'Closed'),
        ('Archived', 'Archived'),
    ]
    JOB_TYPE_CHOICES = [
        ('Full-Time', 'Full-Time'),
        ('Part-Time', 'Part-Time'),
        ('Contract', 'Contract'),
        ('Internship', 'Internship'),
    ]
    
    # 📌 Job Details (Image Fields)
    title = models.CharField(max_length=255, verbose_name="Job Title") # Job Title
    department = models.CharField(max_length=100, blank=True, verbose_name="Department") # Department
    location = models.CharField(max_length=100, blank=True, verbose_name="Job Location") # Job Location
    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES, default='Full-Time', verbose_name="Job Type") # Job Type

    # 📌 Requirements (Image Fields)
    experience_min = models.IntegerField(default=0, verbose_name="Experience Min (Years)") # Experience Min
    experience_max = models.IntegerField(default=5, verbose_name="Experience Max (Years)") # Experience Max
    skills_required = models.TextField(blank=True, verbose_name="Skills Required (Comma separated)") # Skills
    positions_available = models.IntegerField(default=1, verbose_name="Positions Available") # Positions (renamed for clarity)

    # 📌 Logistics (Image Fields)
    # Note: 'Rounds' will be better handled in a separate related model/structure for complexity, 
    # but we will store the total number of rounds here for simplicity in the form.
    total_rounds = models.IntegerField(default=3, verbose_name="Total Interview Rounds") # Rounds (Simplified)
    pay_scale = models.CharField(max_length=100, blank=True, verbose_name="Pay Scale / Salary Range") # Pay Scale
    end_date = models.DateField(null=True, blank=True, verbose_name="Application End Date") # End Date

    # 📌 Existing Fields
    description = models.TextField()
    question_paper = models.ForeignKey(
        QuestionPaper, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='job_posts',
        verbose_name="Written Test Question Paper"
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Open')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    public_link_slug = models.SlugField(unique=True, max_length=100, help_text="Unique URL identifier")
    created_at = models.DateTimeField(auto_now_add=True)
  
    def __str__(self):
        return self.title


class Candidate(models.Model):
    # This links the candidate to the initial Test Registration details
    test_registration = models.OneToOneField(
        TestRegistration, 
        on_delete=models.CASCADE, 
        related_name='candidate_profile'
    )
    job_post = models.ForeignKey(
        JobPost, 
        on_delete=models.CASCADE, 
        related_name='candidates'
    )
    
    ROUND_CHOICES = [
        ('Applied', 'Applied'),
        ('Written Test Passed', 'Written Test Passed'),
        ('GD Round', 'Group Discussion Round'),
        ('Interview Round', 'Technical Interview'),
        ('HR Round', 'HR Interview'),
        ('Final Offer', 'Final Offer'),
        ('Rejected', 'Rejected'),
    ]
    current_round = models.CharField(max_length=50, choices=ROUND_CHOICES, default='Applied')
    is_hired = models.BooleanField(default=False)
    is_experienced = models.CharField(max_length=15, default='fresher', null=True, blank=True)
    # The 'mobile' field that caused the error:
    mobile = models.CharField(max_length=15, null=True, blank=True) 
    
    your_skills = models.TextField(blank=True, null=True)
    total_experience = models.IntegerField(default=0, blank=True, null=True)
    current_location = models.CharField(max_length=100, blank=True, null=True)
    current_ctc = models.CharField(max_length=50, blank=True, null=True)
    current_ctc_rate = models.CharField(max_length=50, blank=True, null=True)
    expected_ctc = models.CharField(max_length=50, blank=True, null=True)
    expected_ctc_rate = models.CharField(max_length=50, blank=True, null=True)
    notice_period = models.CharField(max_length=50, blank=True, null=True)
    heard_about_us = models.CharField(max_length=255, blank=True, null=True)
    cover_letter = models.TextField(blank=True, null=True)
    
    # FileFields are already nullable, confirm they are set correctly:
    cv_or_resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    photo = models.FileField(upload_to='photos/', blank=True, null=True)
    @property
    def name(self):
        return self.test_registration.name

    def __str__(self):
        return f"{self.name} - {self.job_post.title}"


class RoundFeedback(models.Model):
    candidate = models.ForeignKey(
        Candidate, 
        on_delete=models.CASCADE, 
        related_name='feedbacks'
    )
    round_name = models.CharField(max_length=50) 
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='candidate_reviews'
    )
    
    score = models.IntegerField(null=True, blank=True, help_text="Score out of 10")
    comments = models.TextField()
    
    RECOMMENDATION_CHOICES = [
        ('Pass', 'Pass'),
        ('Fail', 'Fail'),
        ('Hold', 'Hold'),
    ]
    recommendation = models.CharField(max_length=10, choices=RECOMMENDATION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'round_name', 'interviewer')


from django.db import models
from django.conf import settings

class EvaluationTemplate(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Template Name") 
   
    cutoff_score = models.IntegerField(default=60, help_text="Minimum score required to pass")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class EvaluationParameter(models.Model):
    template = models.ForeignKey(
        EvaluationTemplate, 
        on_delete=models.CASCADE, 
        related_name='parameters'
    )
    name = models.CharField(max_length=255, verbose_name="Parameter Name") # e.g., "Communication", "Coding Logic"
    weight = models.IntegerField(default=10, help_text="Max score for this parameter")

    def __str__(self):
        return self.name



class RoundMaster(models.Model):
    ROUND_TYPE_CHOICES = Candidate.ROUND_CHOICES 

    name = models.CharField(max_length=255, verbose_name="Round Name") # e.g., "Senior Tech Round - Java"
    round_type = models.CharField(max_length=50, choices=ROUND_TYPE_CHOICES, verbose_name="Round Type")
    
   
    evaluation_template = models.ForeignKey(
        EvaluationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='linked_rounds',
        verbose_name="Linked Evaluation Template"
    )
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_round_type_display()})"


# recruitment/models.py ke end mein ye add karein

from .models import RoundMaster # Ensure RoundMaster is imported

# ... existing JobPost class ...

# recruitment/models.py

# ... existing code ...

class JobRound(models.Model):
    job_post = models.ForeignKey(
        JobPost, 
        on_delete=models.CASCADE, 
        related_name='rounds'
    )
    round_master = models.ForeignKey(
        RoundMaster, 
        on_delete=models.CASCADE,
        verbose_name="Round Type"
    )
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.job_post.title} - Round {self.order}: {self.round_master.name}"