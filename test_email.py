import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_test.settings")
django.setup()
from django.core.mail import send_mail
from django.conf import settings
print("EMAIL HOST:", settings.EMAIL_HOST_USER)
try:
    send_mail("Test", "Test", settings.DEFAULT_FROM_EMAIL, ["test@example.com"])
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
