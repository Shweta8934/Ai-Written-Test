# app/models.py

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import models
import re
from django.db import models  # ✅ YEH ZAROORI HAI

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Naye User create hone par turant UserProfile banao."""
    if created:
        UserProfile.objects.create(user=instance)

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def pretty_name(self):
        """
        Returns a nicely formatted name for the UI.
        """

        if self.name == "nodejs":
            return "Node.js"
        if self.name == "javascript":
            return "JavaScript"

        return self.name.title()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

class Section(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=100, default="")
    sections = models.ManyToManyField(Section)

    def __str__(self):
        return self.name


class QuestionPaper(models.Model):
    """
    Represents a complete, saved question paper.
    """

    cutoff_score = models.PositiveIntegerField(
        default=20, help_text="Minimum percentage to pass (e.g., 70)"
    )
    title = models.CharField(max_length=255)
    job_title = models.CharField(max_length=200)
    department_name = models.CharField(max_length=100, default="Unassigned")
    min_exp = models.PositiveIntegerField()
    max_exp = models.PositiveIntegerField()
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    skills_list = models.TextField(
        help_text="Comma-separated list of skills", default=""
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_papers",
        null=True,
    )
    total_questions = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    is_active = models.BooleanField(default=False)
    is_public_active = models.BooleanField(null=True, blank=True)
    is_private_link_active = models.BooleanField(default=False) # <--- ADD default=False
    job_location = models.CharField(max_length=50, null=True, blank=True)
    recruitment_drive = models.ForeignKey(
        'RecruitmentDrive',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assessment_rounds'
    )
    # ✅ ADD THESE MISSING FIELDS:
    job_location = models.CharField(max_length=100, blank=True, default="")
    job_type = models.CharField(
        max_length=50, 
        choices=[('Full Time', 'Full Time'), ('Part Time', 'Part Time'), ('Contract', 'Contract'), ('Internship', 'Internship')], 
        blank=True, 
        default=""
    )
    positions = models.IntegerField(default=1) 
    rounds = models.CharField(max_length=100, blank=True, default="")
    pay_scale = models.CharField(max_length=100, blank=True, default="")
    end_date = models.DateField(null=True, blank=True) # Assuming it's a date field
    round_number = models.PositiveIntegerField(default=1, help_text="Which round is this test? (1, 2, 3...)")
    is_interview_round = models.BooleanField(
        default=False,
        help_text="True if this is an Interview Round (no auto-assessment)"
    )
    def __str__(self):
        return f"{self.title} for {self.job_title}"


class PaperSection(models.Model):
    """
    Represents a single section within a QuestionPaper.
    """

    question_paper = models.ForeignKey(
        QuestionPaper, on_delete=models.CASCADE, related_name="paper_sections"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    weightage = models.FloatField(default=0.0, help_text="Weightage percentage for this section")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Section '{self.title}' of paper '{self.question_paper.title}'"


class Question(models.Model):
    """
    Represents a single question within a PaperSection.
    """

    class QuestionType(models.TextChoices):
        MCQ = "MCQ", "Multiple Choice"
        SA = "SA", "Short Answer"
        CODE = "CODE", "Coding"

    section = models.ForeignKey(
        PaperSection, on_delete=models.CASCADE, related_name="questions"
    )
    text = models.TextField()
    answer = models.TextField()
    options = models.JSONField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    weightage = models.FloatField(
        default=0.0, 
        null=True,     # डेटाबेस में NULL स्वीकार करें
        blank=True     # Django फॉर्म्स में खाली स्वीकार करें
    )
    question_type = models.CharField(
        max_length=15,
        choices=QuestionType.choices,
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Q: {self.text[:50]}..."


# class TestRegistration(models.Model):
#     email = models.EmailField(max_length=255)
#     phone_number = models.CharField(max_length=15)
#     address = models.TextField(null=True, blank=True)
#     start_time = models.DateTimeField()
#     is_completed = models.BooleanField(default=False)
#     question_paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE)
#     score = models.FloatField(null=True, blank=True)
#     is_shortlisted = models.BooleanField(default=False)
    
#     recruitment_drive = models.ForeignKey(
#         'RecruitmentDrive',  # String reference - will be resolved later
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='test_attempts'
#     )
#     candidate_application = models.ForeignKey(
#         'CandidateApplication',  # String reference - will be resolved later
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name='app_test_attempts'
#     )
#     candidate_stage = models.CharField(
#         max_length=20,
#         null=True,
#         blank=True,
#         # ✅ FIX: Use hardcoded choices instead of CandidateApplication.CandidateStage.choices
#         choices=[
#             ('APPLIED', 'Applied'),
#             ('SCREENING', 'Under Screening'),
#             ('ROUND_1', 'Round 1 (Test)'),
#             ('ROUND_2', 'Round 2 (Interview)'),
#             ('FINAL_ROUND', 'Final Round'),
#             ('HIRED', 'Hired'),
#             ('REJECTED', 'Rejected'),
#             ('WITHDRAWN', 'Withdrawn'),
#         ]
#     )
    
#     class Meta:
#         db_table = "app_testregistration"
#         managed = False  # Keep this as-is
 
   
  
#     def __str__(self):
#         return f"{self.email} - Paper ID: {self.question_paper.id}"
# ...existing code...
class TestRegistration(models.Model):
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15)
    address = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    question_paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE)
    score = models.FloatField(null=True, blank=True)
    is_shortlisted = models.BooleanField(default=False)
    
    recruitment_drive = models.ForeignKey(
        'RecruitmentDrive',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_attempts'
    )
    # candidate_stage field removed to match existing DB schema
    # ...existing code...
    class Meta:
        db_table = "app_testregistration"
        managed = False  # Keep this as-is
# ...existing code...

class UserResponse(models.Model):
    user_answer = models.TextField()
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    registration = models.ForeignKey(TestRegistration, on_delete=models.DO_NOTHING)
    is_correct = models.BooleanField(null=True, blank=True)
    
    class Meta:
        db_table = "user_tests_userresponse"
        managed = False

    def __str__(self):
        return f"Response for Q:{self.question.id} by Reg:{self.registration.id}"


# ============ RECRUITMENT DRIVE MODELS ============

import uuid
from django.core.validators import MinValueValidator

class RecruitmentDrive(models.Model):
    """
    Main model for managing recruitment drives with multi-round assessments.
    """
    
    # Status choices
    class DriveStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open for Applications'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    # Basic Information
    title = models.CharField(max_length=255, help_text="e.g., 'Backend Developer Hiring - Jan 2025'")
    position = models.CharField(max_length=200, help_text="Job role, e.g., 'Senior Backend Developer'")
    description = models.TextField(help_text="Full job description")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Hiring Capacity
    total_positions = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    filled_positions = models.PositiveIntegerField(default=0)
    
    # Timeline
    application_start_date = models.DateField()
    application_end_date = models.DateField()
    expected_joining_date = models.DateField(null=True, blank=True)
    
    # Status Management
    drive_status = models.CharField(
        max_length=20,
        choices=DriveStatus.choices,
        default=DriveStatus.DRAFT
    )
    auto_close_on_full = models.BooleanField(default=True)
    
    # Link Generation
    drive_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_public_link_active = models.BooleanField(default=False)
    link_expiry_date = models.DateField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_drives'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Assessment Configuration
    require_test = models.BooleanField(default=True)
    test_papers = models.ManyToManyField(
        'QuestionPaper',
        related_name='linked_drives',
        blank=True
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.position}"
    
    @property
    def positions_remaining(self):
        """Calculate remaining positions"""
        return self.total_positions - self.filled_positions
    
    @property
    def is_accepting_applications(self):
        """
        Check if drive is accepting applications based on:
        1. Drive status is OPEN
        2. Public link is active
        3. Link has not expired (if expiry date is set)
        4. Application window is open (between start and end dates)
        """
        from django.utils import timezone
        now = timezone.now()
        
        # Check drive status
        if self.drive_status != 'OPEN':
            return False
        
        # Check if public link is active
        if not self.is_public_link_active:
            return False
        
        # ✅ FIX: Check if link has expired
        if self.link_expiry_date and now > self.link_expiry_date:
            return False
        
        # Check application date window
        if self.application_start_date and now < self.application_start_date:
            return False
        
        if self.application_end_date and now > self.application_end_date:
            return False
        
        return True
    
    
    @property
    def hiring_progress_percentage(self):
        """Calculate hiring progress as percentage"""
        if self.total_positions == 0:
            return 0
        return round((self.filled_positions / self.total_positions) * 100, 1)
    
    def get_public_link(self):
        """Generate public application link"""
        from django.urls import reverse
        return reverse('recruitment_apply', kwargs={'drive_uuid': str(self.drive_uuid)})
    
    def mark_as_completed(self):
        """Mark drive as completed"""
        from django.utils import timezone
        self.drive_status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.is_public_link_active = False
        self.save(update_fields=['drive_status', 'completed_at', 'is_public_link_active'])
    
    def get_stage_wise_count(self):
        """Return count of candidates per stage"""
        from django.db.models import Count
        return CandidateApplication.objects.filter(
            recruitment_drive=self
        ).values('current_stage').annotate(count=Count('id'))


class CandidateApplication(models.Model):
    """
    Tracks a candidate's overall journey through a recruitment drive.
    Aggregates multiple test attempts across rounds.
    """
    
    class CandidateStage(models.TextChoices):
        APPLIED = 'APPLIED', 'Applied'
        SCREENING = 'SCREENING', 'Under Screening'
        ROUND_1 = 'ROUND_1', 'Round 1 (Test)'
        ROUND_2 = 'ROUND_2', 'Round 2 (Interview)'
        FINAL_ROUND = 'FINAL_ROUND', 'Final Round'
        HIRED = 'HIRED', 'Hired'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
    
    class ApplicationStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        HIRED = 'HIRED', 'Hired'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
    
    
    recruitment_drive = models.ForeignKey(RecruitmentDrive, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    full_name = models.CharField(max_length=255)
    # ⭐ NEW FIELDS FOR APPLICATION FORM ⭐
    is_experienced = models.BooleanField(
        default=False, 
        help_text="True if candidate is Experienced (based on candidateType radio button)"
    )
    total_experience = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Total years of experience (0 for Fresher)"
    )
    current_ctc = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    expected_ctc = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    current_ctc_rate = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text="Unit for Current CTC (e.g., LPA, PM)"
    ) 
    expected_ctc_rate = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text="Unit for Expected CTC (e.g., LPA, PM)"
    )
    notice_period = models.CharField(
        max_length=100, 
        null=True, 
        blank=True
    )
    skills = models.TextField(
        null=True, 
        blank=True,
        help_text="Your Skills (comma separated)"
    )
    current_location = models.CharField(
        max_length=100, 
        null=True, 
        blank=True
    )
    referral_source = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="From where did you hear about us?"
    )
    photo_file = models.FileField(
        upload_to='photos/', 
        null=True, 
        blank=True,
        help_text="Candidate Photo"
    ) 
    
    # Add Foreign Key to QuestionPaper (for Interview Applications)
    linked_paper = models.ForeignKey(
        'QuestionPaper',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications_received'
    )
    # Stage tracking
    current_stage = models.CharField(
        max_length=20,
        choices=CandidateStage.choices,
        default=CandidateStage.APPLIED
    )
    overall_status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.ACTIVE
    )
    
    # Test tracking
    all_tests_completed = models.BooleanField(default=False)
    aggregate_score = models.FloatField(null=True, blank=True)
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    hired_at = models.DateTimeField(null=True, blank=True)
    
    # Additional fields
    resume_file = models.FileField(upload_to='resumes/', null=True, blank=True)
    cover_letter = models.TextField(null=True, blank=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    recruitment_drive = models.ForeignKey(RecruitmentDrive, on_delete=models.SET_NULL, null=True, blank=True)
    # Metadata
    stage_updated_at = models.DateTimeField(null=True, blank=True)
    stage_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stage_updates'
    )
    
    class Meta:
        # unique_together = ['recruitment_drive', 'email']
        ordering = ['-applied_at']
    
    def __str__(self):
        if self.linked_paper:
             return f"{self.full_name} ({self.email}) - {self.linked_paper.title}"
        return f"{self.full_name} ({self.email})"
        # return f"{self.full_name} ({self.email}) - {self.recruitment_drive.title}"
    
    def get_all_test_scores(self):
        """Get scores from all test rounds"""
        return self.test_attempts.filter(
            is_completed=True
        ).values_list('score', flat=True)
    
    def calculate_aggregate_score(self):
        """Calculate average score across all completed tests"""
        scores = list(self.get_all_test_scores())
        if scores:
            self.aggregate_score = sum(scores) / len(scores)
            self.save(update_fields=['aggregate_score'])
            return self.aggregate_score
        return None
    
    def move_to_stage(self, new_stage, updated_by=None, reason=''):
        """Update candidate stage with validation"""
        from django.utils import timezone
        self.current_stage = new_stage
        self.stage_updated_at = timezone.now()
        self.stage_updated_by = updated_by
        
        if new_stage == 'HIRED':
            self.overall_status = 'HIRED'
            self.hired_at = timezone.now()
            # Increment drive's filled_positions
            self.recruitment_drive.filled_positions += 1
            self.recruitment_drive.save(update_fields=['filled_positions'])
            
            # Auto-complete drive if full
            if self.recruitment_drive.filled_positions >= self.recruitment_drive.total_positions:
                if self.recruitment_drive.auto_close_on_full:
                    self.recruitment_drive.mark_as_completed()
        
        elif new_stage == 'REJECTED':
            self.overall_status = 'REJECTED'
            self.rejection_reason = reason
        
        elif new_stage == 'WITHDRAWN':
            self.overall_status = 'WITHDRAWN'
        
        self.save()
