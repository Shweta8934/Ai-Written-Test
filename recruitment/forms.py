# recruitment/forms.py
from django import forms
from .models import JobPost, RoundFeedback
from django.core.exceptions import ValidationError

INPUT_CLASSES = (
    "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-blue-primary "
    "focus:border-blue-primary sm:text-sm"
)
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"

from django import forms
from .models import JobPost, RoundFeedback 
from django.core.exceptions import ValidationError

INPUT_CLASSES = (
    "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-blue-primary "
    "focus:border-blue-primary sm:text-sm"
)
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"


from django import forms
from .models import JobPost, RoundFeedback
from django.core.exceptions import ValidationError

INPUT_CLASSES = (
    "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-blue-primary "
    "focus:border-blue-primary sm:text-sm"
)
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = [
        
            'title', 'department', 'location', 'job_type',
            
        
            'experience_min', 'experience_max', 'skills_required', 'positions_available',
            
           
            'total_rounds', 'pay_scale', 'end_date',
            
            'description', 'question_paper', 'status', 
           
        ]
        widgets = {
            # Job Details
            'title': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Job Title (e.g., Senior Django Developer)'}),
            'department': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Department (e.g., Engineering, Sales)'}),
            'location': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'City, State or Remote'}),
            'job_type': forms.Select(attrs={'class': INPUT_CLASSES}),
            
            # Requirements
            'experience_min': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Experience Min (Years)', 'min': 0}),
            'experience_max': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Experience Max (Years)', 'min': 0}),
            'skills_required': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Python, Django, React (comma separated)'}), 
            'positions_available': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Number of Openings', 'min': 1}),

           
            'total_rounds': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Total Interview Rounds', 'min': 1}),
            'pay_scale': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'e.g., 8LPA - 12LPA or Negotiable'}),
            'end_date': forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
            
            
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 4, 'placeholder': 'Detailed Job Description and Responsibilities'}),
        
            'status': forms.Select(attrs={'class': INPUT_CLASSES}),
        }
        
    def clean_experience_max(self):
        min_exp = self.cleaned_data.get('experience_min')
        max_exp = self.cleaned_data.get('experience_max')
        if max_exp is not None and min_exp is not None and max_exp < min_exp:
            raise ValidationError("Maximum experience cannot be less than Minimum experience.")
        return max_exp



class RoundFeedbackForm(forms.ModelForm):

    candidate_id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = RoundFeedback
      
        fields = ['score', 'comments', 'recommendation']
        widgets = {
            'score': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': 0, 'max': 10, 'placeholder': 'Score (0-10)'}),
            'comments': forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 3, 'placeholder': 'Detailed Feedback/Notes'}),
            'recommendation': forms.RadioSelect(choices=RoundFeedback.RECOMMENDATION_CHOICES),
        }


