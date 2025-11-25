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

# class CandidateApplicationForm(forms.ModelForm):
#     """
#     Public-facing form for candidates to apply.
#     Note: We manually add 'candidate_type' in views as it's not a model field.
#     """
    
#     # Temporary field to capture radio button value for validation
#     candidate_type = forms.CharField(required=True, max_length=15) 
    
#     class Meta:
#         model = CandidateApplication
#         fields = [
#             'full_name', 'email', 'phone_number', 
#             'resume_file', 'cover_letter', 'photo_file', 
            
#             # Fields that rely on is_experienced logic in clean()
#             'is_experienced', 'total_experience', 
            
#             # Other New Application Fields
#             'current_ctc', 'expected_ctc', 
#             'current_ctc_rate', 'expected_ctc_rate', 
#             'notice_period', 'skills', 
#             'current_location', 'referral_source',
#             'linked_paper', # Optional: if you pass paper_id in initial data
#         ]
#         widgets = {
#             # ... (Existing widgets)
            
#             # Hiding is_experienced as it's set in clean method
#             'is_experienced': forms.HiddenInput(),
#         }

#     def __init__(self, *args, **kwargs):
#         # We handle linked_paper via initial data, not form input directly
#         self.linked_paper_id = kwargs.pop('linked_paper_id', None) 
#         super().__init__(*args, **kwargs)
        
#         # Manually set required fields' widgets
#         for field in ['full_name', 'email', 'phone_number']:
#              self.fields[field].widget.attrs['class'] = INPUT_CLASSES

#         # Dynamically add the candidate_type field to allow validation
#         self.fields['candidate_type'] = forms.CharField(required=True)
#         # Rename field names to match HTML/JS naming convention for simplicity in POST data
#         self.fields['full_name'].widget.attrs['name'] = 'fullName'
#         self.fields['phone_number'].widget.attrs['name'] = 'mobile'
#         self.fields['resume_file'].widget.attrs['name'] = 'resume'
#         self.fields['photo_file'].widget.attrs['name'] = 'photo'
#         self.fields['skills'].widget.attrs['name'] = 'skills'
#         self.fields['current_location'].widget.attrs['name'] = 'location'
#         self.fields['referral_source'].widget.attrs['name'] = 'referral'
#         self.fields['cover_letter'].widget.attrs['name'] = 'coverLetter'
        
#         self.fields['total_experience'].widget.attrs['name'] = 'experience'
#         self.fields['current_ctc_rate'].widget.attrs['name'] = 'currentCTCRate'
#         self.fields['expected_ctc_rate'].widget.attrs['name'] = 'expectedCTCRate'
#         self.fields['notice_period'].widget.attrs['name'] = 'noticePeriod'

#         # Since we use JavaScript to conditionally hide fields, set them to not required here 
#         # unless it's a field that should always be required if provided, like experience for experienced users
#         self.fields['total_experience'].required = False
#         self.fields['current_ctc'].required = False
#         self.fields['current_ctc_rate'].required = False
#         self.fields['notice_period'].required = False

#     def clean(self):
#         cleaned_data = super().clean()
        
#         # 1. Handle is_experienced flag from radio button (candidateType)
#         candidate_type = self.data.get('candidateType') # Use self.data to get raw POST value
#         is_experienced = (candidate_type == 'experienced')
#         cleaned_data['is_experienced'] = is_experienced 
        
#         # 2. Conditional Validation and cleaning based on is_experienced
#         total_experience = cleaned_data.get('total_experience')

#         if is_experienced:
#             # Enforce required experience check for experienced users
#             if not total_experience or total_experience <= 0:
#                 self.add_error('total_experience', "Total Experience must be greater than 0 for experienced applicants.")
                
#         else:
#              # If Fresher, clear/set optional experienced-only fields to None/0 for clean DB state
#              cleaned_data['total_experience'] = 0.0 # Save as 0 for Fresher
#              cleaned_data['current_ctc'] = None
#              cleaned_data['current_ctc_rate'] = None
#              cleaned_data['notice_period'] = None

#         # Clean photo and resume separately (size/type validation is handled by HTML/JS, here we ensure required status if needed)
        
#         return cleaned_data

#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         # Set linked_paper if available (only applicable if this form is used in a specific context)
#         if self.linked_paper_id:
#              from .models import QuestionPaper # Ensure QuestionPaper is imported
#              instance.linked_paper = QuestionPaper.objects.get(pk=self.linked_paper_id)
        
#         if commit:
#             instance.save()
#         return instance

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

# app/forms.py - Update your CandidateApplicationForm

# app/forms.py - UPDATED CandidateApplicationForm

from django import forms
from .models import CandidateApplication
from django.core.exceptions import ValidationError

