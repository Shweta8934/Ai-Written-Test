# app/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth import get_user_model
from .models import User, UserProfile
from .models import Department, Skill
from .models import Section
from .models import QuestionPaper
import re

User = get_user_model()
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class LoginForm(AuthenticationForm):
    """
    Custom login form to add specific validation for email and password fields.
    """

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email address",
                "autofocus": True,
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "minlength": "8",
                "maxlength": "64",
                "autocomplete": "current-password",
            }
        ),
    )

    # def clean_username(self):
    #     username = self.cleaned_data.get("username")
    #     if username and not username.strip():
    #         raise ValidationError(
    #             "This field cannot be blank or contain only whitespace.",
    #             code="whitespace_username",
    #         )
    #     return username.strip()
    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()

        # Find user case-insensitive
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise ValidationError("This email is not registered.", code="invalid")

        # replace with actual stored username casing
        self.cleaned_data["username"] = user.username

        return user.username

    def clean_password(self):
        """
        Adds server-side validation for the password field.
        """
        password = self.cleaned_data.get("password")
        if password and not password.strip():
            raise ValidationError(
                "Password cannot contain only whitespace.", code="whitespace_password"
            )

        password = password.strip()

        if len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long.", code="min_length"
            )
        # ✨ YAHAN BADLAV KIYA GAYA HAI ✨
        if len(password) > 64:
            raise ValidationError(
                "Password is too long. Please use a password with 64 characters or less.",
                code="max_length",
            )

        return password


INPUT_CLASSES = (
    "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-blue-primary "
    "focus:border-blue-primary sm:text-sm"
)
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"


# -------------------- USER REGISTRATION FORM --------------------
class UserRegistrationForm(BaseUserCreationForm):
    """
    Handles new user creation with consistent Tailwind styling.
    """

    email = forms.EmailField(
        required=True, help_text="A valid email address is required."
    )
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if field.label:
                placeholder_text = f"Enter your {field.label.lower()}..."
            else:
                placeholder_text = f"Enter {field_name.replace('_', ' ')}..."

            field.widget.attrs.update(
                {"class": INPUT_CLASSES, "placeholder": placeholder_text}
            )

    def clean_email(self):
        """
        Validates that the email is not already registered.
        """
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Email already registered. Please login.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].lower()
        if commit:
            user.save()
        return user

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")


