"""
Transaction model for Floatly.

Records every money movement in the system with auto-calculated profit.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from ..managers import TransactionManager
from .user import phone_validator


# =============================================================================
# TRANSACTION MODEL
# =============================================================================

class Transaction(models.Model):
    """
    Every money movement recorded in the system.
    The most critical table - needs good indexing for performance.
    """
    
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit (Cash In)'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal (Cash Out)'
        PROFIT_WITHDRAWAL = 'PROFIT_WITHDRAWAL', 'Profit Withdrawal'
    
    # Relationships
    kiosk = models.ForeignKey(
        'Kiosk',
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text='Which kiosk this transaction belongs to'
    )
    recorded_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_transactions',
        help_text='The agent who recorded this transaction'
    )
    network = models.ForeignKey(
        'Network',
        on_delete=models.PROTECT,
        related_name='transactions',
        help_text='Which mobile network was used'
    )
    
    # Transaction details
    transaction_type = models.CharField(
        'type',
        max_length=20,
        choices=TransactionType.choices,
        help_text='Deposit = customer sending money, Withdrawal = customer taking cash'
    )
    amount = models.DecimalField(
        'amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Transaction amount in CFA'
    )
    
    # Profit tracking (both calculated and actual)
    calculated_profit = models.DecimalField(
        'calculated profit',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Auto-calculated commission based on rate rules'
    )
    profit = models.DecimalField(
        'actual profit',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Final profit (can be edited by user)'
    )
    profit_was_edited = models.BooleanField(
        'profit was edited',
        default=False,
        help_text='Was the profit manually overridden?'
    )
    
    # Customer information (optional)
    customer_phone = models.CharField(
        'customer phone',
        max_length=20,
        blank=True,
        validators=[phone_validator],
        help_text='Customer phone number if known'
    )
    customer_name = models.CharField(
        'customer name',
        max_length=100,
        blank=True,
        help_text='Customer/sender name if known'
    )
    transaction_ref = models.CharField(
        'transaction reference',
        max_length=100,
        blank=True,
        help_text='Transaction ID from the receipt'
    )
    
    # Additional details
    notes = models.TextField(
        'notes',
        blank=True,
        help_text='Any additional notes about this transaction'
    )
    receipt_photo = models.ImageField(
        'receipt photo',
        upload_to='receipts/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text='Photo of the transaction receipt'
    )
    sms_text = models.TextField(
        'SMS text',
        blank=True,
        help_text='Full text message from the receipt if shared'
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        'transaction time',
        default=timezone.now,
        db_index=True,
        help_text='When the transaction occurred'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )
    
    objects = TransactionManager()
    
    class Meta:
        verbose_name = 'transaction'
        verbose_name_plural = 'transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['kiosk', '-timestamp']),
            models.Index(fields=['recorded_by', '-timestamp']),
            models.Index(fields=['network', 'transaction_type']),
            models.Index(fields=['customer_phone']),
            models.Index(fields=['transaction_ref']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} CFA @ {self.kiosk.name}"
    
    def save(self, *args, **kwargs):
        """
        Auto-calculate profit based on transaction type and agent's commission rates.
        
        For DEPOSITS: profit = agent's commission (% of amount or fixed)
        For WITHDRAWALS: profit = agent's share of network fee
        For PROFIT_WITHDRAWAL: no profit calculation needed
        """
        from .network import CommissionRate, AgentCommissionRate
        
        # Calculate commission if this is a new transaction or amount changed
        is_new = self.pk is None
        
        if is_new or not self.profit_was_edited:
            # Skip profit calculation for profit withdrawal transactions
            if self.transaction_type == self.TransactionType.PROFIT_WITHDRAWAL:
                self.calculated_profit = Decimal('0')
                if not self.profit_was_edited:
                    self.profit = Decimal('0')
            else:
                # Try to use agent-specific rate first
                profit = AgentCommissionRate.calculate_agent_profit(
                    kiosk=self.kiosk,
                    network=self.network,
                    transaction_type=self.transaction_type,
                    amount=self.amount
                )
                
                if profit > Decimal('0'):
                    self.calculated_profit = profit
                    if not self.profit_was_edited:
                        self.profit = profit
                else:
                    # Fallback to old CommissionRate (for backward compatibility)
                    rate = CommissionRate.get_rate_for_amount(self.network, self.amount)
                    if rate:
                        self.calculated_profit = rate.calculate_commission(self.amount)
                        if not self.profit_was_edited:
                            self.profit = self.calculated_profit
                    else:
                        self.calculated_profit = Decimal('0')
                        if not self.profit_was_edited:
                            self.profit = Decimal('0')
        
        super().save(*args, **kwargs)
    
    @property
    def is_deposit(self):
        return self.transaction_type == self.TransactionType.DEPOSIT
    
    @property
    def is_withdrawal(self):
        return self.transaction_type == self.TransactionType.WITHDRAWAL
