"""
Tests for authentication flow in Floatly.

Covers:
- User registration
- Email verification
- Login/Logout
- Onboarding (first kiosk creation)
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

from core.models import Kiosk, KioskMember

User = get_user_model()


class RegistrationTests(TestCase):
    """Test user registration flow."""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('core:register')
    
    def test_registration_page_loads(self):
        """Registration page should load successfully."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
    
    def test_registration_creates_user(self):
        """Valid registration should create a user."""
        response = self.client.post(self.register_url, {
            'email': 'test@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'phone_number': '+237677123456',
        })
        
        # Should redirect to verification pending
        self.assertEqual(response.status_code, 302)
        
        # User should exist
        self.assertTrue(User.objects.filter(email='test@example.com').exists())
        
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.phone_number, '+237677123456')
        self.assertFalse(user.email_verified)
    
    def test_registration_creates_email_address(self):
        """Registration should create an unverified EmailAddress."""
        self.client.post(self.register_url, {
            'email': 'test@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        
        user = User.objects.get(email='test@example.com')
        email_address = EmailAddress.objects.get(user=user)
        
        self.assertFalse(email_address.verified)
        self.assertTrue(email_address.primary)
    
    def test_registration_password_mismatch(self):
        """Mismatched passwords should show error."""
        response = self.client.post(self.register_url, {
            'email': 'test@example.com',
            'password1': 'SecurePass123!',
            'password2': 'DifferentPass456!',
        })
        
        # Should stay on page with errors
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='test@example.com').exists())
    
    def test_registration_duplicate_email(self):
        """Duplicate email should show error."""
        User.objects.create_user(email='existing@example.com', password='test123')
        
        response = self.client.post(self.register_url, {
            'email': 'existing@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
    
    def test_honeypot_blocks_bots(self):
        """Filling honeypot field should be rejected."""
        response = self.client.post(self.register_url, {
            'email': 'bot@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'website': 'spam-site.com',  # Honeypot
        })
        
        self.assertFalse(User.objects.filter(email='bot@example.com').exists())


class LoginTests(TestCase):
    """Test user login flow."""
    
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('core:login')
        
        # Create verified user
        self.user = User.objects.create_user(
            email='verified@example.com',
            password='TestPass123!'
        )
        EmailAddress.objects.create(
            user=self.user,
            email='verified@example.com',
            primary=True,
            verified=True
        )
        
        # Create unverified user
        self.unverified_user = User.objects.create_user(
            email='unverified@example.com',
            password='TestPass123!'
        )
        EmailAddress.objects.create(
            user=self.unverified_user,
            email='unverified@example.com',
            primary=True,
            verified=False
        )
    
    def test_login_page_loads(self):
        """Login page should load successfully."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome Back')
    
    def test_login_with_verified_email(self):
        """Verified user should be able to login."""
        response = self.client.post(self.login_url, {
            'login': 'verified@example.com',
            'password': 'TestPass123!',
        })
        
        # Should redirect (to onboarding since no kiosk)
        self.assertEqual(response.status_code, 302)
    
    def test_login_with_unverified_email(self):
        """Unverified user should be redirected to verification page."""
        response = self.client.post(self.login_url, {
            'login': 'unverified@example.com',
            'password': 'TestPass123!',
        })
        
        # Should redirect to verification pending
        self.assertRedirects(response, reverse('core:verification_pending'))
    
    def test_login_wrong_password(self):
        """Wrong password should show error."""
        response = self.client.post(self.login_url, {
            'login': 'verified@example.com',
            'password': 'WrongPassword!',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')
    
    def test_login_redirects_to_dashboard_if_has_kiosk(self):
        """User with kiosk should go to dashboard."""
        # Create kiosk for user
        kiosk = Kiosk.objects.create(
            name='Test Kiosk',
            owner=self.user
        )
        
        response = self.client.post(self.login_url, {
            'login': 'verified@example.com',
            'password': 'TestPass123!',
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')


class LogoutTests(TestCase):
    """Test user logout."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_logout(self):
        """User should be logged out."""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('core:logout'))
        
        # Should redirect to home
        self.assertEqual(response.status_code, 302)
        
        # Verify not authenticated
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirects to login


class OnboardingTests(TestCase):
    """Test first kiosk creation flow."""
    
    def setUp(self):
        self.client = Client()
        self.onboarding_url = reverse('core:onboarding')
        
        # Create verified user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        EmailAddress.objects.create(
            user=self.user,
            email='test@example.com',
            primary=True,
            verified=True
        )
    
    def test_onboarding_requires_login(self):
        """Onboarding page requires authentication."""
        response = self.client.get(self.onboarding_url)
        self.assertEqual(response.status_code, 302)
    
    def test_onboarding_page_loads(self):
        """Onboarding page loads for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(self.onboarding_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome')
    
    def test_onboarding_creates_kiosk(self):
        """Onboarding creates kiosk and membership."""
        self.client.force_login(self.user)
        
        response = self.client.post(self.onboarding_url, {
            'name': 'My First Kiosk',
            'location': 'Akwa, Douala',
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        
        # Kiosk should exist
        kiosk = Kiosk.objects.get(name='My First Kiosk')
        self.assertEqual(kiosk.owner, self.user)
        self.assertEqual(kiosk.location, 'Akwa, Douala')
        
        # User should be admin member
        membership = KioskMember.objects.get(kiosk=kiosk, user=self.user)
        self.assertEqual(membership.role, KioskMember.Role.ADMIN)
    
    def test_onboarding_redirects_if_has_kiosk(self):
        """User with kiosk should skip onboarding."""
        # Create kiosk
        Kiosk.objects.create(name='Existing Kiosk', owner=self.user)
        
        self.client.force_login(self.user)
        response = self.client.get(self.onboarding_url)
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)


class DashboardTests(TestCase):
    """Test dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('core:dashboard')
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_dashboard_requires_login(self):
        """Dashboard requires authentication."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_loads(self):
        """Dashboard loads for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
    
    def test_dashboard_shows_kiosks(self):
        """Dashboard shows user's kiosks."""
        kiosk = Kiosk.objects.create(name='Test Kiosk', owner=self.user)
        
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        
        self.assertContains(response, 'Test Kiosk')


class VerificationPendingTests(TestCase):
    """Test verification pending page."""
    
    def test_page_loads(self):
        """Verification pending page loads."""
        response = self.client.get(reverse('core:verification_pending'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Check Your Email')