# -------------------- USER PROFILE FORM --------------------
class UserProfileRegistrationForm(forms.ModelForm):
    """
    Handles the user profile fields (phone, address) with same styling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.label:
                placeholder_text = f"Enter your {field.label.lower()}..."
            else:
                placeholder_text = f"Enter {field_name.replace('_', ' ')}..."

            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update(
                    {
                        "class": TEXTAREA_CLASSES,
                        "rows": "1",
                        "placeholder": placeholder_text,
                    }
                )
            else:
                field.widget.attrs.update(
                    {"class": INPUT_CLASSES, "placeholder": placeholder_text}
                )

    class Meta:
        model = UserProfile
        fields = ("phone_number", "address")


from django import forms
from .models import Department, Section


class DepartmentForm(forms.ModelForm):
    sections = forms.ModelMultipleChoiceField(
        queryset=Section.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={
            "required": "Please select at least one section for the department."
        },
    )

    class Meta:
        model = Department
        fields = ["name", "sections"]

    def clean_name(self):
        """
        Custom validation to prevent ONLY exact duplicate department names (case-insensitive).
        """
        name = self.cleaned_data.get("name", "").strip()

        # ✨ YEH NAYA AUR BEHTAR LOGIC HAI ✨
        # __iexact ka matlab hai: case-insensitive (chote/bade letters se farak nahi padta) EXACT match.
        query = Department.objects.filter(name__iexact=name)

        # Agar form edit ho raha hai, toh khud ko check na karein
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)

        # Agar is naam ka koi department pehle se hai, toh error dein
        if query.exists():
            raise forms.ValidationError(
                "A department with this exact name already exists. Please use a different name."
            )

        return name


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = "__all__"


text_input_class = "w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-theme-primary focus:border-theme-primary"


from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth import get_user_model
from .models import User, UserProfile
from .models import Department, Skill
from .models import Section
from .models import QuestionPaper

User = get_user_model()
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError




text_input_class = "w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-theme-primary focus:border-theme-primary"


class QuestionPaperEditForm(forms.ModelForm):
    
    job_title = forms.CharField(
        min_length=3,
        max_length=30,  
        widget=forms.TextInput(attrs={"class": text_input_class}),
    )

    class Meta:
        model = QuestionPaper
        fields = [
            "job_title",
            "title",
            "department_name",
            "duration",
            "min_exp",
            "max_exp",
            "skills_list",
            "cutoff_score",
        ]
        widgets = {
            "job_title": forms.TextInput(attrs={"class": text_input_class}),
            "title": forms.TextInput(attrs={"class": text_input_class}),
            "department_name": forms.TextInput(attrs={"class": text_input_class}),
            "duration": forms.NumberInput(
                attrs={"class": text_input_class, "min": "1"}
            ),
            "min_exp": forms.NumberInput(
                attrs={"class": text_input_class, "id": "min_exp_input", "min": "0"}
            ),
            "max_exp": forms.NumberInput(
                attrs={"class": text_input_class, "id": "max_exp_input", "min": "0"}
            ),
            "skills_list": forms.TextInput(
                attrs={
                    "class": f"{text_input_class} skill-autocomplete-input",  
                    "placeholder": "e.g., Python, Django, JavaScript",
                    "autocomplete": "off",  
                }
            ),
        }

  
    def clean_job_title(self):
        """
        Adds custom validation for the job_title field.
        Ensures the job title is a string with a length between 3 and 30 characters.
        """
        job_title = self.cleaned_data.get("job_title", "").strip()

        if len(job_title) < 3:
            raise forms.ValidationError("Job title must be at least 3 characters long.")

        if len(job_title) > 30:  
            raise forms.ValidationError(
                "Job title cannot be longer than 30 characters."  
            )

        if not re.search(r"[a-zA-Z]", job_title):
            raise forms.ValidationError("Job title must contain letters.")

        return job_title


text_input_class = "w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-theme-primary focus:border-theme-primary"


SKILL_ALIASES = {
    "reactjs": "react",
    "vuejs": "vue",
    "node js": "nodejs",
    "angular js": "angular",
}


from django import forms
from .models import Skill

SKILL_ALIASES = {
    "reactjs": "react",
    "vuejs": "vue",
    "node js": "nodejs",
    "angular js": "angular",
}


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        # ✅ CHANGE: 'is_active' ko yahan add karein
        fields = ["name", "is_active"]

    def clean_name(self):
        """
        Custom validation for the skill name.
        1. Converts the name to lowercase.
        2. Checks for aliases (e.g., reactjs -> react).
        3. Checks for case-insensitive uniqueness.
        """
        name = self.cleaned_data.get("name")
        if name:
            # self.instance ko check karna zaroori hai update ke time existing name ko allow karne ke liye
            if self.instance and self.instance.name.lower() == name.strip().lower():
                return name  # Agar naam change nahi hua hai, to validation skip karein

            cleaned_name = name.strip().lower()

            if cleaned_name in SKILL_ALIASES:
                cleaned_name = SKILL_ALIASES[cleaned_name]

            if Skill.objects.filter(name__iexact=cleaned_name).exists():
                raise forms.ValidationError(
                    "This skill already exists. Please use the existing one."
                )

            return cleaned_name
        return name


text_input_class = "w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-theme-primary focus:border-theme-primary"


from django import forms


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        required=True,
        error_messages={
            "required": "Email address is required.",
            "invalid": "Please enter a valid email address.",
        },
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        blocked_domains = ["test.com", "example.com", "mailinator.com", "fake.com"]
        domain = email.split("@")[-1]
        if domain in blocked_domains:
            raise forms.ValidationError(
                "Email domain not allowed. Please use your real email."
            )
        return email

from django.core.exceptions import ValidationError

class InviteCandidateForm(forms.Form):
    """
    Form for inviting a candidate via email.
    """

    email = forms.EmailField(
        label="Candidate Email",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter candidate's email address",
                "class": INPUT_CLASSES, 
            }
        ),
        error_messages={
            "required": "The candidate's email address is required.",
            "invalid": "Please enter a valid email address.",
        },
    )

    paper_id = forms.IntegerField(widget=forms.HiddenInput(), required=True)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        
        return email


class SectionForm(forms.ModelForm):
    """Form to create new sections."""
    class Meta:
        model = Section
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-theme-button",
                "placeholder": "Enter section name",
            })
        }
    
    def clean_name(self):
        """Validate that section name doesn't already exist."""
        name = self.cleaned_data.get("name", "").strip()
        if Section.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("This section already exists.")
        return name


