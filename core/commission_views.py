"""
Views for managing agent commission rates.
"""

import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.contrib import messages

from .models import Kiosk, KioskMember, Network, AgentCommissionRate

logger = logging.getLogger('core')


class CommissionRatesView(LoginRequiredMixin, View):
    """
    View for managing agent commission rates per kiosk.
    Shows all rates for the active kiosk grouped by network and transaction type.
    """
    template_name = 'settings/commission_rates.html'
    login_url = '/auth/login/'
    
    def get_active_kiosk(self, user, kiosk_slug=None):
        """Get the active kiosk for the user."""
        if kiosk_slug:
            kiosk = get_object_or_404(Kiosk, slug=kiosk_slug, is_active=True)
        else:
            kiosk = Kiosk.objects.filter(owner=user, is_active=True).first()
        
        if not kiosk:
            raise Http404("No kiosk found")
        
        # Verify user is owner (only owners can edit rates)
        if kiosk.owner != user:
            raise Http404("Only kiosk owners can edit commission rates")
        
        return kiosk
    
    def get(self, request, slug=None):
        """Display commission rates for the kiosk."""
        kiosk = self.get_active_kiosk(request.user, slug)
        networks = Network.objects.filter(is_active=True)
        
        # Organize rates by network and transaction type
        rates_by_network = {}
        for network in networks:
            rates_by_network[network.id] = {
                'network': network,
                'deposit_rates': AgentCommissionRate.objects.filter(
                    kiosk=kiosk,
                    network=network,
                    transaction_type='DEPOSIT',
                    is_active=True
                ).order_by('min_amount'),
                'withdrawal_rates': AgentCommissionRate.objects.filter(
                    kiosk=kiosk,
                    network=network,
                    transaction_type='WITHDRAWAL',
                    is_active=True
                ).order_by('min_amount'),
            }
        
        context = {
            'page_title': 'Commission Rates',
            'kiosk': kiosk,
            'networks': networks,
            'rates_by_network': rates_by_network,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, slug=None):
        """Save a commission rate."""
        kiosk = self.get_active_kiosk(request.user, slug)
        
        # Parse form data
        network_id = request.POST.get('network_id')
        transaction_type = request.POST.get('transaction_type')
        min_amount = request.POST.get('min_amount', '0')
        max_amount = request.POST.get('max_amount', '0')
        rate_type = request.POST.get('rate_type', 'PERCENTAGE')
        rate_value = request.POST.get('rate_value', '0')
        rate_id = request.POST.get('rate_id')  # For editing existing rate
        
        try:
            network = Network.objects.get(id=network_id, is_active=True)
            
            if rate_id:
                # Update existing rate
                rate = AgentCommissionRate.objects.get(id=rate_id, kiosk=kiosk)
                rate.min_amount = Decimal(min_amount)
                rate.max_amount = Decimal(max_amount)
                rate.rate_type = rate_type
                rate.rate_value = Decimal(rate_value)
                rate.save()
                messages.success(request, 'Commission rate updated!')
            else:
                # Create new rate
                AgentCommissionRate.objects.create(
                    kiosk=kiosk,
                    network=network,
                    transaction_type=transaction_type,
                    min_amount=Decimal(min_amount),
                    max_amount=Decimal(max_amount),
                    rate_type=rate_type,
                    rate_value=Decimal(rate_value),
                )
                messages.success(request, 'Commission rate added!')
                
        except Network.DoesNotExist:
            messages.error(request, 'Invalid network selected')
        except AgentCommissionRate.DoesNotExist:
            messages.error(request, 'Rate not found')
        except Exception as e:
            logger.error(f"Error saving commission rate: {e}")
            messages.error(request, 'Failed to save commission rate')
        
        return redirect('core:commission_rates')


class DeleteCommissionRateView(LoginRequiredMixin, View):
    """Delete a commission rate."""
    login_url = '/auth/login/'
    
    def post(self, request, pk):
        try:
            rate = AgentCommissionRate.objects.get(pk=pk)
            
            # Verify ownership
            if rate.kiosk.owner != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            rate.delete()
            messages.success(request, 'Commission rate deleted!')
            
        except AgentCommissionRate.DoesNotExist:
            messages.error(request, 'Rate not found')
        
        return redirect('core:commission_rates')
