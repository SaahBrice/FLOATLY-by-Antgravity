"""
Model tests for Floatly.

Tests cover:
- User creation with email login
- Kiosk unique name/slug generation
- KioskMember unique constraint
- Commission rate lookup and calculation
- Transaction auto-profit calculation
- Balance calculations
"""

from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from core.models import (
    User, Kiosk, KioskMember, Network, 
    CommissionRate, Transaction, Notification
)
from core.services import (
    calculate_commission, get_kiosk_balances,
    generate_unique_kiosk_name, create_kiosk_with_owner_as_admin,
    seed_default_networks, seed_default_commission_rates
)


class UserModelTests(TestCase):
    """Tests for custom User model."""
    
    def test_create_user_with_email(self):
        """Test creating a user with email (not username)."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.full_name, 'Test User')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.email_verified)
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.email_verified)
    
    def test_user_display_name_priority(self):
        """Test display_name returns best available name."""
        # With username
        user1 = User.objects.create_user(
            email='user1@example.com',
            password='pass123',
            username='CoolUser',
            full_name='John Doe'
        )
        self.assertEqual(user1.display_name, 'CoolUser')
        
        # Without username, with full_name
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass123',
            full_name='Jane Smith'
        )
        self.assertEqual(user2.display_name, 'Jane')  # First name
        
        # Only email
        user3 = User.objects.create_user(
            email='user3@example.com',
            password='pass123'
        )
        self.assertEqual(user3.display_name, 'user3')  # Email prefix
    
    def test_email_uniqueness(self):
        """Test that email addresses must be unique."""
        User.objects.create_user(email='unique@example.com', password='pass123')
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='unique@example.com', password='pass456')


class KioskModelTests(TestCase):
    """Tests for Kiosk model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='pass123'
        )
    
    def test_kiosk_creation(self):
        """Test basic kiosk creation."""
        kiosk = Kiosk.objects.create(
            name='Akwa Shop',
            owner=self.user,
            location='Akwa, Douala'
        )
        
        self.assertEqual(kiosk.name, 'Akwa Shop')
        self.assertEqual(kiosk.owner, self.user)
        self.assertTrue(kiosk.is_active)
        self.assertIsNotNone(kiosk.slug)
    
    def test_auto_slug_generation(self):
        """Test that slug is auto-generated from name."""
        kiosk = Kiosk.objects.create(
            name='My Awesome Kiosk',
            owner=self.user
        )
        
        self.assertEqual(kiosk.slug, 'my-awesome-kiosk')
    
    def test_unique_slug_generation(self):
        """Test that duplicate names get unique slugs."""
        kiosk1 = Kiosk.objects.create(name='Shop', owner=self.user)
        kiosk2 = Kiosk.objects.create(name='Shop', owner=self.user)
        
        self.assertEqual(kiosk1.slug, 'shop')
        self.assertEqual(kiosk2.slug, 'shop-1')
    
    def test_generate_unique_kiosk_name(self):
        """Test unique name generation service."""
        Kiosk.objects.create(name='My Shop', owner=self.user)
        
        unique_name = generate_unique_kiosk_name('My Shop', self.user)
        self.assertEqual(unique_name, 'My Shop (1)')
    
    def test_create_kiosk_with_owner_as_admin(self):
        """Test service creates kiosk and adds owner as admin member."""
        kiosk = create_kiosk_with_owner_as_admin(
            name='New Kiosk',
            owner=self.user,
            location='Molyko'
        )
        
        self.assertEqual(kiosk.name, 'New Kiosk')
        self.assertTrue(
            KioskMember.objects.filter(
                kiosk=kiosk,
                user=self.user,
                role='ADMIN'
            ).exists()
        )


class KioskMemberTests(TestCase):
    """Tests for KioskMember model."""
    
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@example.com', password='pass')
        self.agent = User.objects.create_user(email='agent@example.com', password='pass')
        self.kiosk = Kiosk.objects.create(name='Test Kiosk', owner=self.owner)
    
    def test_add_member(self):
        """Test adding a team member to a kiosk."""
        member = KioskMember.objects.create(
            kiosk=self.kiosk,
            user=self.agent,
            role='AGENT'
        )
        
        self.assertEqual(member.kiosk, self.kiosk)
        self.assertEqual(member.user, self.agent)
        self.assertEqual(member.role, 'AGENT')
        self.assertFalse(member.is_admin)
    
    def test_unique_member_constraint(self):
        """Test that a user can only be added once per kiosk."""
        KioskMember.objects.create(kiosk=self.kiosk, user=self.agent, role='AGENT')
        
        with self.assertRaises(IntegrityError):
            KioskMember.objects.create(kiosk=self.kiosk, user=self.agent, role='ADMIN')
    
    def test_user_can_be_member_of_multiple_kiosks(self):
        """Test that one user can be a member of multiple kiosks."""
        kiosk2 = Kiosk.objects.create(name='Second Kiosk', owner=self.owner)
        
        KioskMember.objects.create(kiosk=self.kiosk, user=self.agent, role='AGENT')
        KioskMember.objects.create(kiosk=kiosk2, user=self.agent, role='ADMIN')
        
        self.assertEqual(self.agent.kiosk_memberships.count(), 2)