# Input Classes (Ensure these are defined in your forms.py)
INPUT_CLASSES = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-primary focus:border-blue-primary sm:text-sm"
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"


# class CandidateApplicationForm(forms.ModelForm):
#     # Hidden field for radio button value (only for validation logic)
#     candidateType = forms.CharField(required=True, max_length=15) 
    
#     class Meta:
#         model = CandidateApplication
#         fields = [
#             'full_name', 'email', 'phone_number', 
#             'is_experienced', 'total_experience', 
#             'current_ctc', 'current_ctc_rate', 'expected_ctc', 'expected_ctc_rate', 
#             'notice_period', 'skills', 'current_location', 'referral_source', 
#             'resume_file', 'photo_file', 'cover_letter', 'linked_paper'
#         ]

#         widgets = {
#             'is_experienced': forms.HiddenInput(),
#             'linked_paper': forms.HiddenInput(),
#         }

#     def __init__(self, *args, **kwargs):
#         # We handle linked_paper via initial data/view, not form input directly
#         self.linked_paper_id = kwargs.pop('linked_paper_id', None) 
#         super().__init__(*args, **kwargs)

#         # 🚨 HTML Field Name Mapping (Crucial for correct data access) 🚨
#         # Django form expects 'full_name', but HTML sends 'fullName'. We fix it by setting the widget's 'name' attribute.
#         self.fields['full_name'].widget.attrs['name'] = 'fullName'
#         self.fields['phone_number'].widget.attrs['name'] = 'mobile'
#         self.fields['resume_file'].widget.attrs['name'] = 'resume'
#         self.fields['photo_file'].widget.attrs['name'] = 'photo'
#         self.fields['skills'].widget.attrs['name'] = 'skills'
#         self.fields['current_location'].widget.attrs['name'] = 'location'
#         self.fields['referral_source'].widget.attrs['name'] = 'referral'
#         self.fields['cover_letter'].widget.attrs['name'] = 'coverLetter'
#         self.fields['total_experience'].widget.attrs['name'] = 'experience'
#         self.fields['current_ctc_rate'].widget.attrs['name'] = 'currentCTCRate'
#         self.fields['expected_ctc_rate'].widget.attrs['name'] = 'expectedCTCRate'
#         self.fields['notice_period'].widget.attrs['name'] = 'noticePeriod'
        
#         # NOTE: 'candidateType' is a custom field for validation, it is NOT in the model Meta.
#         self.fields['candidateType'].widget.attrs['name'] = 'candidateType' 


#         # Ensure Model Fields are required as per HTML (even if using JS validation)
#         for field in ['full_name', 'email', 'phone_number', 'resume_file', 'photo_file']:
#             self.fields[field].required = True 

#         # Set optional fields to not required
#         self.fields['total_experience'].required = False
#         self.fields['current_ctc'].required = False
#         self.fields['current_ctc_rate'].required = False
#         self.fields['expected_ctc'].required = False
#         self.fields['expected_ctc_rate'].required = False
#         self.fields['notice_period'].required = False
#         self.fields['cover_letter'].required = False
#         self.fields['linked_paper'].required = False
        
#         # File field validation (Max size check)
#         self.fields['resume_file'].help_text = "Max 2MB. Allowed: pdf, doc, docx."
#         self.fields['photo_file'].help_text = "Max 1MB. Allowed: png, jpg, jpeg."


#     def clean(self):
#         cleaned_data = super().clean()
        
#         # 1. Handle is_experienced flag from radio button (candidateType)
#         candidate_type = self.data.get('candidateType') # Use self.data to get raw POST value
#         is_experienced = (candidate_type == 'experienced')
#         cleaned_data['is_experienced'] = is_experienced 
        
#         # 2. Conditional Validation for total_experience
#         total_experience = cleaned_data.get('total_experience')

#         if is_experienced:
#             # Enforce required experience check for experienced users
#             if not total_experience:
#                 self.add_error('total_experience', "Total Experience is required for experienced applicants.")
#             elif total_experience < 0.5:
#                  self.add_error('total_experience', "Total Experience must be 0.5 years or more for experienced applicants.")
#         else:
#              # If Fresher, set total_experience to 0.0 and clear experienced-only fields
#              cleaned_data['total_experience'] = 0.0 
#              cleaned_data['current_ctc'] = None
#              cleaned_data['current_ctc_rate'] = None
#              cleaned_data['notice_period'] = None
        
#         # 3. Resume File Validation
#         resume = cleaned_data.get('resume_file')
#         if resume:
#              if resume.size > 2 * 1024 * 1024:
#                 self.add_error('resume_file', "Max file size for Resume is 2MB.")
#              ext = resume.name.split('.')[-1].lower()
#              if ext not in ['pdf', 'doc', 'docx']:
#                  self.add_error('resume_file', "Allowed formats for Resume are pdf, doc, docx.")

