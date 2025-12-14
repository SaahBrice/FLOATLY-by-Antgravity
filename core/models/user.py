"""
User model for Floatly.

Custom User model where email is the unique identifier for authentication.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils import timezone

from ..managers import UserManager


# =============================================================================
# VALIDATORS
# =============================================================================

phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{9,15}$',
    message='Phone number must be 9-15 digits, optionally starting with +'
)


# =============================================================================
# USER MODEL
# =============================================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model where email is the unique identifier for authentication.
    Supports future Google OAuth integration.
    """
    
    # Primary identification
    email = models.EmailField(
        'email address',
        unique=True,
        db_index=True,
        help_text='Primary login identifier'
    )
    
    # Profile information
    username = models.CharField(
        'username',
        max_length=50,
        blank=True,
        help_text='Display name (how the user wants to be called)'
    )
    full_name = models.CharField(
        'full name',
        max_length=150,
        blank=True,
        help_text='Full legal name for records'
    )
    phone_number = models.CharField(
        'phone number',
        max_length=20,
        blank=True,
        validators=[phone_validator],
        help_text='With country code, e.g., +237677123456'
    )
    
    # Email verification
    email_verified = models.BooleanField(
        'email verified',
        default=False,
        help_text='Has the user verified their email address?'
    )
    
    # Google OAuth fields (for future integration)
    google_id = models.CharField(
        'Google ID',
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text='Google account identifier for OAuth'
    )
    profile_picture = models.URLField(
        'profile picture URL',
        max_length=500,
        blank=True,
        help_text='URL to profile picture (from Google or uploaded)'
    )
    
    # Django permission fields
    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Can access admin site'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Account is active and can log in'
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        'date joined',
        default=timezone.now
    )
    last_login = models.DateTimeField(
        'last login',
        blank=True,
        null=True
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by USERNAME_FIELD
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.display_name
    
    @property
    def display_name(self):
        """Return the best available display name."""
        if self.username:
            return self.username
        if self.full_name:
            return self.full_name.split()[0]  # First name
        return self.email.split('@')[0]
    
    def get_full_name(self):
        return self.full_name or self.display_name
    
    def get_short_name(self):
        return self.display_name
