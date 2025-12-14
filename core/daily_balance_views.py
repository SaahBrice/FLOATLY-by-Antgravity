"""
Views for Daily Opening Balance (Start Day) functionality.
"""

import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.utils import timezone

from .models import Kiosk, KioskMember, Network, DailyOpeningBalance, NetworkFloatBalance
from .daily_balance_forms import StartDayForm

logger = logging.getLogger('core')


class StartDayView(LoginRequiredMixin, View):
    """
    Handle Start Day functionality.
    
    GET: Show form to set/edit opening balances
    POST: Save opening balances
    
    Pre-populates with yesterday's closing balance.
    Shows warning if already started today.
    """
    template_name = 'daily_balance/start_day.html'
    login_url = '/auth/login/'
    
    def get_active_kiosk(self, user, kiosk_slug=None):
        """Get the active kiosk for the user."""
        if kiosk_slug:
            kiosk = get_object_or_404(Kiosk, slug=kiosk_slug, is_active=True)
        else:
            # Get first owned or member kiosk
            owned = Kiosk.objects.filter(owner=user, is_active=True).first()
            member = Kiosk.objects.filter(
                members__user=user, is_active=True
            ).exclude(owner=user).first()
            kiosk = owned or member
        
        if not kiosk:
            raise Http404("No kiosk found")
        
        # Verify access
        is_owner = kiosk.owner == user
        is_member = KioskMember.objects.filter(kiosk=kiosk, user=user).exists()
        if not is_owner and not is_member:
            raise Http404("Access denied")
        
        return kiosk
    
    def get(self, request, slug=None):
        """Show Start Day form."""
        kiosk = self.get_active_kiosk(request.user, slug)
        today = timezone.now().date()
        
        # Check if already started today
        try:
            existing = DailyOpeningBalance.objects.get(kiosk=kiosk, date=today)
            already_started = True
        except DailyOpeningBalance.DoesNotExist:
            existing = None
            already_started = False
        
        # Get yesterday's closing balance for defaults
        if existing:
            # Use existing values
            initial_cash = existing.opening_cash
        else:
            # Calculate from yesterday's closing
            closing = DailyOpeningBalance.get_previous_day_closing(kiosk, today)
            initial_cash = closing.get('cash', Decimal('0'))
        
        networks = Network.objects.filter(is_active=True)
        
        form = StartDayForm(
            networks=networks,
            opening_balance=existing,
            initial={
                'opening_cash': initial_cash,
                'adjustment_reason': existing.adjustment_reason if existing else '',
                'adjustment_notes': existing.adjustment_notes if existing else '',
            }
        )
        
        context = {
            'page_title': 'Start Day',
            'kiosk': kiosk,
            'form': form,
            'already_started': already_started,
            'existing_balance': existing,
            'today': today,
            'networks': networks,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, slug=None):
        """Save Start Day balances."""
        kiosk = self.get_active_kiosk(request.user, slug)
        today = timezone.now().date()
        networks = Network.objects.filter(is_active=True)
        
        # Check if already exists
        try:
            existing = DailyOpeningBalance.objects.get(kiosk=kiosk, date=today)
            is_update = True
        except DailyOpeningBalance.DoesNotExist:
            existing = None
            is_update = False
        
        form = StartDayForm(
            request.POST,
            networks=networks,
            opening_balance=existing,
        )
        
        if form.is_valid():
            if existing:
                # Update existing
                existing.opening_cash = form.cleaned_data['opening_cash']
                existing.adjustment_reason = form.cleaned_data.get('adjustment_reason', '')
                existing.adjustment_notes = form.cleaned_data.get('adjustment_notes', '')
                existing.save()
                
                # Update network floats
                float_data = form.get_float_data()
                for network_id, opening_float in float_data.items():
                    NetworkFloatBalance.objects.update_or_create(
                        daily_balance=existing,
                        network_id=network_id,
                        defaults={'opening_float': opening_float}
                    )
                
                logger.info(f"Start Day updated: kiosk={kiosk.name}, user={request.user.email}")
                messages.success(request, 'Opening balances updated successfully!')
            else:
                # Create new
                opening = DailyOpeningBalance.objects.create(
                    kiosk=kiosk,
                    date=today,
                    opening_cash=form.cleaned_data['opening_cash'],
                    adjustment_reason=form.cleaned_data.get('adjustment_reason', ''),
                    adjustment_notes=form.cleaned_data.get('adjustment_notes', ''),
                    created_by=request.user,
                )
                
                # Create network floats
                float_data = form.get_float_data()
                for network_id, opening_float in float_data.items():
                    NetworkFloatBalance.objects.create(
                        daily_balance=opening,
                        network_id=network_id,
                        opening_float=opening_float,
                    )
                
                logger.info(f"Start Day created: kiosk={kiosk.name}, user={request.user.email}")
                messages.success(request, 'Day started successfully! Opening balances saved.')
            
            return redirect('core:dashboard')
        
        # Form validation failed
        context = {
            'page_title': 'Start Day',
            'kiosk': kiosk,
            'form': form,
            'already_started': is_update,
            'existing_balance': existing,
            'today': today,
            'networks': networks,
        }
        return render(request, self.template_name, context)


class StartDayStatusView(LoginRequiredMixin, View):
    """
    API endpoint to check if day has been started for a kiosk.
    Returns JSON with status.
    """
    login_url = '/auth/login/'
    
    def get(self, request):
        kiosk_slug = request.GET.get('kiosk')
        
        if kiosk_slug:
            kiosk = get_object_or_404(Kiosk, slug=kiosk_slug, is_active=True)
        else:
            kiosk = Kiosk.objects.filter(owner=request.user, is_active=True).first()
        
        if not kiosk:
            return JsonResponse({'error': 'No kiosk found'}, status=404)
        
        today = timezone.now().date()
        
        try:
            opening = DailyOpeningBalance.objects.get(kiosk=kiosk, date=today)
            return JsonResponse({
                'started': True,
                'opening_cash': float(opening.opening_cash),
                'total_float': float(opening.total_opening_float),
                'date': str(today),
            })
        except DailyOpeningBalance.DoesNotExist:
            # Calculate default from yesterday
            closing = DailyOpeningBalance.get_previous_day_closing(kiosk, today)
            return JsonResponse({
                'started': False,
                'suggested_cash': float(closing.get('cash', 0)),
                'suggested_floats': {k: float(v) for k, v in closing.get('floats', {}).items()},
                'date': str(today),
            })
