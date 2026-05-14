# user_tests/models.py (THE FINAL VERSION)

from django.db import models
from django.utils import timezone
from app.models import QuestionPaper ,Question


# ----------------------------------------------------------------------
# --- MODEL FOR CANDIDATE REGISTRATION AND REPETITION CHECK ---
# ----------------------------------------------------------------------

class TestRegistration(models.Model):
    """
    Stores one unique attempt (registration) by an email for a specific Question Paper.
    This model has been MOVED from the 'app' module.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    is_shortlisted = models.BooleanField(default=False)
    is_evaluated = models.BooleanField(default=False)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    question_paper = models.ForeignKey(
        QuestionPaper,
        on_delete=models.CASCADE,
        related_name="registrations",
        null=True, blank=True
    )

    start_time = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    # --- PROCTORING SUMMARY FIELDS ---
    total_violations = models.PositiveIntegerField(default=0)
    proctoring_score = models.FloatField(default=100.0, help_text="Trust percentage (0-100)")
    camera_access_granted = models.BooleanField(default=False)

    class Meta:
        # **THE FIX:** Use the old table name to match the existing data
        db_table = 'app_testregistration'
        
        # **CORE CONSTRAINT:** Ensures same email cannot be used for the same paper twice.
        unique_together = ('email', 'question_paper')

    def __str__(self):
        return f"{self.email} registered for {self.question_paper.title}"

class UserResponse(models.Model):
    """
    Stores the user's answer for a specific question during a test attempt.
    """
    # FK to TestRegistration (Pura test attempt)
    registration = models.ForeignKey(
        TestRegistration, 
        on_delete=models.CASCADE, 
        related_name="responses"
    )
    
    # FK to Question (Kaunsa question tha) - Yeh Question model 'app' se aayega
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name="user_responses"
    )
    
    # User ne kya answer diya (MCQ ho ya subjective)
    user_answer = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(null=True, blank=True)
    evaluation_reason = models.TextField(blank=True, null=True)  # CRITICAL: Prevents redundant AI calls
    class Meta:
        # Ek user ek test mein ek question ka sirf ek hi answer de sakta hai
        unique_together = ('registration', 'question')
        # DB Table ka naam default 'user_tests_userresponse' hoga
        
    def __str__(self):
        return f"Response for Q{self.question.id} by {self.registration.name}"
class CheatingLog(models.Model):
    """
    Logs potential cheating activities like tab switching or window blurring.
    """
    registration = models.ForeignKey(
        TestRegistration, 
        on_delete=models.CASCADE, 
        related_name="cheating_logs"
    )
    event_type = models.CharField(max_length=100) # e.g., 'tab_switch', 'window_blur', 'focus'
    url_at_time = models.CharField(max_length=500, null=True, blank=True)
    tab_title = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.event_type} - {self.registration.email} at {self.timestamp}"

class TestViolation(models.Model):
    """
    Robust model for proctoring violations with media proof.
    """
    VIOLATION_TYPES = [
        ('TAB_SWITCH', 'Tab Switch'),
        ('WINDOW_BLUR', 'Window Blur'),
        ('FULLSCREEN_EXIT', 'Fullscreen Exit'),
        ('FACE_NOT_FOUND', 'Face Not Found'),
        ('MULTIPLE_FACES', 'Multiple Faces Detected'),
        ('SCREEN_RECORDING_STOPPED', 'Screen Recording Stopped'),
        ('CAMERA_ACTIVE', 'Camera Activated'),
        ('CAMERA_DENIED', 'Camera Denied'),
        ('PERIODIC_CHECK', 'Periodic Identity Check'),
    ]

    registration = models.ForeignKey(
        TestRegistration, 
        on_delete=models.CASCADE, 
        related_name="violations"
    )
    violation_type = models.CharField(max_length=50, choices=VIOLATION_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    duration = models.FloatField(default=0.0, help_text="Duration in seconds (if applicable)")
    snapshot = models.ImageField(upload_to='proctoring/snapshots/', null=True, blank=True)
    video_clip = models.FileField(upload_to='proctoring/clips/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_violation_type_display()} - {self.registration.email}"
