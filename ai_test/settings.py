# settings.py - Production Ready Configuration for Render

from pathlib import Path
import os
import environ
import dj_database_url # ⭐ FIX 1: Render Database URL parsing ke liye
from dotenv import load_dotenv

# Base Directory Setup
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables reading
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-rf^i_@h*%*-6bz7n5djy8d2r26z+e!y-s4=h2g83pv=uptw)gk"), # Fallback
    # AI Keys
    OPENAI_API_KEY=(str, ""),
    GEMINI_API_KEY=(str, ""),
    # Email Settings
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_HOST=(str, ""),
    EMAIL_PORT=(int, 587),
    DEFAULT_FROM_EMAIL=(str, ""),
)

# .env file ko sirf locally read karein
if not os.environ.get('RENDER'):
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    
# Core Security Settings
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")

# ----------------------------------------------------
# 1. HOSTS & SECURITY (Production Fixes)
# ----------------------------------------------------
if not DEBUG:
    # Render automatically sets this
    ALLOWED_HOSTS = [env('ALLOWED_HOSTS', default='your-render-app-domain.onrender.com')]
    # Required for production security
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # 💡 FIX 2: XFrameOptionsMiddleware ko hatana zaroori hai agar aap Embeds use kar rahe hain
    # Jaise aapki file mein tha, hum isse 'SAMEORIGIN' par set kar denge agar ye nahi hata
    X_FRAME_OPTIONS = 'SAMEORIGIN'
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "192.168.1.10", "10.0.0.42", env('ALLOWED_HOSTS', default='')]

# Application definition (UNCHANGED)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.humanize',
    "app",
    "user_tests",
    "widget_tweaks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # ADD THIS
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # "django.middleware.clickjacking.XFrameOptionsMiddleware", # Isse hamesha rehne dein ya 'SAMEORIGIN' par set karein
]
# ... (ROOT_URLCONF and TEMPLATES UNCHANGED) ...

# ----------------------------------------------------
# 2. DATABASE CONFIGURATION (Render Fix)
# ----------------------------------------------------
# ⭐ FIX 3: Database ko DATABASE_URL se load karein
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL', default='postgres://postgres:12345@localhost:5432/aiTest'),
        conn_max_age=600,
        ssl_require=True # Render par SSL zaroori hai
    )
}
# Agar Render par deployed hai toh DATABASE_URL ko force karein:
if 'DATABASE_URL' in os.environ:
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600,
        ssl_require=True
    )

# ----------------------------------------------------
# 3. EMAIL CONFIGURATION (Fix for Invitation Not Sent)
# ----------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')          
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_USE_TLS = True 
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

# ----------------------------------------------------
# 4. AI / API KEYS
# ----------------------------------------------------
OPENAI_API_KEY = env("OPENAI_API_KEY")
GEMINI_API_KEY = env("GEMINI_API_KEY")

# ----------------------------------------------------
# 5. STATIC FILES (Render/Whitenoise Fix)
# ----------------------------------------------------
# ⭐ FIX 4: Static files ko production ke liye configure karein
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Locally use this for development
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
# Default primary key field type (UNCHANGED)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Note: Remember to install 'dj-database-url' and 'psycopg2-binary'