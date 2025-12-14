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