class CommissionRateTests(TestCase):
    """Tests for Network and CommissionRate models."""
    
    def setUp(self):
        self.mtn = Network.objects.create(
            name='MTN Mobile Money',
            code='MTN',
            color='#ffcc00'
        )
        
        # Create rate rules
        CommissionRate.objects.create(
            network=self.mtn,
            min_amount=Decimal('100'),
            max_amount=Decimal('5000'),
            rate_type='FIXED',
            rate_value=Decimal('50')
        )
        CommissionRate.objects.create(
            network=self.mtn,
            min_amount=Decimal('5001'),
            max_amount=Decimal('10000'),
            rate_type='FIXED',
            rate_value=Decimal('100')
        )
        CommissionRate.objects.create(
            network=self.mtn,
            min_amount=Decimal('50001'),
            max_amount=Decimal('500000'),
            rate_type='PERCENTAGE',
            rate_value=Decimal('0.3')
        )
    
    def test_fixed_commission_lookup(self):
        """Test finding and calculating fixed commission."""
        rate = CommissionRate.get_rate_for_amount(self.mtn, Decimal('3000'))
        
        self.assertIsNotNone(rate)
        self.assertEqual(rate.rate_type, 'FIXED')
        self.assertEqual(rate.calculate_commission(Decimal('3000')), Decimal('50'))
    
    def test_percentage_commission_calculation(self):
        """Test calculating percentage-based commission."""
        rate = CommissionRate.get_rate_for_amount(self.mtn, Decimal('100000'))
        
        self.assertIsNotNone(rate)
        self.assertEqual(rate.rate_type, 'PERCENTAGE')
        # 100,000 * 0.3% = 300
        self.assertEqual(rate.calculate_commission(Decimal('100000')), Decimal('300.00'))
    
    def test_commission_service_function(self):
        """Test calculate_commission helper."""
        commission = calculate_commission(self.mtn, 7500)
        self.assertEqual(commission, Decimal('100'))
    
    def test_no_matching_rate(self):
        """Test behavior when no matching rate exists."""
        rate = CommissionRate.get_rate_for_amount(self.mtn, Decimal('50'))  # Below min
        self.assertIsNone(rate)


class TransactionTests(TestCase):
    """Tests for Transaction model and auto-profit calculation."""
    
    def setUp(self):
        self.user = User.objects.create_user(email='agent@example.com', password='pass')
        self.kiosk = Kiosk.objects.create(name='Test Kiosk', owner=self.user)
        self.mtn = Network.objects.create(name='MTN', code='MTN', color='#ffcc00')
        
        # Create commission rate
        CommissionRate.objects.create(
            network=self.mtn,
            min_amount=Decimal('100'),
            max_amount=Decimal('50000'),
            rate_type='FIXED',
            rate_value=Decimal('150')
        )
    
    def test_auto_profit_calculation(self):
        """Test that profit is auto-calculated on save."""
        transaction = Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.mtn,
            transaction_type='DEPOSIT',
            amount=Decimal('10000')
        )
        
        self.assertEqual(transaction.calculated_profit, Decimal('150'))
        self.assertEqual(transaction.profit, Decimal('150'))
        self.assertFalse(transaction.profit_was_edited)
    
    def test_profit_override(self):
        """Test manually overriding calculated profit."""
        transaction = Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.mtn,
            transaction_type='DEPOSIT',
            amount=Decimal('10000')
        )
        
        # Override profit
        transaction.profit = Decimal('100')
        transaction.profit_was_edited = True
        transaction.save()
        
        # Calculated profit unchanged, actual profit updated
        self.assertEqual(transaction.calculated_profit, Decimal('150'))
        self.assertEqual(transaction.profit, Decimal('100'))
        self.assertTrue(transaction.profit_was_edited)


