# recruitment/models.py
from django.db import models
from django.conf import settings
from app.models import QuestionPaper # Existing QuestionPaper model
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

# ... rest of the models (Candidate, RoundFeedback) remain the same for now ...
# 2. Candidate Model: Central Tracking
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
    round_name = models.CharField(max_length=50) # e.g., 'GD Round', 'Interview Round'
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
        # Ensures one feedback per interviewer per candidate per round
        unique_together = ('candidate', 'round_name', 'interviewer')