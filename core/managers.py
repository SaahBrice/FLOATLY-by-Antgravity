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
    
    def calculate_balances(self):
        """
        Calculate the current cash and float balances based on transactions.
        
        Deposit (Cash In): Physical Cash ↑ | Digital Float ↓
        Withdrawal (Cash Out): Physical Cash ↓ | Digital Float ↑
        
        Returns dict with cash_balance and float_balance.
        """
        result = self.aggregate(
            # Deposits increase cash, withdrawals decrease cash
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
            # Withdrawals increase float balance (we received e-money)
            # Deposits decrease float balance (we sent e-money)
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
