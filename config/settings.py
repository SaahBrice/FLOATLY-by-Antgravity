"""
Django settings for Floatly project.

Floatly - Digital Logbook for Mobile Money Agents in Cameroon
Built with: Django + TailwindCSS + HTMX + AlpineJS
"""

import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)

# Read .env file
environ.Env.read_env(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # For formatting numbers (CFA amounts)
    'django.contrib.sites',     # Required by allauth
]

THIRD_PARTY_APPS = [
    'django_htmx',              # HTMX integration
    'compressor',               # CSS/JS compression
    'crispy_forms',             # Better form rendering
    'crispy_tailwind',          # Tailwind CSS for crispy forms
    'django_extensions',        # Useful dev tools
    'pwa',                      # Progressive Web App support
    'allauth',                  # Django-allauth for social auth
    'allauth.account',          # Account management
    'allauth.socialaccount',    # Social account support
    'allauth.socialaccount.providers.google',  # Google OAuth
]

LOCAL_APPS = [
    'core',                     # Main application
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Site ID for django.contrib.sites (required by allauth)
SITE_ID = 1


# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files efficiently
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',  # HTMX middleware
    'allauth.account.middleware.AccountMiddleware',  # Allauth middleware
]

ROOT_URLCONF = 'config.urls'


# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# =============================================================================
# DATABASE
# =============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Douala'  # Cameroon timezone

USE_I18N = True

USE_TZ = True


# =============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise for efficient static file serving
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]


# =============================================================================
# MEDIA FILES (User Uploads - Receipt Photos, etc.)
# =============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model (email-based authentication)
AUTH_USER_MODEL = 'core.User'


# =============================================================================
# CRISPY FORMS (TailwindCSS)
# =============================================================================

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'


# =============================================================================
# DJANGO COMPRESSOR
# =============================================================================

COMPRESS_ENABLED = True
COMPRESS_CSS_HASHING_METHOD = 'content'


# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = 'Floatly <noreply@floatly.cm>'


# =============================================================================
# PUSH NOTIFICATIONS (Web Push / VAPID)
# =============================================================================

VAPID_PUBLIC_KEY = env('VAPID_PUBLIC_KEY', default='')
VAPID_PRIVATE_KEY = env('VAPID_PRIVATE_KEY', default='')
VAPID_ADMIN_EMAIL = env('VAPID_ADMIN_EMAIL', default='admin@floatly.cm')


# =============================================================================
# PWA (Progressive Web App) SETTINGS
# =============================================================================

PWA_APP_NAME = 'Floatly'
PWA_APP_DESCRIPTION = 'Digital logbook for mobile money agents'
PWA_APP_THEME_COLOR = '#1e40af'  # Blue-800
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'portrait'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_ICONS = [
    {
        'src': '/static/images/icon-192x192.png',
        'sizes': '192x192',
        'type': 'image/png'
    },
    {
        'src': '/static/images/icon-512x512.png',
        'sizes': '512x512',
        'type': 'image/png'
    }
]
PWA_APP_ICONS_APPLE = [
    {
        'src': '/static/images/icon-192x192.png',
        'sizes': '192x192',
        'type': 'image/png'
    }
]
PWA_APP_SPLASH_SCREEN = [
    {
        'src': '/static/images/splash-640x1136.png',
        'media': '(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)'
    }
]
PWA_SERVICE_WORKER_PATH = BASE_DIR / 'static' / 'js' / 'serviceworker.js'


# =============================================================================
# SECURITY SETTINGS (Enable in Production)
# =============================================================================

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'floatly.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
(BASE_DIR / 'logs').mkdir(exist_ok=True)


# =============================================================================
# AUTHENTICATION SETTINGS
# =============================================================================

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Login/Logout URLs
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# Session settings
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days for "remember me"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# =============================================================================
# DJANGO-ALLAUTH SETTINGS
# =============================================================================

# Email is the primary identifier, not username
ACCOUNT_LOGIN_METHODS = {'email'}  # New syntax for allauth 0.58+
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# Email verification is mandatory
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1  # 24 hours

# Registration settings
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_UNIQUE_EMAIL = True

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Google already verified
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_LOGIN_ON_GET = True

# Custom adapter paths (we'll create these)
ACCOUNT_ADAPTER = 'core.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'core.adapters.CustomSocialAccountAdapter'

# Google OAuth settings (configured via environment or admin)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}

# Use console email backend for development
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {pathname}:{lineno} {funcName} [{process:d}:{thread:d}] {message}',
            'style': '{',
        },
        'standard': {
            'format': '{levelname} {asctime} {filename}:{lineno} {funcName} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {filename}:{lineno} {message}',
            'style': '{',
        },
    },
    
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    
    'handlers': {
        # Console handler - for development
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        
        # Main log file - all app logs
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'floatly.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        
        # Error log file - only errors and above
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        
        # Security log file - authentication and security events
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'security.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    
    'loggers': {
        # Django root logger
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        
        # Django security logger
        'django.security': {
            'handlers': ['security_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # Django request logger
        'django.request': {
            'handlers': ['file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        
        # Core app logger
        'core': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        
        # Transaction-specific logger
        'core.transactions': {
            'handlers': ['file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        
        # Authentication logger
        'core.auth': {
            'handlers': ['file', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
