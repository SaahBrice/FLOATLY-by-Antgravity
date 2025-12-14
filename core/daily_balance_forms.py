"""
Forms for Daily Opening Balance (Start Day) functionality.
"""

from decimal import Decimal
from django import forms
from django.core.validators import MinValueValidator

from .models import Network, DailyOpeningBalance


class StartDayForm(forms.Form):
    """
    Form for setting/editing daily opening balances.
    
    Includes:
    - Opening cash balance
    - Per-network float balances (dynamically added)
    - Adjustment reason (if editing)
    - Additional notes
    """
    
    ADJUSTMENT_CHOICES = [
        ('', 'No adjustment needed'),
        ('CASH_INJECTION', 'Cash Injection'),
        ('DISCREPANCY', 'Discrepancy Correction'),
        ('FLOAT_RECHARGE', 'Float Recharge'),
        ('OTHER', 'Other'),
    ]
    
    opening_cash = forms.DecimalField(
        label='Opening Cash (CFA)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-input text-2xl font-bold text-center py-4',
            'placeholder': '0',
            'inputmode': 'numeric',
        })
    )
    
    adjustment_reason = forms.ChoiceField(
        label='Adjustment Reason',
        choices=ADJUSTMENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-input',
        })
    )
    
    adjustment_notes = forms.CharField(
        label='Additional Notes',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 2,
            'placeholder': 'Optional: explain the adjustment...',
        })
    )
    
    def __init__(self, *args, networks=None, opening_balance=None, **kwargs):
        """
        Initialize form with dynamic network float fields.
        
        Args:
            networks: Queryset of active networks
            opening_balance: Existing DailyOpeningBalance instance (for editing)
        """
        super().__init__(*args, **kwargs)
        
        self.networks = networks or Network.objects.filter(is_active=True)
        self.opening_balance = opening_balance
        
        # Get existing network float values if editing
        existing_floats = {}
        if opening_balance:
            for nf in opening_balance.network_floats.all():
                existing_floats[nf.network_id] = nf.opening_float
        
        # Add a field for each network's float
        for network in self.networks:
            field_name = f'float_{network.id}'
            initial_value = existing_floats.get(network.id, Decimal('0'))
            
            self.fields[field_name] = forms.DecimalField(
                label=f'{network.name} Float',
                max_digits=12,
                decimal_places=2,
                validators=[MinValueValidator(Decimal('0'))],
                initial=initial_value,
                widget=forms.NumberInput(attrs={
                    'class': 'form-input font-semibold',
                    'placeholder': '0',
                    'inputmode': 'numeric',
                    'data-network-id': network.id,
                    'data-network-code': network.code,
                    'style': f'border-left: 4px solid {network.color};',
                })
            )
    
    def get_network_float_fields(self):
        """Get all network float fields for template iteration."""
        for network in self.networks:
            field_name = f'float_{network.id}'
            yield {
                'network': network,
                'field': self[field_name],
            }
    
    def clean(self):
        """Validate all float fields have values."""
        cleaned_data = super().clean()
        
        for network in self.networks:
            field_name = f'float_{network.id}'
            if field_name not in cleaned_data or cleaned_data[field_name] is None:
                cleaned_data[field_name] = Decimal('0')
        
        return cleaned_data
    
    def get_float_data(self):
        """Get cleaned float data as dict of {network_id: value}."""
        result = {}
        for network in self.networks:
            field_name = f'float_{network.id}'
            result[network.id] = self.cleaned_data.get(field_name, Decimal('0'))
        return result
