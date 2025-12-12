"""
Transaction forms for Floatly.

Forms include:
- TransactionForm: Main transaction entry form
- QuickTransactionForm: Minimal fields for fast entry
"""

from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal

from .models import Transaction, Network, Kiosk


class TransactionForm(forms.ModelForm):
    """
    Full transaction form with all fields.
    """
    
    class Meta:
        model = Transaction
        fields = [
            'network',
            'transaction_type',
            'amount',
            'profit',
            'customer_phone',
            'transaction_ref',
            'notes',
            'sms_text',
        ]
        widgets = {
            'network': forms.Select(attrs={
                'class': 'form-select',
                'hx-get': '/transactions/calculate-profit/',
                'hx-trigger': 'change',
                'hx-target': '#profit-container',
                'hx-include': '[name=amount], [name=transaction_type]',
            }),
            'transaction_type': forms.RadioSelect(attrs={
                'class': 'hidden peer',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input text-2xl font-bold text-center',
                'placeholder': '0',
                'inputmode': 'numeric',
                'min': '1',
                'step': '1',
                'hx-get': '/transactions/calculate-profit/',
                'hx-trigger': 'keyup changed delay:300ms',
                'hx-target': '#profit-container',
                'hx-include': '[name=network], [name=transaction_type]',
            }),
            'profit': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Auto-calculated',
                'inputmode': 'numeric',
                'step': '1',
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+237...',
                'inputmode': 'tel',
                'autocomplete': 'tel',
            }),
            'transaction_ref': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Transaction ID from receipt',
                'autocomplete': 'off',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Any notes about this transaction...',
                'rows': 2,
            }),
            'sms_text': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        self.kiosk = kwargs.pop('kiosk', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show active networks
        self.fields['network'].queryset = Network.objects.filter(is_active=True)
        
        # Set transaction type choices
        self.fields['transaction_type'].choices = [
            ('DEPOSIT', 'Cash In (Deposit)'),
            ('WITHDRAWAL', 'Cash Out (Withdrawal)'),
        ]
        
        # Make optional fields not required
        self.fields['customer_phone'].required = False
        self.fields['transaction_ref'].required = False
        self.fields['notes'].required = False
        self.fields['sms_text'].required = False
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount < Decimal('1'):
            raise forms.ValidationError('Amount must be at least 1 CFA.')
        return amount
    
    def save(self, commit=True):
        transaction = super().save(commit=False)
        
        if self.kiosk:
            transaction.kiosk = self.kiosk
        if self.user:
            transaction.recorded_by = self.user
        
        # Check if profit was manually edited
        original_profit = self.initial.get('profit')
        if original_profit and transaction.profit != Decimal(str(original_profit)):
            transaction.profit_was_edited = True
        
        if commit:
            transaction.save()
        
        return transaction


class QuickTransactionForm(forms.Form):
    """
    Minimal form for quick transaction entry.
    Just network, type, and amount - profit calculated automatically.
    """
    
    network = forms.ModelChoiceField(
        queryset=Network.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    transaction_type = forms.ChoiceField(
        choices=[
            ('DEPOSIT', 'Cash In'),
            ('WITHDRAWAL', 'Cash Out'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'hidden peer',
        })
    )
    
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-input text-2xl font-bold text-center',
            'placeholder': '0',
            'inputmode': 'numeric',
        })
    )
