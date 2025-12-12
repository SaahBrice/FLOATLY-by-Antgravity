"""
Authentication views for Floatly.

Handles:
- Registration (email/password)
- Email verification
- Login (email/password + Google OAuth)
- Logout
- Onboarding (first kiosk creation)
"""

import logging
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from allauth.account.models import EmailAddress

from .auth_forms import FloatlySignupForm, FloatlyLoginForm, OnboardingForm, ResendVerificationForm
from .models import User, Kiosk, KioskMember

# Logger for authentication operations
logger = logging.getLogger('core.auth')


class RegisterView(FormView):
    """
    User registration with email and password.
    Custom implementation to avoid allauth URL dependencies.
    """
    template_name = 'auth/register.html'
    form_class = FloatlySignupForm
    success_url = reverse_lazy('core:verification_pending')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Account'
        return context
    
    def form_valid(self, form):
        """
        Create user and send verification email.
        """
        # Check honeypot
        if form.cleaned_data.get('website'):
            logger.warning(f"Bot detected on registration: IP={self.request.META.get('REMOTE_ADDR')}")
            messages.error(self.request, 'Bot detected.')
            return self.form_invalid(form)
        
        # Create user
        email = form.cleaned_data['email']
        password = form.cleaned_data['password1']
        phone_number = form.cleaned_data.get('phone_number', '')
        
        try:
            user = User.objects.create_user(
                email=email,
                password=password
            )
            if phone_number:
                user.phone_number = phone_number
                user.save(update_fields=['phone_number'])
            
            # Create EmailAddress for allauth (for verification)
            email_address = EmailAddress.objects.create(
                user=user,
                email=email,
                primary=True,
                verified=False
            )
            
            logger.info(f"User registered: email={email}, phone={phone_number or 'N/A'}")
            
            # Try to send verification email (non-fatal if it fails)
            try:
                email_address.send_confirmation(self.request, signup=True)
                logger.info(f"Verification email sent: email={email}")
            except Exception as email_error:
                # Log but don't fail - user can resend later
                logger.warning(f"Failed to send verification email to {email}: {email_error}")
            
            # Store email in session for display
            self.request.session['pending_verification_email'] = email
            
            messages.success(
                self.request,
                'Account created! Check your email to verify your account.'
            )
            
        except Exception as e:
            messages.error(self.request, f'Error creating account: {str(e)}')
            return self.form_invalid(form)
        
        return super().form_valid(form)


class LoginView(FormView):
    """
    User login with email/password.
    """
    template_name = 'auth/login.html'
    form_class = FloatlyLoginForm
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url_for_user(request.user))
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Log In'
        return context
    
    def form_valid(self, form):
        """
        Authenticate and login user.
        """
        # Check honeypot
        if form.cleaned_data.get('website'):
            messages.error(self.request, 'Bot detected.')
            return self.form_invalid(form)
        
        email = form.cleaned_data['login']
        password = form.cleaned_data['password']
        remember = form.cleaned_data.get('remember', True)
        
        # Authenticate
        user = authenticate(self.request, username=email, password=password)
        
        if user is None:
            messages.error(self.request, 'Invalid email or password.')
            return self.form_invalid(form)
        
        if not user.is_active:
            messages.error(self.request, 'This account has been disabled.')
            return self.form_invalid(form)
        
        # Check email verification
        try:
            email_address = EmailAddress.objects.get(user=user, primary=True)
            if not email_address.verified:
                # Store email for resend
                self.request.session['pending_verification_email'] = email
                logger.info(f"Login blocked - email not verified: email={email}")
                messages.warning(
                    self.request,
                    'Please verify your email before logging in.'
                )
                return redirect('core:verification_pending')
        except EmailAddress.DoesNotExist:
            # Legacy user or admin - allow login
            pass
        
        # Login
        login(self.request, user)
        
        logger.info(
            f"User logged in: email={user.email}, "
            f"IP={self.request.META.get('REMOTE_ADDR')}, "
            f"remember_me={remember}"
        )
        
        # Handle remember me
        if not remember:
            self.request.session.set_expiry(0)
        
        messages.success(self.request, f'Welcome back, {user.display_name}!')
        
        return redirect(self.get_success_url_for_user(user))
    
    def get_success_url_for_user(self, user):
        """Redirect based on user's kiosk status."""
        has_kiosks = (
            user.owned_kiosks.exists() or 
            user.kiosk_memberships.exists()
        )
        
        if not has_kiosks:
            return reverse('core:onboarding')
        
        return reverse('core:dashboard')


