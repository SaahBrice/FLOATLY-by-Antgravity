"""
Tests for dashboard views in Floatly.

Covers:
- Dashboard access and display
- Balance calculations
- Kiosk switching
- Permission checks
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from core.models import User, Kiosk, KioskMember, Network, Transaction


class DashboardAccessTests(TestCase):
    """Test dashboard access and permissions."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        self.dashboard_url = reverse('core:dashboard')
    
    def test_dashboard_requires_login(self):
        """Dashboard should redirect unauthenticated users."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_loads_for_authenticated_user(self):
        """Dashboard should load for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_shows_no_kiosk_message(self):
        """Dashboard should show message when user has no kiosks."""
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        self.assertContains(response, 'No Kiosk Found')
    
    def test_dashboard_shows_kiosk_data(self):
        """Dashboard should show kiosk data when user has a kiosk."""
        kiosk = Kiosk.objects.create(
            name='Test Kiosk',
            owner=self.user
        )
        
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        self.assertContains(response, 'Test Kiosk')


class BalanceCalculationTests(TestCase):
    """Test balance calculations on the dashboard."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        self.kiosk = Kiosk.objects.create(
            name='Test Kiosk',
            owner=self.user
        )
        self.network = Network.objects.create(
            name='MTN Mobile Money',
            code='MTN',
            color='#ffcc00'
        )
    
    def test_zero_balance_with_no_transactions(self):
        """Balances should be zero with no transactions."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:dashboard'))
        
        self.assertContains(response, '0')
    
    def test_deposit_increases_cash_decreases_float(self):
        """Deposit should increase cash and decrease float."""
        # Create a deposit transaction
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.network,
            transaction_type='DEPOSIT',
            amount=Decimal('10000'),
            profit=Decimal('100')
        )
        
        # Verify balances
        balances = self.kiosk.transactions.calculate_balances()
        
        # After deposit: cash increases, float decreases
        self.assertEqual(balances['cash_balance'], Decimal('10000'))
        self.assertEqual(balances['float_balance'], Decimal('-10000'))
    
    def test_withdrawal_decreases_cash_increases_float(self):
        """Withdrawal should decrease cash and increase float."""
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.network,
            transaction_type='WITHDRAWAL',
            amount=Decimal('5000'),
            profit=Decimal('50')
        )
        
        balances = self.kiosk.transactions.calculate_balances()
        
        # After withdrawal: cash decreases, float increases
        self.assertEqual(balances['cash_balance'], Decimal('-5000'))
        self.assertEqual(balances['float_balance'], Decimal('5000'))
    
    def test_mixed_transactions_balance(self):
        """Test balance with mixed transactions."""
        # Deposit 20000
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.network,
            transaction_type='DEPOSIT',
            amount=Decimal('20000'),
            profit=Decimal('200')
        )
        
        # Withdraw 5000
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.network,
            transaction_type='WITHDRAWAL',
            amount=Decimal('5000'),
            profit=Decimal('50')
        )
        
        balances = self.kiosk.transactions.calculate_balances()
        
        # Cash: 20000 - 5000 = 15000
        self.assertEqual(balances['cash_balance'], Decimal('15000'))
        # Float: -20000 + 5000 = -15000
        self.assertEqual(balances['float_balance'], Decimal('-15000'))


class KioskSwitchingTests(TestCase):
    """Test kiosk switching functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        self.kiosk1 = Kiosk.objects.create(
            name='Kiosk One',
            owner=self.user
        )
        self.kiosk2 = Kiosk.objects.create(
            name='Kiosk Two',
            owner=self.user
        )
    
    def test_can_switch_between_owned_kiosks(self):
        """User should be able to switch between their kiosks."""
        self.client.force_login(self.user)
        
        # Switch to kiosk2
        response = self.client.get(
            reverse('core:kiosk_switch', args=[self.kiosk2.slug]),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kiosk Two')
    
    def test_cannot_access_other_users_kiosk(self):
        """User should not be able to access another user's kiosk."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='OtherPass123!'
        )
        other_kiosk = Kiosk.objects.create(
            name='Other Kiosk',
            owner=other_user
        )
        
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('core:kiosk_switch', args=[other_kiosk.slug])
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_member_can_access_kiosk(self):
        """Kiosk member should be able to access the kiosk."""
        member = User.objects.create_user(
            email='member@example.com',
            password='MemberPass123!'
        )
        KioskMember.objects.create(
            kiosk=self.kiosk1,
            user=member,
            role=KioskMember.Role.AGENT
        )
        
        self.client.force_login(member)
        response = self.client.get(
            reverse('core:kiosk_switch', args=[self.kiosk1.slug]),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)


class TodayStatsTests(TestCase):
    """Test today's statistics on the dashboard."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        self.kiosk = Kiosk.objects.create(
            name='Test Kiosk',
            owner=self.user
        )
        self.network = Network.objects.create(
            name='MTN',
            code='MTN'
        )
    
    def test_today_profit_calculation(self):
        """Today's profit should sum all profits from today."""
        # Create transactions with profit
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.network,
            transaction_type='DEPOSIT',
            amount=Decimal('10000'),
            profit=Decimal('100')
        )
        Transaction.objects.create(
            kiosk=self.kiosk,
            recorded_by=self.user,
            network=self.network,
            transaction_type='WITHDRAWAL',
            amount=Decimal('5000'),
            profit=Decimal('50')
        )
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:dashboard'))
        
        # Should show total profit of 150
        self.assertContains(response, '150')
    
    def test_today_transaction_count(self):
        """Transaction count should reflect today's transactions."""
        # Create 3 transactions
        for i in range(3):
            Transaction.objects.create(
                kiosk=self.kiosk,
                recorded_by=self.user,
                network=self.network,
                transaction_type='DEPOSIT',
                amount=Decimal('1000'),
                profit=Decimal('10')
            )
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:dashboard'))
        
        # Should show count of 3
        self.assertContains(response, '>3<')
