# user_tests/forms.py

from django import forms
from .models import TestRegistration 



INPUT_CLASSES = (
    "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-blue-primary "
    "focus:border-blue-primary sm:text-sm"
)
TEXTAREA_CLASSES = f"{INPUT_CLASSES} resize-y"


class TestRegistrationForm(forms.ModelForm):
    """
    Candidate registration form for test attempt tracking. (MOVED HERE)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.label:
                placeholder_text = f"Enter your {field.label.lower()}"
            else:
                placeholder_text = f"Enter {field_name.replace('_', ' ')}"

            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update(
                    {
                        "class": TEXTAREA_CLASSES,
                        "rows": "3",
                        "placeholder": placeholder_text,
                    }
                )
            else:
                field.widget.attrs.update(
                    {"class": INPUT_CLASSES, "placeholder": placeholder_text}
                )

    class Meta:
        model = TestRegistration
        
        fields = ['name', 'email', 'phone_number', 'address'] 
        
        labels = {
            'phone_number': 'Phone Number',
        }
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email or email.strip() == "":
            raise forms.ValidationError("Email address cannot be empty.")
        return email.strip()