# ============ RECRUITMENT DRIVE FORMS ============

from django import forms
from .models import RecruitmentDrive, CandidateApplication

class RecruitmentDriveForm(forms.ModelForm):
    """Form for creating/editing recruitment drives"""
    
    test_papers = forms.ModelMultipleChoiceField(
        queryset=QuestionPaper.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select test papers for multi-round assessments"
    )
    
    class Meta:
        model = RecruitmentDrive
        fields = [
            'title', 'position', 'description', 'department',
            'total_positions', 'application_start_date', 'application_end_date',
            'expected_joining_date', 'require_test', 'test_papers',
            'auto_close_on_full', 'link_expiry_date'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'position': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 4}),
            'total_positions': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': 1}),
            'application_start_date': forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
            'application_end_date': forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
            'expected_joining_date': forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
            'link_expiry_date': forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('application_start_date')
        end_date = cleaned_data.get('application_end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data



class CandidateStageUpdateForm(forms.Form):
    """Form for recruiters to update candidate stage"""
    
    new_stage = forms.ChoiceField(
        choices=CandidateApplication.CandidateStage.choices,
        widget=forms.Select(attrs={'class': INPUT_CLASSES})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 3, 'placeholder': 'Add notes (optional)'})
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 2, 'placeholder': 'Reason for rejection (if applicable)'})
    )


class BulkStageUpdateForm(forms.Form):
    """Form for bulk updating candidate stages"""
    
    candidate_ids = forms.CharField(widget=forms.HiddenInput())
    new_stage = forms.ChoiceField(
        choices=CandidateApplication.CandidateStage.choices,
        widget=forms.Select(attrs={'class': INPUT_CLASSES})
    )


from django import forms
from .models import CandidateApplication
from django.core.exceptions import ValidationError

# Input Classes (Ensure these are defined in your forms.py)
INPUT_CLASSES = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-primary focus:border-blue-primary sm:text-sm"
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"


# app/forms.py (Add this form)

from django import forms
from .models import InterviewEvaluation

class InterviewEvaluationForm(forms.ModelForm):
    # Hidden fields to pass necessary IDs
    application_id = forms.IntegerField(widget=forms.HiddenInput())
    round_name = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = InterviewEvaluation
        fields = [
            'score', 
            'feedback', 
            'is_passed', 
            'communication_score', 
            'domain_knowledge_score', 
            'leadership_score'
        ]
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 4}),
        }

# class CandidateApplicationForm(forms.ModelForm):
#     # candidateType ko form mein ek temporary field ke roop mein add karein
#     candidateType = forms.CharField(max_length=20, required=True)

#     class Meta:
#         model = CandidateApplication
#         fields = (
#             'full_name', 'email', 'phone_number', 'total_experience', 
#             'current_ctc', 'current_ctc_rate', 'expected_ctc', 'expected_ctc_rate',
#             'skills', 'current_location', 'referral_source', 'resume_file', 
#             'photo_file', 'cover_letter', 'candidateType' # Temporary field
#         )
        