#         # 4. Photo File Validation
#         photo = cleaned_data.get('photo_file')
#         if photo:
#              if photo.size > 1 * 1024 * 1024:
#                 self.add_error('photo_file', "Max file size for Photo is 1MB.")
#              ext = photo.name.split('.')[-1].lower()
#              if ext not in ['png', 'jpg', 'jpeg']:
#                  self.add_error('photo_file', "Allowed formats for Photo are png, jpg, jpeg.")
        
#         # 5. Cover Letter word count (Assuming 500 word limit as per UI JS)
#         cover_text = cleaned_data.get('cover_letter', '').strip()
#         word_count = len(cover_text.split()) 
#         if word_count > 500:
#              self.add_error('cover_letter', "Cover letter exceeds 500 words limit.")
        
#         return cleaned_data

#     def save(self, commit=True, linked_paper=None):
#         instance = super().save(commit=False)
        
#         # Set linked_paper if provided (either via initial or passed directly)
#         if linked_paper:
#              instance.linked_paper = linked_paper
        
#         # Set phone_number, email, and full_name for uniqueness check
#         instance.full_name = self.cleaned_data['full_name']
#         instance.email = self.cleaned_data['email'].lower()
#         instance.phone_number = self.cleaned_data['phone_number']

#         # NOTE: recruitment_drive is required in the model, but we might not have it here. 
#         # This view assumes paper_id is the primary link and a recruitment_drive will be 
#         # assigned later, or that the paper *must* be linked to a drive if the drive field 
#         # is made required in the model. Since your model shows `linked_paper` but still
#         # requires `recruitment_drive` (no null/blank=True), we must handle it. 
#         # 💡 BEST FIX: In this specific view, we assume the application is linked to a paper
#         # that *is* part of a drive, or we default to the paper's drive.
#         # Since this is a direct application via paper ID, we can't assume a drive.
#         # Let's ensure the `recruitment_drive` field in `CandidateApplication` model is `null=True, blank=True` 
#         # for these direct-paper applications.

#         if commit:
#             instance.save()
#         return instance
#     class Meta:
#         model = CandidateApplication
#         fields = [
#             'full_name',
#             'email',
#             'phone_number',
#             'is_experienced',
#             'total_experience',
#             'current_ctc',
#             'current_ctc_rate',
#             'expected_ctc',
#             'expected_ctc_rate',
#             'notice_period',
#             'skills',
#             'current_location',
#             'referral_source',
#             'resume_file',
#             'photo_file',
#             'cover_letter'
#         ]
        
#     def __init__(self, *args, **kwargs):
#         # Remove linked_paper_id if it was being passed
#         self.linked_paper_id = kwargs.pop('linked_paper_id', None)
#         super().__init__(*args, **kwargs)
        
#         # Make certain fields optional
#         self.fields['total_experience'].required = False
#         self.fields['current_ctc'].required = False
#         self.fields['expected_ctc'].required = False
#         self.fields['current_ctc_rate'].required = False
#         self.fields['expected_ctc_rate'].required = False
#         self.fields['notice_period'].required = False
#         self.fields['skills'].required = False
#         self.fields['current_location'].required = False
#         self.fields['referral_source'].required = False
#         self.fields['photo_file'].required = False
#         self.fields['cover_letter'].required = False
        
#     def clean(self):
#         cleaned_data = super().clean()
        
#         # If experienced, validate experience-related fields
#         is_experienced = cleaned_data.get('is_experienced')
#         if is_experienced:
#             total_exp = cleaned_data.get('total_experience')
#             if not total_exp or total_exp < 0:
#                 self.add_error('total_experience', 'Please enter valid experience for experienced candidates.')
        
#         return cleaned_data


# app/forms.py (Hypothetical Update)
#... (Rest of the imports and form definition)

class CandidateApplicationForm(forms.ModelForm):
    # candidateType ko form mein ek temporary field ke roop mein add karein
    candidateType = forms.CharField(max_length=20, required=True)

    class Meta:
        model = CandidateApplication
        fields = (
            'full_name', 'email', 'phone_number', 'total_experience', 
            'current_ctc', 'current_ctc_rate', 'expected_ctc', 'expected_ctc_rate',
            'skills', 'current_location', 'referral_source', 'resume_file', 
            'photo_file', 'cover_letter', 'candidateType' # Temporary field
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
             instance.total_experience = None
             instance.current_ctc = None
             # ... (other experienced fields ko bhi clear karein) ...
        
        if commit:
            instance.save()
        return instance