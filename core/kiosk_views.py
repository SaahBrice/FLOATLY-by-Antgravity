"""
Kiosk management views for Floatly.

Handles:
- Edit kiosk details
- Delete kiosk (owner only)
"""

import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.contrib import messages
from django.db.models import Sum, Count
from django import forms

from .models import Kiosk, KioskMember, Transaction

# Logger for kiosk operations
logger = logging.getLogger('core')


class KioskEditForm(forms.ModelForm):
    """Simple form for editing kiosk name and location."""
    
    class Meta:
        model = Kiosk
        fields = ['name', 'location']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Kiosk name',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Location (optional)',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].required = False


class EditKioskView(LoginRequiredMixin, FormView):
    """
    Edit kiosk details.
    Only owner can edit.
    """
    template_name = 'kiosks/edit.html'
    form_class = KioskEditForm
    login_url = '/auth/login/'
    
    def dispatch(self, request, *args, **kwargs):
        self.kiosk = get_object_or_404(Kiosk, slug=kwargs.get('slug'))
        
        logger.debug(f"EditKioskView dispatch: kiosk={self.kiosk.name}, user={request.user.email}")
        
        # Only owner can edit
        if self.kiosk.owner != request.user:
            logger.warning(f"Kiosk edit denied: user={request.user.email}, kiosk={self.kiosk.name}")
            raise Http404("Only the kiosk owner can edit")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.kiosk  # Pass existing kiosk for editing
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit {self.kiosk.name}'
        context['kiosk'] = self.kiosk
        context['is_edit'] = True
        return context
    
    def form_valid(self, form):
        # Store old name for logging
        old_name = self.kiosk.name
        
        # Save the form (updates the kiosk)
        kiosk = form.save()
        
        logger.info(
            f"Kiosk edited: user={self.request.user.email}, "
            f"old_name={old_name}, new_name={kiosk.name}, "
            f"location={kiosk.location}"
        )
        
        messages.success(self.request, f'✅ Kiosk "{kiosk.name}" updated!')
        
        return redirect('core:dashboard')


class DeleteKioskView(LoginRequiredMixin, View):
    """
    Delete a kiosk with confirmation.
    Only owner can delete.
    Shows warning about transactions that will be deleted.
    """
    login_url = '/auth/login/'
    
    def get(self, request, slug):
        """Show confirmation page with stats."""
        kiosk = get_object_or_404(Kiosk, slug=slug)
        
        # Only owner can delete
        if kiosk.owner != request.user:
            raise Http404("Only the kiosk owner can delete")
        
        # Get transaction stats
        tx_count = kiosk.transactions.count()
        tx_totals = kiosk.transactions.aggregate(
            total_amount=Sum('amount'),
            total_profit=Sum('profit')
        )
        
        return render(request, 'kiosks/delete_confirm.html', {
            'page_title': 'Delete Kiosk',
            'kiosk': kiosk,
            'transaction_count': tx_count,
            'total_amount': tx_totals['total_amount'] or Decimal('0'),
            'total_profit': tx_totals['total_profit'] or Decimal('0'),
        })
    
    def post(self, request, slug):
        """Delete the kiosk."""
        kiosk = get_object_or_404(Kiosk, slug=slug)
        
        # Only owner can delete
        if kiosk.owner != request.user:
            logger.warning(
                f"Unauthorized kiosk delete attempt: user={request.user.email}, "
                f"kiosk={kiosk.name}"
            )
            raise Http404("Only the kiosk owner can delete")
        
        # Store details for logging
        kiosk_details = {
            'name': kiosk.name,
            'location': kiosk.location,
            'transaction_count': kiosk.transactions.count(),
        }
        
        kiosk_name = kiosk.name
        kiosk.delete()
        
        logger.info(
            f"Kiosk deleted: user={request.user.email}, details={kiosk_details}"
        )
        
        messages.success(request, f'🗑️ Kiosk "{kiosk_name}" deleted successfully.')
        
        return redirect('core:dashboard')
