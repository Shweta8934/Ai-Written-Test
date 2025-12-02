# """
# WSGI config for project_name project.

# It exposes the WSGI callable as a module-level variable named ``application``.

# For more information on this file, see
# https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
# """

# import os

# from django.core.wsgi import get_wsgi_application

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_test.settings")

# application = get_wsgi_application()
"""
WSGI config for project_name project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_test.settings")

application = get_wsgi_application()

# --- Auto-run migrations on startup (temporary fix for production free tier) ---
from django.core.management import call_command
try:
    # Run all unapplied migrations
    call_command('migrate', interactive=False, run_syncdb=True)
    print("✅ Migrations applied successfully")
except Exception as e:
    print(f"⚠️ Migration error: {e}")