class BalanceCalculationTests(TestCase):
    """Tests for cash and float balance calculations."""
    
    def setUp(self):
        self.user = User.objects.create_user(email='agent@example.com', password='pass')
        self.kiosk = Kiosk.objects.create(name='Test Kiosk', owner=self.user)
        self.mtn = Network.objects.create(name='MTN', code='MTN', color='#ffcc00')
        
        CommissionRate.objects.create(
            network=self.mtn,
            min_amount=Decimal('0'),
            max_amount=Decimal('1000000'),
            rate_type='FIXED',
            rate_value=Decimal('100')
        )
    
    def test_deposit_increases_cash(self):
        """Test: Deposit → Cash ↑, Float ↓"""
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.mtn,
            transaction_type='DEPOSIT',
            amount=Decimal('10000')
        )
        
        balances = self.kiosk.get_balances()
        
        self.assertEqual(balances['cash_balance'], Decimal('10000'))
        self.assertEqual(balances['float_balance'], Decimal('-10000'))
    
    def test_withdrawal_decreases_cash(self):
        """Test: Withdrawal → Cash ↓, Float ↑"""
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.mtn,
            transaction_type='WITHDRAWAL',
            amount=Decimal('5000')
        )
        
        balances = self.kiosk.get_balances()
        
        self.assertEqual(balances['cash_balance'], Decimal('-5000'))
        self.assertEqual(balances['float_balance'], Decimal('5000'))
    
    def test_multiple_transactions_balance(self):
        """Test balance calculation with multiple transactions."""
        # 3 deposits totaling 25,000
        Transaction.objects.create(
            kiosk=self.kiosk, recorded_by=self.user, network=self.mtn,
            transaction_type='DEPOSIT', amount=Decimal('10000')
        )
        Transaction.objects.create(
            kiosk=self.kiosk, recorded_by=self.user, network=self.mtn,
            transaction_type='DEPOSIT', amount=Decimal('10000')
        )
        Transaction.objects.create(
            kiosk=self.kiosk, recorded_by=self.user, network=self.mtn,
            transaction_type='DEPOSIT', amount=Decimal('5000')
        )
        
        # 2 withdrawals totaling 12,000
        Transaction.objects.create(
            kiosk=self.kiosk, recorded_by=self.user, network=self.mtn,
            transaction_type='WITHDRAWAL', amount=Decimal('8000')
        )
        Transaction.objects.create(
            kiosk=self.kiosk, recorded_by=self.user, network=self.mtn,
            transaction_type='WITHDRAWAL', amount=Decimal('4000')
        )
        
        balances = self.kiosk.get_balances()
        
        # Cash: +25,000 - 12,000 = 13,000
        self.assertEqual(balances['cash_balance'], Decimal('13000'))
        # Float: -25,000 + 12,000 = -13,000
        self.assertEqual(balances['float_balance'], Decimal('-13000'))
        # Profit: 5 transactions × 100 = 500
        self.assertEqual(balances['total_profit'], Decimal('500'))


class NotificationTests(TestCase):
    """Tests for Notification model."""
    
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='pass')
        self.owner = User.objects.create_user(email='owner@example.com', password='pass')
        self.kiosk = Kiosk.objects.create(name='Test Kiosk', owner=self.owner)
    
    def test_create_invite_notification(self):
        """Test creating an invitation notification."""
        notification = Notification.create_invite(
            user=self.user,
            kiosk=self.kiosk,
            invited_by=self.owner
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'INVITE')
        self.assertEqual(notification.related_kiosk, self.kiosk)
        self.assertFalse(notification.is_read)
        self.assertIn(self.kiosk.name, notification.title)
    
    def test_mark_as_read(self):
        """Test marking notification as read."""
        notification = Notification.objects.create(
            user=self.user,
            title='Test',
            message='Test message',
            notification_type='SYSTEM'
        )
        
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        
        notification.mark_as_read()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)


class SeedDataTests(TestCase):
    """Tests for data seeding functions."""
    
    def test_seed_default_networks(self):
        """Test seeding default networks."""
        networks = seed_default_networks()
        
        self.assertEqual(len(networks), 4)
        self.assertTrue(Network.objects.filter(code='MTN').exists())
        self.assertTrue(Network.objects.filter(code='OM').exists())
    
    def test_seed_default_commission_rates(self):
        """Test seeding default commission rates."""
        rates = seed_default_commission_rates()
        
        # Should create 8 rates (4 per network for MTN and OM)
        self.assertGreaterEqual(len(rates), 8)
        
        # Verify MTN rate lookup works
        mtn = Network.objects.get(code='MTN')
        rate = CommissionRate.get_rate_for_amount(mtn, Decimal('7500'))
        self.assertIsNotNone(rate)
        self.assertEqual(rate.calculate_commission(Decimal('7500')), Decimal('100'))
