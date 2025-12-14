"""
Daily Opening Balance models for Floatly.

Tracks the opening cash and float balances for each kiosk at the start of each day.
This provides the baseline for all daily balance calculations.
"""

from decimal import Decimal
from django.db import models
from django.utils import timezone


class DailyOpeningBalance(models.Model):
    """
    Stores the opening cash balance for a kiosk on a specific date.
    One record per kiosk per day.
    
    Each day when an agent starts work, they confirm/adjust:
    - Opening cash in drawer
    - Opening float per network
    
    This resets the baseline for that day's calculations.
    """
    
    class AdjustmentReason(models.TextChoices):
        NONE = '', 'No adjustment'
        CASH_INJECTION = 'CASH_INJECTION', 'Cash Injection'
        DISCREPANCY = 'DISCREPANCY', 'Discrepancy Correction'
        FLOAT_RECHARGE = 'FLOAT_RECHARGE', 'Float Recharge'
        OTHER = 'OTHER', 'Other'
    
    kiosk = models.ForeignKey(
        'Kiosk',
        on_delete=models.CASCADE,
        related_name='daily_balances',
        help_text='Which kiosk this opening balance belongs to'
    )
    date = models.DateField(
        'date',
        db_index=True,
        help_text='The date for this opening balance'
    )
    opening_cash = models.DecimalField(
        'opening cash',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Cash in drawer at start of day'
    )
    adjustment_reason = models.CharField(
        'adjustment reason',
        max_length=20,
        choices=AdjustmentReason.choices,
        blank=True,
        default='',
        help_text='Why the opening balance differs from yesterday\'s closing'
    )
    adjustment_notes = models.TextField(
        'adjustment notes',
        blank=True,
        help_text='Additional notes about the adjustment'
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='started_days',
        help_text='The user who set this opening balance'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'daily opening balance'
        verbose_name_plural = 'daily opening balances'
        ordering = ['-date']
        unique_together = ['kiosk', 'date']
        indexes = [
            models.Index(fields=['kiosk', '-date']),
        ]
    
    def __str__(self):
        return f"{self.kiosk.name} - {self.date} (Cash: {self.opening_cash})"
    
    @classmethod
    def get_or_create_today(cls, kiosk, user=None):
        """
        Get today's opening balance or create one with yesterday's closing.
        Returns (instance, created) tuple.
        """
        today = timezone.now().date()
        
        try:
            return cls.objects.get(kiosk=kiosk, date=today), False
        except cls.DoesNotExist:
            # Calculate yesterday's closing balance
            yesterday_closing = cls.get_previous_day_closing(kiosk, today)
            
            instance = cls.objects.create(
                kiosk=kiosk,
                date=today,
                opening_cash=yesterday_closing.get('cash', Decimal('0')),
                created_by=user
            )
            
            # Create network float balances
            from .network import Network
            for network in Network.objects.filter(is_active=True):
                NetworkFloatBalance.objects.create(
                    daily_balance=instance,
                    network=network,
                    opening_float=yesterday_closing.get('floats', {}).get(network.id, Decimal('0'))
                )
            
            return instance, True
    
    @classmethod
    def get_previous_day_closing(cls, kiosk, current_date):
        """
        Calculate the closing balance from the previous day.
        This is opening balance + day's transactions.
        """
        from datetime import timedelta
        from .transaction import Transaction
        
        yesterday = current_date - timedelta(days=1)
        
        # Try to get yesterday's opening balance
        try:
            yesterday_opening = cls.objects.get(kiosk=kiosk, date=yesterday)
            opening_cash = yesterday_opening.opening_cash
            
            # Get per-network opening floats
            opening_floats = {
                nf.network_id: nf.opening_float 
                for nf in yesterday_opening.network_floats.all()
            }
        except cls.DoesNotExist:
            # No opening balance yesterday, start from zero or recurse
            opening_cash = Decimal('0')
            opening_floats = {}
        
        # Calculate yesterday's transaction deltas
        yesterday_transactions = Transaction.objects.filter(
            kiosk=kiosk,
            timestamp__date=yesterday
        )
        
        # Cash delta: deposits add, withdrawals subtract
        from django.db.models import Sum, Case, When, F, DecimalField
        from django.db.models.functions import Coalesce
        
        cash_delta = yesterday_transactions.aggregate(
            delta=Coalesce(
                Sum(
                    Case(
                        When(transaction_type='DEPOSIT', then=F('amount')),
                        When(transaction_type='WITHDRAWAL', then=-F('amount')),
                        default=Decimal('0'),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ),
                Decimal('0')
            )
        )['delta']
        
        # Float delta per network: withdrawals add, deposits subtract
        from .network import Network
        float_deltas = {}
        for network in Network.objects.filter(is_active=True):
            network_transactions = yesterday_transactions.filter(network=network)
            float_delta = network_transactions.aggregate(
                delta=Coalesce(
                    Sum(
                        Case(
                            When(transaction_type='WITHDRAWAL', then=F('amount')),
                            When(transaction_type='DEPOSIT', then=-F('amount')),
                            default=Decimal('0'),
                            output_field=DecimalField(max_digits=12, decimal_places=2)
                        )
                    ),
                    Decimal('0')
                )
            )['delta']
            
            opening_float = opening_floats.get(network.id, Decimal('0'))
            float_deltas[network.id] = opening_float + float_delta
        
        return {
            'cash': opening_cash + cash_delta,
            'floats': float_deltas
        }
    
    @property
    def total_opening_float(self):
        """Sum of all network opening floats."""
        return sum(nf.opening_float for nf in self.network_floats.all())


class NetworkFloatBalance(models.Model):
    """
    Stores opening float balance per network for a specific day.
    Linked to DailyOpeningBalance.
    
    Each network (MTN, Orange, etc.) has its own float balance that
    is tracked separately.
    """
    
    daily_balance = models.ForeignKey(
        DailyOpeningBalance,
        on_delete=models.CASCADE,
        related_name='network_floats',
        help_text='The daily balance this belongs to'
    )
    network = models.ForeignKey(
        'Network',
        on_delete=models.CASCADE,
        related_name='float_balances',
        help_text='Which network this float balance is for'
    )
    opening_float = models.DecimalField(
        'opening float',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Float balance for this network at start of day'
    )
    
    class Meta:
        verbose_name = 'network float balance'
        verbose_name_plural = 'network float balances'
        unique_together = ['daily_balance', 'network']
    
    def __str__(self):
        return f"{self.daily_balance.kiosk.name} - {self.daily_balance.date} - {self.network.code}: {self.opening_float}"
