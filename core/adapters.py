"""
Custom adapters for django-allauth.

These adapters customize the authentication flow:
- CustomAccountAdapter: Handles email-based registration and redirects
- CustomSocialAccountAdapter: Handles Google OAuth signup/login
"""

from django.shortcuts import redirect
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for email-based authentication.
    Handles redirects after signup/login based on user state.
    """
    
    def get_login_redirect_url(self, request):
        """
        Redirect user after login based on their state:
        - No kiosks: Go to onboarding
        - Has kiosks: Go to dashboard
        """
        user = request.user
        
        # Check if user has any kiosks (owned or member of)
        has_kiosks = (
            user.owned_kiosks.exists() or 
            user.kiosk_memberships.exists()
        )
        
        if not has_kiosks:
            return reverse('core:onboarding')
        
        return reverse('core:dashboard')
    
    def get_signup_redirect_url(self, request):
        """
        After signup, redirect to verification pending page.
        """
        return reverse('core:verification_pending')
    
    def send_mail(self, template_prefix, email, context):
        """
        Override to customize email sending.
        Adds app branding to context.
        """
        context['app_name'] = 'Floatly'
        context['support_email'] = 'support@floatly.cm'
        super().send_mail(template_prefix, email, context)
    
    def is_open_for_signup(self, request):
        """
        Control whether registration is open.
        Could be used to close registration temporarily.
        """
        return True
    
    def save_user(self, request, user, form, commit=True):
        """
        Save user with additional fields from registration form.
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Get phone number from form if provided
        phone_number = form.cleaned_data.get('phone_number', '')
        if phone_number:
            user.phone_number = phone_number
        
        if commit:
            user.save()
        
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for social (Google) authentication.
    Auto-fills user profile from Google data.
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Called before social login completes.
        Can be used to connect social account to existing user.
        """
        # If email already exists, connect accounts
        if sociallogin.is_existing:
            return
        
        # Try to find existing user with this email
        email = sociallogin.account.extra_data.get('email')
        if email:
            from core.models import User
            try:
                existing_user = User.objects.get(email__iexact=email)
                # Connect social account to existing user
                sociallogin.connect(request, existing_user)
            except User.DoesNotExist:
                pass
    
    def populate_user(self, request, sociallogin, data):
        """
        Populate user instance with data from social provider.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Fill in additional fields from Google data
        extra_data = sociallogin.account.extra_data
        
        # Set full name
        if 'name' in extra_data:
            user.full_name = extra_data['name']
        
        # Set profile picture URL
        if 'picture' in extra_data:
            user.profile_picture = extra_data['picture']
        
        # Set Google ID
        user.google_id = extra_data.get('sub', '')
        
        # Email is automatically verified via Google
        user.email_verified = True
        
        return user
    
    def get_login_redirect_url(self, request):
        """
        Redirect after Google login.
        """
        return CustomAccountAdapter().get_login_redirect_url(request)
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Control whether social signup is allowed.
        """
        return True