#     def clean(self):
#         cleaned_data = super().clean()
        
#         # is_experienced ko calculate karein
#         candidate_type = cleaned_data.get('candidateType')
#         is_experienced = (candidate_type == 'experienced')
        
#         # is_experienced ko cleaned_data mein inject karein
#         cleaned_data['is_experienced'] = is_experienced 

#         # Experienced logic
#         if is_experienced:
#             total_experience = cleaned_data.get('total_experience')
#             if not total_experience or total_experience <= 0:
#                  # Ensure total_experience is validated if experienced
#                  self.add_error('total_experience', 'Total Experience is required for experienced applicants.')
#         else:
#             # Fresher ke liye total_experience ko 0 ya None set karein
#             cleaned_data['total_experience'] = None
            
#         # Optional: candidateType ko cleaned_data se hata dein agar model mein yeh field nahi hai
#         del cleaned_data['candidateType'] 
        
#         return cleaned_data

#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         # Cleaned data se is_experienced ki calculated value ko instance mein copy karein
#         instance.is_experienced = self.cleaned_data.get('is_experienced')
        
#         # Agar experienced nahi hai, toh optional fields ko clear karein (safeside ke liye)
#         if not instance.is_experienced:
#              instance.total_experience = None
#              instance.current_ctc = None
#              # ... (other experienced fields ko bhi clear karein) ...
        
#         if commit:
#             instance.save()
#         return instance
from django import forms
from .models import CandidateApplication # मान लें कि यह इम्पोर्टेड है
from django.core.exceptions import ValidationError

# ... (INPUT_CLASSES और TEXTAREA_CLASSES यहाँ परिभाषित हैं)

class CandidateApplicationForm(forms.ModelForm):
    # candidateType ko form mein ek temporary field ke roop mein add karein
    candidateType = forms.CharField(max_length=20, required=True)

    class Meta:
        model = CandidateApplication
        fields = (
            'full_name', 'email', 'phone_number', 'total_experience', 
            'current_ctc', 'current_ctc_rate', 'expected_ctc', 'expected_ctc_rate',
            'skills', 'current_location', 'referral_source', 'resume_file', 
            'photo_file',  # ✨ 1. photo_file को Meta में शामिल किया गया
            'cover_letter', 'candidateType' 
        )
        
    def clean(self):
        cleaned_data = super().clean()
        
        # is_experienced ko calculate karein
        candidate_type = cleaned_data.get('candidateType')
        is_experienced = (candidate_type == 'experienced')
        
        # is_experienced ko cleaned_data mein inject karein
        cleaned_data['is_experienced'] = is_experienced 

        # Experienced logic
        if is_experienced:
            total_experience = cleaned_data.get('total_experience')
            if not total_experience or total_experience <= 0:
                 # Ensure total_experience is validated if experienced
                 self.add_error('total_experience', 'Total Experience is required for experienced applicants.')
        else:
            # Fresher ke liye total_experience ko 0 ya None set karein
            cleaned_data['total_experience'] = None
            
        # Optional: candidateType ko cleaned_data se hata dein agar model mein yeh field nahi hai
        del cleaned_data['candidateType'] 
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Cleaned data se is_experienced ki calculated value ko instance mein copy karein
        instance.is_experienced = self.cleaned_data.get('is_experienced')
        
        # Agar experienced nahi hai, toh optional fields ko clear karein (safeside ke liye)
        if not instance.is_experienced:
             # ✨ 2. Fresher होने पर सभी Experience/CTC फ़ील्ड्स को None सेट करें
             instance.total_experience = None
             instance.current_ctc = None
             instance.current_ctc_rate = None
             instance.expected_ctc = None
             instance.expected_ctc_rate = None
             instance.skills = None
             instance.current_location = None
             instance.referral_source = None
             
             # Note: resume_file, photo_file, और cover_letter freshers के लिए भी
             # वैकल्पिक (Optional) रहते हैं क्योंकि वे मॉडल में null=True हैं।
        
        if commit:
            instance.save()
        return instance


