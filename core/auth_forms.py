"""
Authentication forms for Floatly.

Forms include:
- FloatlySignupForm: Email, password, phone (optional), honeypot for bots
- FloatlyLoginForm: Email, password, remember me
- OnboardingForm: First kiosk setup
"""

from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Kiosk

User = get_user_model()

# Phone validator
phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{9,15}$',
    message='Enter a valid phone number (9-15 digits)'
)


class HoneypotMixin:
    """
    Mixin to add honeypot bot protection to forms.
    Bots typically fill all fields, including hidden ones.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hidden honeypot field - bots fill it, humans don't
        self.fields['website'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'tabindex': '-1',
                'autocomplete': 'off',
                'style': 'position: absolute; left: -9999px;'
            }),
            label=''
        )
    
    def clean_website(self):
        """
        If honeypot field has content, it's a bot.
        """
        website = self.cleaned_data.get('website', '')
        if website:
            raise forms.ValidationError('Bot detected.')
        return website


class FloatlySignupForm(HoneypotMixin, forms.Form):
    """
    Custom registration form with phone number and honeypot protection.
    """
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email address',
            'class': 'form-input',
            'type': 'email',
            'autocomplete': 'email',
            'inputmode': 'email',
        })
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-input',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        label='Password'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm password',
            'class': 'form-input',
            'autocomplete': 'new-password',
        }),
        label='Confirm Password'
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone number (optional)',
            'type': 'tel',
            'class': 'form-input',
            'autocomplete': 'tel',
        }),
        help_text='Optional. Include country code, e.g., +237677123456'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        # Use Django's password validation
        validate_password(password)
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data


class FloatlyLoginForm(HoneypotMixin, forms.Form):
    """
    Custom login form with styled inputs and honeypot protection.
    """
    
    login = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email address',
            'class': 'form-input',
            'type': 'email',
            'autocomplete': 'email',
            'inputmode': 'email',
        }),
        label='Email'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-input',
            'autocomplete': 'current-password',
        })
    )
    
    remember = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='Remember me for 30 days'
    )


class OnboardingForm(forms.ModelForm):
    """
    Form for creating the user's first kiosk during onboarding.
    """
    
    class Meta:
        model = Kiosk
        fields = ['name', 'location']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g., My Main Shop',
                'class': 'form-input',
                'autofocus': True,
                'autocomplete': 'off',
                'maxlength': '100',
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'e.g., Akwa, Douala (optional)',
                'class': 'form-input',
                'autocomplete': 'off',
                'maxlength': '255',
            }),
        }
        labels = {
            'name': 'Kiosk Name',
            'location': 'Location (optional)',
        }
        help_texts = {
            'name': 'Give your kiosk a memorable name',
            'location': 'Where is your kiosk located?',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make location optional
        self.fields['location'].required = False
    
    def clean_name(self):
        """
        Validate kiosk name.
        """
        name = self.cleaned_data.get('name', '').strip()
        
        if not name:
            raise forms.ValidationError('Please enter a name for your kiosk.')
        
        if len(name) < 2:
            raise forms.ValidationError('Kiosk name must be at least 2 characters.')
        
        return name
    
    def save(self, commit=True):
        """
        Save kiosk and set the current user as owner.
        """
        kiosk = super().save(commit=False)
        kiosk.owner = self.user
        
        if commit:
            kiosk.save()
            
            # Add owner as admin member
            from .models import KioskMember
            KioskMember.objects.create(
                kiosk=kiosk,
                user=self.user,
                role=KioskMember.Role.ADMIN
            )
        
        return kiosk


class ResendVerificationForm(forms.Form):
    """
    Form to resend verification email.
    """
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Your email address',
            'class': 'form-input',
            'autocomplete': 'email',
        })
    )
