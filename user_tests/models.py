# user_tests/models.py (THE FINAL VERSION)

from django.db import models
from django.utils import timezone
from app.models import QuestionPaper ,Question


class TestRegistration(models.Model):
    """
    Stores one unique attempt (registration) by an email for a specific Question Paper, 
    matching the required schema for app_testregistration table.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=False, blank=False, null=False) # Ensure email is NOT blank/null
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    
    address = models.TextField(null=True, blank=True)
    
    question_paper = models.ForeignKey(
        # सुनिश्चित करें कि QuestionPaper model सही जगह से import हो रहा है
        QuestionPaper,
        on_delete=models.CASCADE,
        # related_name को आपके अनुरोधित ब्लॉक के अनुसार 'registrations' रखा गया है।
        related_name="registrations" 
    )
    
    # start_time को आपके अनुरोधित ब्लॉक के अनुसार auto_now_add=True के साथ सेट किया गया है।
    start_time = models.DateTimeField(auto_now_add=True)
    
    is_completed = models.BooleanField(default=False)
    
    # is_evaluated और evaluated_at को आपके अनुरोधित ब्लॉक के अनुसार जोड़ा गया है।
    is_evaluated = models.BooleanField(default=False)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    # अन्य फ़ील्ड्स (score, is_shortlisted, recruitment_drive) हटा दिए गए हैं।

    class Meta:
        # पुराने टेबल नाम से मैच करने के लिए db_table सेट करें।
        db_table = 'app_testregistration'
        # managed=False सेटिंग को बरकरार रखा गया है।
        managed = True
        
        # मुख्य Constraint को बरकरार रखा गया है।
        unique_together = ('email', 'question_paper')

    def __str__(self):
        return f"{self.email} registered for {self.question_paper.title}"


class TestRegistration(models.Model):
    """
    Stores one unique attempt (registration) by an email for a specific Question Paper.
    Matches the existing app_testregistration table schema.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    
    is_shortlisted = models.BooleanField(default=False)
    score = models.FloatField(null=True, blank=True) 
    
    question_paper = models.ForeignKey(
        QuestionPaper,
        on_delete=models.CASCADE,
        related_name="registrations"
    )
    score = models.FloatField(null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    
  
    is_evaluated = models.BooleanField(default=False)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    

    class Meta:
        db_table = 'app_testregistration' 
        
        unique_together = ('email', 'question_paper')

    def __str__(self):
        return f"{self.email} registered for {self.question_paper.title}"


class UserResponse(models.Model):
    """
    Stores the user's answer for a specific question during a test attempt.
    """
    registration = models.ForeignKey(
        TestRegistration, 
        on_delete=models.CASCADE, 
        related_name="responses"
    )
    
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name="user_responses"
    )
    
    user_answer = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(null=True, blank=True)
    
    class Meta:
        unique_together = ('registration', 'question')
        
    def __str__(self):
        return f"Response for Q{self.question.id} by {self.registration.name}"