# app/forms.py

from django import forms
from .models import InterviewEvaluation, CandidateApplication
from django.core.exceptions import ValidationError

# Input Classes (Forms.py में पहले से परिभाषित)
INPUT_CLASSES = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-primary focus:border-blue-primary sm:text-sm"
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"


# -------------------- BASE EVALUATION FORM --------------------
class BaseEvaluationForm(forms.ModelForm):
    """
    सभी मूल्यांकन (Evaluation) फॉर्म के लिए बेस क्लास, जिसमें मुख्य स्कोर और निर्णय शामिल हैं।
    """
    # Hidden fields to pass necessary IDs (Optional, can be passed in view context)
    application_id = forms.IntegerField(widget=forms.HiddenInput())
    round_name = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = InterviewEvaluation
        fields = [
            'score',
            'feedback',
            'is_passed',
            # Base fields for soft skills/general interview
            'communication_score',
        ]
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 4, 'class': TEXTAREA_CLASSES}),
            'score': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': 0, 'max': 100}),
            'communication_score': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': 0, 'max': 100}),
            # is_passed (Checkbox) widget HTML में ही है
        }
    
    # Optional: common cleanup/validation can go here

# -------------------- ROUND-SPECIFIC FORMS --------------------

# class GroupDiscussionEvaluationForm(BaseEvaluationForm):
#     """GD के लिए: Communication और Leadership पर ज़ोर।"""
#     class Meta(BaseEvaluationForm.Meta):
#         fields = BaseEvaluationForm.Meta.fields + [
#             'leadership_score',  # Leadership/Teamwork/Initiative Score
#         ]


# class TechnicalRound1EvaluationForm(BaseEvaluationForm):
#     """Tech R1 के लिए: Basic Programming, Logical, Cultural Fit आदि।"""
#     # Custom fields for R1 metrics (100 में से स्कोर)
#     basic_programming_score = forms.IntegerField(
#         min_value=0, max_value=100, required=True, label="Basic Programming",
#         widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
#     )
#     logical_score = forms.IntegerField(
#         min_value=0, max_value=100, required=True, label="Logical Reasoning",
#         widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
#     )
#     cultural_fit_score = forms.IntegerField(
#         min_value=0, max_value=100, required=True, label="Cultural Fit / Values",
#         widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
#     )
#     awareness_score = forms.IntegerField(
#         min_value=0, max_value=100, required=True, label="Awareness of New Tech",
#         widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
#     )

#     class Meta(BaseEvaluationForm.Meta):
#         fields = BaseEvaluationForm.Meta.fields + [
#             # Technical fields for R1
#             'basic_programming_score',
#             'logical_score',
#             'cultural_fit_score',
#             'awareness_score',
#             'domain_knowledge_score', # Domain knowledge score को भी R1 में रखें
#         ]
# app/forms.py (लगभग line 655 के आसपास)

# ... (बाकी classes के बाद)

# -------------------- ROUND-SPECIFIC FORMS (GD) --------------------

class GroupDiscussionEvaluationForm(BaseEvaluationForm):
    """GD के लिए: Communication, Leadership, और Confidence पर ज़ोर।"""
    
    # 💡 आपका पहला पॉइंट: Communication (Base Form से लिया गया)
    # communication_score already BaseEvaluationForm में है
    
    # 💡 आपका दूसरा पॉइंट: Team Player/Collaboration (Leadership Score का उपयोग करें)
    # leadership_score already BaseEvaluationForm में है (इसे Team Player की तरह उपयोग करें)
    
    # 💡 आपका तीसरा पॉइंट: Confidence/Assertiveness/Presentation
    confidence_score = forms.IntegerField(
        min_value=0, max_value=100, required=True, label="Confidence / Assertiveness",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )
    
    # 💡 Teamwork/Collaboration के लिए एक अलग फील्ड जोड़ें (यदि leadership focus न हो)
    collaboration_score = forms.IntegerField(
        min_value=0, max_value=100, required=True, label="Teamwork / Collaboration",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )

    class Meta(BaseEvaluationForm.Meta):
        fields = BaseEvaluationForm.Meta.fields + [
            'leadership_score',        # How they lead or organize the discussion
            'confidence_score',        # Assertiveness and presentation style
            'collaboration_score',     # How they include others / are team players
        ]
