"""
Custom managers for Floatly models.

Provides specialized querysets and manager methods for:
- User creation with email-based authentication
- Transaction aggregation and filtering
- Kiosk balance calculations
"""

from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models import Sum, Q, Case, When, F, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal


class UserManager(BaseUserManager):
    """
    Custom manager for User model where email is the unique identifier
    for authentication instead of username.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class TransactionQuerySet(models.QuerySet):
    """
    Custom QuerySet for Transaction model with common filtering
    and aggregation methods.
    """
    
    def for_kiosk(self, kiosk):
        """Filter transactions for a specific kiosk."""
        return self.filter(kiosk=kiosk)
    
    def for_user(self, user):
        """Filter transactions recorded by a specific user."""
        return self.filter(recorded_by=user)
    
    def deposits(self):
        """Filter only deposit transactions."""
        return self.filter(transaction_type='DEPOSIT')
    
    def withdrawals(self):
        """Filter only withdrawal transactions."""
        return self.filter(transaction_type='WITHDRAWAL')
    
    def for_network(self, network):
        """Filter transactions for a specific network."""
        return self.filter(network=network)
    
    def in_date_range(self, start_date, end_date):
        """Filter transactions within a date range."""
        return self.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
    
    def today(self):
        """Filter transactions from today."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.filter(timestamp__date=today)
    
    def calculate_totals(self):
        """
        Calculate total amounts and profits.
        Returns dict with total_amount, total_profit, count.
        """
        return self.aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal('0')),
            total_profit=Coalesce(Sum('profit'), Decimal('0')),
            count=models.Count('id')
        )
    
    def calculate_balances(self, date=None, kiosk=None):
        """
        Calculate the current cash, float, and profit balances based on transactions.
        
        Cash In (Deposit): Cash ↑, Float ↓, Profit ↑ (commission from network)
        Cash Out (Withdrawal): Cash ↓, Float ↑, Profit ↑ (share of fee)
        Profit Withdrawal: Profit ↓, Float ↑ (moves profit to main account)
        
        If date is provided, uses opening balance for that day + day's transactions.
        If no date, uses today.
        
        Returns dict with:
        - cash_balance: Current cash in drawer
        - float_balance: Total float across all networks
        - float_per_network: Dict of {network_id: balance} for each network
        - profit_balance: Total profit across all networks (today only)
        - profit_per_network: Dict of {network_id: profit} for each network
        - day_started: Whether opening balance exists for the day
        - total_profit: Sum of all profits (alias for profit_balance)
        """
        from django.utils import timezone
        from .models import DailyOpeningBalance, Network
        
        target_date = date or timezone.now().date()
        
        # Try to determine kiosk from queryset if not provided
        if kiosk is None and self.exists():
            first_tx = self.first()
            if first_tx:
                kiosk = first_tx.kiosk
        
        # Get opening balance for the day
        opening = None
        opening_cash = Decimal('0')
        opening_floats = {}
        day_started = False
        
        if kiosk:
            try:
                opening = DailyOpeningBalance.objects.get(kiosk=kiosk, date=target_date)
                opening_cash = opening.opening_cash
                opening_floats = {
                    nf.network_id: nf.opening_float 
                    for nf in opening.network_floats.all()
                }
                day_started = True
            except DailyOpeningBalance.DoesNotExist:
                # No opening balance - use yesterday's closing as default
                closing = DailyOpeningBalance.get_previous_day_closing(kiosk, target_date)
                opening_cash = closing.get('cash', Decimal('0'))
                opening_floats = closing.get('floats', {})
        
        # Get transactions for target date only
        day_transactions = self.filter(timestamp__date=target_date)
        
        # Calculate cash delta for the day
        # DEPOSIT: +cash, WITHDRAWAL: -cash, PROFIT_WITHDRAWAL: no effect on cash
        cash_delta = day_transactions.aggregate(
            delta=Coalesce(
                Sum(
                    Case(
                        When(transaction_type='DEPOSIT', then=F('amount')),
                        When(transaction_type='WITHDRAWAL', then=-F('amount')),
                        # PROFIT_WITHDRAWAL doesn't affect cash
                        default=Decimal('0'),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ),
                Decimal('0')
            )
        )['delta']
        
        # Calculate per-network float and profit deltas
        float_per_network = {}
        profit_per_network = {}
        total_float = Decimal('0')
        total_profit = Decimal('0')
        
        for network in Network.objects.filter(is_active=True):
            network_transactions = day_transactions.filter(network=network)
            
            # Float delta: WITHDRAWAL: +amount, DEPOSIT: -amount, PROFIT_WITHDRAWAL: +amount
            float_delta = network_transactions.aggregate(
                delta=Coalesce(
                    Sum(
                        Case(
                            When(transaction_type='WITHDRAWAL', then=F('amount')),
                            When(transaction_type='DEPOSIT', then=-F('amount')),
                            When(transaction_type='PROFIT_WITHDRAWAL', then=F('amount')),
                            default=Decimal('0'),
                            output_field=DecimalField(max_digits=12, decimal_places=2)
                        )
                    ),
                    Decimal('0')
                )
            )['delta']
            
            # Profit: Sum of all profit fields minus any profit withdrawals
            # DEPOSIT/WITHDRAWAL: profit field is commission/share
            # PROFIT_WITHDRAWAL: profit field is negative (withdrawal from profit account)
            profit_earned = network_transactions.exclude(
                transaction_type='PROFIT_WITHDRAWAL'
            ).aggregate(
                earned=Coalesce(Sum('profit'), Decimal('0'))
            )['earned']
            
            profit_withdrawn = network_transactions.filter(
                transaction_type='PROFIT_WITHDRAWAL'
            ).aggregate(
                withdrawn=Coalesce(Sum('amount'), Decimal('0'))
            )['withdrawn']
            
            network_profit = profit_earned - profit_withdrawn
            
            network_opening = opening_floats.get(network.id, Decimal('0'))
            network_balance = network_opening + float_delta
            
            float_per_network[network.id] = {
                'network': network,
                'balance': network_balance,
                'opening': network_opening,
                'delta': float_delta,
            }
            profit_per_network[network.id] = {
                'network': network,
                'earned': profit_earned,
                'withdrawn': profit_withdrawn,
                'balance': network_profit,
            }
            
            total_float += network_balance
            total_profit += network_profit
        
        return {
            'cash_balance': opening_cash + cash_delta,
            'float_balance': total_float,
            'float_per_network': float_per_network,
            'profit_balance': total_profit,
            'profit_per_network': profit_per_network,
            'day_started': day_started,
            'total_profit': total_profit,
            'opening_cash': opening_cash,
            'cash_delta': cash_delta,
        }

    
    def calculate_balances_legacy(self):
        """
        Legacy balance calculation - cumulative sum of all transactions.
        Kept for backward compatibility with existing tests.
        """
        result = self.aggregate(
            cash_balance=Coalesce(
                Sum(
                    Case(
                        When(transaction_type='DEPOSIT', then=F('amount')),
                        When(transaction_type='WITHDRAWAL', then=-F('amount')),
                        default=Decimal('0'),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ),
                Decimal('0')
            ),
            float_balance=Coalesce(
                Sum(
                    Case(
                        When(transaction_type='WITHDRAWAL', then=F('amount')),
                        When(transaction_type='DEPOSIT', then=-F('amount')),
                        default=Decimal('0'),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ),
                Decimal('0')
            ),
            total_profit=Coalesce(Sum('profit'), Decimal('0'))
        )
        return result


class TransactionManager(models.Manager):
    """Manager for Transaction model using TransactionQuerySet."""
    
    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)
    
    def for_kiosk(self, kiosk):
        return self.get_queryset().for_kiosk(kiosk)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def deposits(self):
        return self.get_queryset().deposits()
    
    def withdrawals(self):
        return self.get_queryset().withdrawals()
    
    def today(self):
        return self.get_queryset().today()


class KioskQuerySet(models.QuerySet):
    """
    Custom QuerySet for Kiosk model.
    """
    
    def active(self):
        """Filter only active kiosks."""
        return self.filter(is_active=True)
    
    def owned_by(self, user):
        """Filter kiosks owned by a specific user."""
        return self.filter(owner=user)
    
    def with_member(self, user):
        """Filter kiosks where user is a member (including owner)."""
        return self.filter(
            Q(owner=user) | Q(members__user=user)
        ).distinct()


class KioskManager(models.Manager):
    """Manager for Kiosk model using KioskQuerySet."""
    
    def get_queryset(self):
        return KioskQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def owned_by(self, user):
        return self.get_queryset().owned_by(user)
    
    def with_member(self, user):
        return self.get_queryset().with_member(user)
