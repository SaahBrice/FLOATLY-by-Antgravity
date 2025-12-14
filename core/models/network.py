"""
Network and CommissionRate models for Floatly.

Mobile money network definitions and commission rules.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


# =============================================================================
# NETWORK MODEL
# =============================================================================

class Network(models.Model):
    """
    Mobile money network (MTN, Orange, etc.)
    Used for transaction categorization and commission rate lookup.
    """
    
    name = models.CharField(
        'network name',
        max_length=50,
        unique=True,
        help_text='e.g., MTN Mobile Money, Orange Money'
    )
    code = models.CharField(
        'network code',
        max_length=10,
        unique=True,
        help_text='Short code like MTN, OM, EU'
    )
    color = models.CharField(
        'brand color',
        max_length=7,
        default='#3b82f6',
        help_text='Hex color for UI display, e.g., #ffcc00 for MTN'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this network currently supported?'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'network'
        verbose_name_plural = 'networks'
        ordering = ['name']
    
    def __str__(self):
        return self.name


# =============================================================================
# COMMISSION RATE MODEL
# =============================================================================

class CommissionRate(models.Model):
    """
    Commission rules for each network based on transaction amount ranges.
    Commissions can be fixed amounts or percentages.
    """
    
    class RateType(models.TextChoices):
        FIXED = 'FIXED', 'Fixed Amount'
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
    
    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        related_name='commission_rates',
        help_text='Which network this rate applies to'
    )
    min_amount = models.DecimalField(
        'minimum amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Minimum transaction amount for this rate (inclusive)'
    )
    max_amount = models.DecimalField(
        'maximum amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Maximum transaction amount for this rate (inclusive)'
    )
    rate_type = models.CharField(
        'rate type',
        max_length=15,
        choices=RateType.choices,
        default=RateType.FIXED,
        help_text='Is the commission a fixed amount or percentage?'
    )
    rate_value = models.DecimalField(
        'rate value',
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Fixed amount in CFA or percentage (e.g., 0.3 for 0.3%)'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this rate currently in effect?'
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
        verbose_name = 'commission rate'
        verbose_name_plural = 'commission rates'
        ordering = ['network', 'min_amount']
        indexes = [
            models.Index(fields=['network', 'is_active']),
            models.Index(fields=['min_amount', 'max_amount']),
        ]
    
    def __str__(self):
        rate_display = (
            f"{self.rate_value} CFA" if self.rate_type == self.RateType.FIXED 
            else f"{self.rate_value}%"
        )
        return f"{self.network.code}: {self.min_amount}-{self.max_amount} → {rate_display}"
    
    def calculate_commission(self, amount):
        """Calculate commission for a given amount."""
        if self.rate_type == self.RateType.FIXED:
            return self.rate_value
        else:
            # Percentage calculation
            return (amount * self.rate_value / Decimal('100')).quantize(Decimal('0.01'))
    
    @classmethod
    def get_rate_for_amount(cls, network, amount):
        """
        Find the matching commission rate for a network and amount.
        Returns the CommissionRate object or None if not found.
        """
        return cls.objects.filter(
            network=network,
            is_active=True,
            min_amount__lte=amount,
            max_amount__gte=amount
        ).first()


# =============================================================================
# AGENT COMMISSION RATE MODEL
# =============================================================================

class AgentCommissionRate(models.Model):
    """
    Agent-specific commission rates per kiosk, network, and transaction type.
    
    For DEPOSITS: Agent's commission from network (% of amount or fixed)
    For WITHDRAWALS: Agent's share of network's fee (% of fee or fixed)
    """
    
    class RateType(models.TextChoices):
        FIXED = 'FIXED', 'Fixed Amount'
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
    
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit (Cash In)'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal (Cash Out)'
    
    kiosk = models.ForeignKey(
        'Kiosk',
        on_delete=models.CASCADE,
        related_name='agent_commission_rates',
        help_text='Which kiosk/agent this rate applies to'
    )
    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        related_name='agent_commission_rates',
        help_text='Which network this rate applies to'
    )
    transaction_type = models.CharField(
        'transaction type',
        max_length=15,
        choices=TransactionType.choices,
        help_text='Does this rate apply to deposits or withdrawals?'
    )
    min_amount = models.DecimalField(
        'minimum amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Minimum transaction amount for this rate (inclusive)'
    )
    max_amount = models.DecimalField(
        'maximum amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Maximum transaction amount for this rate (inclusive)'
    )
    rate_type = models.CharField(
        'rate type',
        max_length=15,
        choices=RateType.choices,
        default=RateType.PERCENTAGE,
        help_text='Is the commission a fixed amount or percentage?'
    )
    rate_value = models.DecimalField(
        'rate value',
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='For deposits: % of amount or fixed. For withdrawals: % of network fee or fixed.'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this rate currently in effect?'
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
        verbose_name = 'agent commission rate'
        verbose_name_plural = 'agent commission rates'
        ordering = ['kiosk', 'network', 'transaction_type', 'min_amount']
        indexes = [
            models.Index(fields=['kiosk', 'network', 'transaction_type', 'is_active']),
            models.Index(fields=['min_amount', 'max_amount']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['kiosk', 'network', 'transaction_type', 'min_amount', 'max_amount'],
                name='unique_agent_rate_range'
            )
        ]
    
    def __str__(self):
        rate_display = (
            f"{self.rate_value} CFA" if self.rate_type == self.RateType.FIXED 
            else f"{self.rate_value}%"
        )
        return f"{self.kiosk.name} - {self.network.code} {self.transaction_type}: {self.min_amount}-{self.max_amount} → {rate_display}"
    
    def calculate_profit(self, base_amount):
        """
        Calculate agent's profit.
        
        For DEPOSITS: base_amount = transaction amount
        For WITHDRAWALS: base_amount = network fee
        """
        if self.rate_type == self.RateType.FIXED:
            return self.rate_value
        else:
            # Percentage calculation
            return (base_amount * self.rate_value / Decimal('100')).quantize(Decimal('0.01'))
    
    @classmethod
    def get_rate_for_transaction(cls, kiosk, network, transaction_type, amount):
        """
        Find the matching agent commission rate.
        Returns the AgentCommissionRate object or None if not found.
        """
        return cls.objects.filter(
            kiosk=kiosk,
            network=network,
            transaction_type=transaction_type,
            is_active=True,
            min_amount__lte=amount,
            max_amount__gte=amount
        ).first()
    
    @classmethod
    def calculate_agent_profit(cls, kiosk, network, transaction_type, amount):
        """
        Calculate agent profit for a transaction.
        
        For DEPOSITS: Returns commission based on transaction amount
        For WITHDRAWALS: Returns share of network fee
        """
        agent_rate = cls.get_rate_for_transaction(kiosk, network, transaction_type, amount)
        
        if not agent_rate:
            return Decimal('0')
        
        if transaction_type == cls.TransactionType.DEPOSIT:
            # Direct commission from network
            return agent_rate.calculate_profit(amount)
        else:
            # Agent's share of network's fee
            network_fee_rate = CommissionRate.get_rate_for_amount(network, amount)
            if network_fee_rate:
                network_fee = network_fee_rate.calculate_commission(amount)
                return agent_rate.calculate_profit(network_fee)
            return Decimal('0')