# app/forms.py में बदलाव करें

# ... (Original code) ...
class TechnicalRound1EvaluationForm(BaseEvaluationForm):
    """Tech R1 के लिए: Basic Programming, Logical, Cultural Fit आदि।"""
    # Custom fields for R1 metrics (100 में से स्कोर)
    
    # 🟢 FIXED: '...' को हटाकर keyword arguments का उपयोग करें
    basic_programming_score = forms.IntegerField(
        min_value=0, 
        max_value=100, 
        required=True, 
        label="Basic Programming",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )
    logical_score = forms.IntegerField(
        min_value=0, 
        max_value=100, 
        required=True, 
        label="Logical Reasoning",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )
    cultural_fit_score = forms.IntegerField(
        min_value=0, 
        max_value=100, 
        required=True, 
        label="Cultural Fit / Values",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )
    awareness_score = forms.IntegerField(
        min_value=0, 
        max_value=100, 
        required=True, 
        label="Awareness of New Tech",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )

    class Meta(BaseEvaluationForm.Meta):
        fields = BaseEvaluationForm.Meta.fields + [
            # Technical fields for R1
            'basic_programming_score',
            'logical_score',
            'cultural_fit_score',
            'awareness_score',
            'domain_knowledge_score', # Domain knowledge score को भी R1 में रखें
        ]
# आप R2 के लिए भी इसी तरह एक नया फॉर्म बना सकते हैं
class TechnicalRound2EvaluationForm(TechnicalRound1EvaluationForm):
    """Tech R2 के लिए: R1 के साथ-साथ System Design, Problem Solving पर ज़ोर।"""
    # R2 के लिए अतिरिक्त / संशोधित fields
    system_design_score = forms.IntegerField(
        min_value=0, max_value=100, required=False, label="System Design / Architecture",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )
    advanced_problem_solving_score = forms.IntegerField(
        min_value=0, max_value=100, required=False, label="Advanced Problem Solving",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )

    class Meta(TechnicalRound1EvaluationForm.Meta):
        fields = TechnicalRound1EvaluationForm.Meta.fields + [
            'system_design_score',
            'advanced_problem_solving_score',
        ]
        # यदि आप R1 के fields हटाना चाहते हैं, तो उन्हें हटा दें और फिर नए fields जोड़ें।
        # इस उदाहरण में, हम उन्हें retained कर रहे हैं।


class HREvaluationForm(BaseEvaluationForm):
    """HR Round के लिए: Personality, Motivation, Expectation पर ज़ोर।"""
    # Custom fields for HR metrics
    personality_score = forms.IntegerField(
        min_value=0, max_value=100, required=True, label="Personality / Attitude",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )
    motivation_score = forms.IntegerField(
        min_value=0, max_value=100, required=True, label="Motivation / Intent",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )
    salary_expectation_fit_score = forms.IntegerField(
        min_value=0, max_value=100, required=False, label="Salary Expectation Fit",
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES})
    )

    class Meta(BaseEvaluationForm.Meta):
        fields = BaseEvaluationForm.Meta.fields + [
            'personality_score',
            'motivation_score',
            'salary_expectation_fit_score',
            'leadership_score', # Leadership को HR में भी रख सकते हैं
        ]

# पुराने InterviewEvaluationForm को अब हटा सकते हैं या इसे एक alias बना सकते हैं।
# यदि आप इसे रखना चाहते हैं, तो इसे BaseEvaluationForm के समान बनाएं।
InterviewEvaluationForm = BaseEvaluationForm