class LogoutView(View):
    """
    User logout.
    """
    def get(self, request):
        return self.post(request)
    
    def post(self, request):
        user_email = request.user.email if request.user.is_authenticated else 'anonymous'
        logout(request)
        logger.info(f"User logged out: email={user_email}")
        messages.success(request, 'You have been logged out.')
        return redirect('core:home')


class VerificationPendingView(TemplateView):
    """
    Shown after registration - "Check your email" message.
    """
    template_name = 'auth/verification_pending.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Verify Your Email'
        context['email'] = self.request.session.get('pending_verification_email', '')
        return context


class VerificationSuccessView(TemplateView):
    """
    Shown after successful email verification.
    """
    template_name = 'auth/verification_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Email Verified!'
        return context


class ResendVerificationView(FormView):
    """
    Resend verification email.
    """
    template_name = 'auth/resend_verification.html'
    form_class = ResendVerificationForm
    success_url = reverse_lazy('core:verification_pending')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        
        try:
            user = User.objects.get(email__iexact=email)
            
            # Get or create email address in allauth
            email_address, created = EmailAddress.objects.get_or_create(
                user=user,
                email=email,
                defaults={'primary': True, 'verified': False}
            )
            
            if not email_address.verified:
                email_address.send_confirmation(self.request)
                self.request.session['pending_verification_email'] = email
                messages.success(
                    self.request,
                    'Verification email sent! Check your inbox.'
                )
            else:
                messages.info(
                    self.request,
                    'This email is already verified. You can log in.'
                )
                return redirect('core:login')
                
        except User.DoesNotExist:
            # Don't reveal if email exists - just show generic message
            messages.success(
                self.request,
                'If this email is registered, you will receive a verification link.'
            )
        
        return super().form_valid(form)


class OnboardingView(LoginRequiredMixin, FormView):
    """
    Kiosk creation view - works for both first kiosk and additional kiosks.
    """
    template_name = 'auth/onboarding.html'
    form_class = OnboardingForm
    success_url = reverse_lazy('core:dashboard')
    login_url = '/auth/login/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        has_kiosks = user.owned_kiosks.exists() or user.kiosk_memberships.exists()
        
        if has_kiosks:
            context['page_title'] = 'Add New Kiosk'
            context['is_first_kiosk'] = False
        else:
            context['page_title'] = 'Welcome to Floatly!'
            context['is_first_kiosk'] = True
        
        context['user'] = user
        return context
    
    def form_valid(self, form):
        kiosk = form.save()
        messages.success(
            self.request,
            f'🎉 Your kiosk "{kiosk.name}" is ready!'
        )
        return super().form_valid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view.
    """
    template_name = 'core/dashboard.html'
    login_url = '/auth/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Dashboard'
        
        user = self.request.user
        
        # Get user's kiosks
        owned_kiosks = Kiosk.objects.filter(owner=user, is_active=True)
        member_kiosks = Kiosk.objects.filter(
            members__user=user, is_active=True
        ).exclude(owner=user).distinct()
        
        context['owned_kiosks'] = owned_kiosks
        context['member_kiosks'] = member_kiosks
        context['has_kiosks'] = owned_kiosks.exists() or member_kiosks.exists()
        
        # Get active kiosk (first owned, or first member)
        if owned_kiosks.exists():
            context['active_kiosk'] = owned_kiosks.first()
        elif member_kiosks.exists():
            context['active_kiosk'] = member_kiosks.first()
        else:
            context['active_kiosk'] = None
        
        return context
