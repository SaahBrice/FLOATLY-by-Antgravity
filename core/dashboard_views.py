"""
Dashboard views for Floatly.

Main dashboard with:
- Balance calculations (cash/float)
- Today's statistics
- Recent transactions
- Kiosk switching via HTMX
"""

import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Kiosk, KioskMember, Transaction, Notification

# Logger for dashboard operations
logger = logging.getLogger('core')


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view with financial overview.
    """
    template_name = 'core/dashboard.html'
    login_url = '/auth/login/'
    
    def get_user_kiosks(self, user):
        """Get all kiosks user has access to."""
        owned = Kiosk.objects.filter(owner=user, is_active=True)
        member_of = Kiosk.objects.filter(
            members__user=user, is_active=True
        ).exclude(owner=user).distinct()
        return owned, member_of
    
    def get_active_kiosk(self, user, kiosk_slug=None):
        """
        Get the active kiosk based on URL param or default.
        Validates user has permission to access it.
        """
        owned, member_of = self.get_user_kiosks(user)
        all_kiosks = list(owned) + list(member_of)
        
        if not all_kiosks:
            return None
        
        # If specific kiosk requested via URL
        if kiosk_slug:
            for kiosk in all_kiosks:
                if kiosk.slug == kiosk_slug:
                    return kiosk
            # User doesn't have access to requested kiosk
            raise Http404("Kiosk not found or access denied")
        
        # Default to first kiosk
        return all_kiosks[0]
    
    def get_kiosk_stats(self, kiosk):
        """
        Calculate all statistics for a kiosk.
        Returns dict with balances, today's stats, and recent transactions.
        """
        if not kiosk:
            return {
                'cash_balance': Decimal('0'),
                'float_balance': Decimal('0'),
                'today_profit': Decimal('0'),
                'today_count': 0,
                'unread_alerts': 0,
                'recent_transactions': [],
            }
        
        # Get all transactions for balance calculation
        all_transactions = kiosk.transactions.all()
        
        # Calculate balances using the manager method
        balances = all_transactions.calculate_balances()
        
        # Today's transactions
        today = timezone.now().date()
        today_transactions = all_transactions.filter(
            timestamp__date=today
        )
        
        today_stats = today_transactions.aggregate(
            total_profit=Sum('profit'),
            count=Count('id')
        )
        
        # Recent transactions (last 5)
        recent = all_transactions.select_related('network', 'recorded_by')[:5]
        
        return {
            'cash_balance': balances.get('cash_balance', Decimal('0')),
            'float_balance': balances.get('float_balance', Decimal('0')),
            'today_profit': today_stats['total_profit'] or Decimal('0'),
            'today_count': today_stats['count'] or 0,
            'recent_transactions': recent,
        }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get kiosk from URL param
        kiosk_slug = self.request.GET.get('kiosk')
        
        # Get user's kiosks
        owned_kiosks, member_kiosks = self.get_user_kiosks(user)
        
        # Get active kiosk
        try:
            active_kiosk = self.get_active_kiosk(user, kiosk_slug)
        except Http404:
            active_kiosk = None
        
        # Get stats for active kiosk
        stats = self.get_kiosk_stats(active_kiosk)
        
        # Get unread notification count
        unread_count = Notification.objects.filter(
            user=user, is_read=False
        ).count()
        
        context.update({
            'page_title': 'Dashboard',
            'owned_kiosks': owned_kiosks,
            'member_kiosks': member_kiosks,
            'all_kiosks': list(owned_kiosks) + list(member_kiosks),
            'has_kiosks': owned_kiosks.exists() or member_kiosks.exists(),
            'active_kiosk': active_kiosk,
            'unread_notifications': unread_count,
            **stats,
        })
        
        return context
    
    def get(self, request, *args, **kwargs):
        """
        Handle GET request.
        If HTMX request, return partial template.
        """
        context = self.get_context_data(**kwargs)
        
        # Check if HTMX request for partial update
        if request.headers.get('HX-Request'):
            return render(request, 'core/partials/dashboard_content.html', context)
        
        return render(request, self.template_name, context)


class KioskSwitchView(LoginRequiredMixin, View):
    """
    HTMX endpoint for switching kiosks.
    Returns just the dashboard content partial.
    """
    login_url = '/auth/login/'
    
    def get(self, request, slug):
        user = request.user
        
        # Validate user has access to this kiosk
        kiosk = get_object_or_404(Kiosk, slug=slug, is_active=True)
        
        # Check ownership or membership
        is_owner = kiosk.owner == user
        is_member = KioskMember.objects.filter(kiosk=kiosk, user=user).exists()
        
        if not is_owner and not is_member:
            logger.warning(f"Kiosk access denied: user={user.email}, kiosk={kiosk.name}")
            raise Http404("Access denied")
        
        logger.info(f"Kiosk switched: user={user.email}, kiosk={kiosk.name}")
        
        # Get owned and member kiosks
        owned_kiosks = Kiosk.objects.filter(owner=user, is_active=True)
        member_kiosks = Kiosk.objects.filter(
            members__user=user, is_active=True
        ).exclude(owner=user).distinct()
        
        # Calculate stats
        all_transactions = kiosk.transactions.all()
        balances = all_transactions.calculate_balances()
        
        today = timezone.now().date()
        today_transactions = all_transactions.filter(timestamp__date=today)
        today_stats = today_transactions.aggregate(
            total_profit=Sum('profit'),
            count=Count('id')
        )
        
        recent = all_transactions.select_related('network', 'recorded_by')[:5]
        
        unread_count = Notification.objects.filter(
            user=user, is_read=False
        ).count()
        
        context = {
            'active_kiosk': kiosk,
            'owned_kiosks': owned_kiosks,
            'member_kiosks': member_kiosks,
            'all_kiosks': list(owned_kiosks) + list(member_kiosks),
            'cash_balance': balances.get('cash_balance', Decimal('0')),
            'float_balance': balances.get('float_balance', Decimal('0')),
            'today_profit': today_stats['total_profit'] or Decimal('0'),
            'today_count': today_stats['count'] or 0,
            'recent_transactions': recent,
            'unread_notifications': unread_count,
        }
        
        return render(request, 'core/partials/dashboard_content.html', context)


class ChartDataView(LoginRequiredMixin, View):
    """
    API endpoint for dashboard chart data.
    Returns JSON with daily stats for deposits, withdrawals, and profit.
    """
    login_url = '/auth/login/'
    
    def get(self, request):
        from django.http import JsonResponse
        from datetime import timedelta
        import json
        
        user = request.user
        kiosk_slug = request.GET.get('kiosk')
        period = request.GET.get('period', '7')  # days
        
        # Get kiosk
        if kiosk_slug:
            kiosk = get_object_or_404(Kiosk, slug=kiosk_slug)
        else:
            owned = Kiosk.objects.filter(owner=user, is_active=True).first()
            member = Kiosk.objects.filter(
                members__user=user, is_active=True
            ).exclude(owner=user).first()
            kiosk = owned or member
        
        if not kiosk:
            return JsonResponse({'error': 'No kiosk found'}, status=404)
        
        # Check access
        is_owner = kiosk.owner == user
        is_member = KioskMember.objects.filter(kiosk=kiosk, user=user).exists()
        if not is_owner and not is_member:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Calculate date range
        try:
            days = int(period)
        except ValueError:
            days = 7
        
        # Build data based on period
        labels = []
        deposits = []
        withdrawals = []
        profits = []
        
        if days == 1:
            # Today - show hourly data
            today = timezone.now().date()
            transactions = Transaction.objects.filter(
                kiosk=kiosk,
                timestamp__date=today
            )
            
            for hour in range(24):
                hour_tx = transactions.filter(timestamp__hour=hour)
                
                hour_deposits = hour_tx.filter(transaction_type='DEPOSIT').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0')
                
                hour_withdrawals = hour_tx.filter(transaction_type='WITHDRAWAL').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0')
                
                hour_profit = hour_tx.aggregate(total=Sum('profit'))['total'] or Decimal('0')
                
                labels.append(f'{hour:02d}h')
                deposits.append(float(hour_deposits))
                withdrawals.append(float(hour_withdrawals))
                profits.append(float(hour_profit))
        else:
            # Multi-day view - show daily data
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days - 1)
            
            transactions = Transaction.objects.filter(
                kiosk=kiosk,
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            )
            
            current_date = start_date
            while current_date <= end_date:
                day_tx = transactions.filter(timestamp__date=current_date)
                
                day_deposits = day_tx.filter(transaction_type='DEPOSIT').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0')
                
                day_withdrawals = day_tx.filter(transaction_type='WITHDRAWAL').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0')
                
                day_profit = day_tx.aggregate(total=Sum('profit'))['total'] or Decimal('0')
                
                # Format label based on period
                if days <= 7:
                    labels.append(current_date.strftime('%a'))  # Mon, Tue...
                elif days <= 30:
                    labels.append(current_date.strftime('%d'))  # 01, 02...
                else:
                    labels.append(current_date.strftime('%d/%m'))  # 01/12...
                
                deposits.append(float(day_deposits))
                withdrawals.append(float(day_withdrawals))
                profits.append(float(day_profit))
                
                current_date += timedelta(days=1)
        
        # Summary stats
        total_deposits = sum(deposits)
        total_withdrawals = sum(withdrawals)
        total_profit = sum(profits)
        
        return JsonResponse({
            'labels': labels,
            'datasets': {
                'deposits': deposits,
                'withdrawals': withdrawals,
                'profits': profits,
            },
            'summary': {
                'total_deposits': total_deposits,
                'total_withdrawals': total_withdrawals,
                'total_profit': total_profit,
                'net_flow': total_deposits - total_withdrawals,
            },
            'period': days,
            'kiosk': kiosk.name,
        })
