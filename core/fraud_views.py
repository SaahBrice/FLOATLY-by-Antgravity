"""
Fraud Reporting Views for Floatly.

Handles:
- Report fraud form
- Blacklist page (searchable)
- Report details
- Phone number check (HTMX)
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.db.models import Count, Q
from django.core.paginator import Paginator

from .models import FraudReport, Kiosk, User
from .notification_service import notify_fraud_alert

logger = logging.getLogger('core.fraud')


# =============================================================================
# REPORT FRAUD VIEW
# =============================================================================

class ReportFraudView(LoginRequiredMixin, View):
    """
    Form to submit a fraud report.
    """
    
    def get(self, request):
        # Get user's active kiosk for context
        kiosks = Kiosk.objects.filter(
            Q(owner=request.user) | 
            Q(members__user=request.user)
        ).distinct()
        
        return render(request, 'fraud/report_form.html', {
            'page_title': 'Report Fraud',
            'report_types': FraudReport.ReportType.choices,
            'kiosks': kiosks,
        })
    
    def post(self, request):
        phone_number = request.POST.get('phone_number', '').strip()
        scammer_name = request.POST.get('scammer_name', '').strip()
        report_type = request.POST.get('report_type', 'OTHER')
        description = request.POST.get('description', '').strip()
        kiosk_id = request.POST.get('kiosk')
        proof_image = request.FILES.get('proof_image')
        
        # Validate required fields
        if not phone_number:
            messages.error(request, 'Phone number is required')
            return redirect('core:fraud_report')
        
        if not description:
            messages.error(request, 'Please describe what happened')
            return redirect('core:fraud_report')
        
        # Get kiosk if provided
        kiosk = None
        if kiosk_id:
            try:
                kiosk = Kiosk.objects.get(id=kiosk_id)
            except Kiosk.DoesNotExist:
                pass
        
        # Create report
        report = FraudReport.objects.create(
            phone_number=phone_number,
            scammer_name=scammer_name,
            report_type=report_type,
            description=description,
            proof_image=proof_image,
            reporter=request.user,
            reporter_kiosk=kiosk,
            reporter_location=kiosk.location if kiosk else ''
        )
        
        logger.info(
            f"Fraud report created: phone={phone_number}, "
            f"reporter={request.user.email}, type={report_type}"
        )
        
        # Check verification status
        report_count = FraudReport.get_report_count(phone_number)
        
        # Send alerts to other users
        self._send_fraud_alerts(report)
        
        if report_count >= 3:
            messages.success(
                request, 
                f'Report submitted! This number is now marked as a Confirmed Danger ({report_count} reports).'
            )
        else:
            messages.success(
                request, 
                f'Report submitted! This number now has {report_count} report(s).'
            )
        
        return redirect('core:blacklist')
    
    def _send_fraud_alerts(self, report):
        """Send alerts to other users about this fraud report."""
        try:
            # Get all active users (simplified - could be location-based)
            # For now, just log - in production would send to nearby users
            logger.info(f"Would send fraud alert for {report.phone_number} to nearby users")
            
            # If this is a verified threat (3+ reports), send to more users
            if report.is_verified:
                logger.info(f"Verified threat: {report.phone_number} - sending broader alert")
                
        except Exception as e:
            logger.error(f"Failed to send fraud alerts: {e}")


# =============================================================================
# BLACKLIST VIEW
# =============================================================================

class BlacklistView(LoginRequiredMixin, ListView):
    """
    Searchable list of reported phone numbers.
    """
    model = FraudReport
    template_name = 'fraud/blacklist.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        qs = FraudReport.objects.all()
        
        # Search filter
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(phone_number__icontains=search) |
                Q(scammer_name__icontains=search)
            )
        
        # Type filter
        report_type = self.request.GET.get('type')
        if report_type:
            qs = qs.filter(report_type=report_type)
        
        # Verified only filter
        verified_only = self.request.GET.get('verified')
        if verified_only == 'true':
            qs = qs.filter(is_verified=True)
        
        return qs.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Community Blacklist'
        context['search'] = self.request.GET.get('search', '')
        context['report_types'] = FraudReport.ReportType.choices
        context['selected_type'] = self.request.GET.get('type', '')
        context['verified_only'] = self.request.GET.get('verified', '') == 'true'
        
        # Stats
        context['total_reports'] = FraudReport.objects.count()
        context['verified_threats'] = FraudReport.objects.filter(is_verified=True).values('phone_number').distinct().count()
        
        return context


# =============================================================================
# BLACKLIST AGGREGATED VIEW
# =============================================================================

class BlacklistAggregatedView(LoginRequiredMixin, View):
    """
    Shows aggregated blacklist (one row per phone number).
    """
    
    def get(self, request):
        search = request.GET.get('search', '').strip()
        
        # Aggregate reports by phone number
        numbers = FraudReport.objects.values('phone_number').annotate(
            report_count=Count('id'),
            is_verified=Q(is_verified=True)
        ).order_by('-report_count')
        
        if search:
            numbers = numbers.filter(
                Q(phone_number__icontains=search)
            )
        
        # Paginate
        paginator = Paginator(numbers, 20)
        page = request.GET.get('page', 1)
        entries = paginator.get_page(page)
        
        return render(request, 'fraud/blacklist_aggregated.html', {
            'page_title': 'Community Blacklist',
            'entries': entries,
            'search': search,
            'total_numbers': numbers.count(),
        })


# =============================================================================
# REPORT DETAIL VIEW
# =============================================================================

class ReportDetailView(LoginRequiredMixin, DetailView):
    """
    View full details of a fraud report.
    """
    model = FraudReport
    template_name = 'fraud/report_detail.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.object
        
        context['page_title'] = f'Report: {report.phone_number}'
        
        # Get other reports for same number
        context['related_reports'] = FraudReport.objects.filter(
            phone_number=report.phone_number
        ).exclude(id=report.id).order_by('-created_at')[:5]
        
        context['total_reports'] = FraudReport.get_report_count(report.phone_number)
        
        return context


# =============================================================================
# CHECK PHONE VIEW (HTMX)
# =============================================================================

class CheckPhoneView(LoginRequiredMixin, View):
    """
    HTMX endpoint to check a phone number against the blacklist.
    Used in transaction form for real-time warnings.
    """
    
    def get(self, request):
        phone = request.GET.get('phone', '').strip()
        
        if not phone or len(phone) < 9:
            return HttpResponse('')
        
        # Check blacklist
        if FraudReport.is_verified_threat(phone):
            return render(request, 'fraud/partials/_warning_banner.html', {
                'level': 'danger',
                'phone': phone,
                'message': '⚠️ DANGER: This number has been verified as a fraud threat! Multiple agents have reported scam activity.',
                'report_count': FraudReport.get_report_count(phone),
            })
        elif FraudReport.is_blacklisted(phone):
            report_count = FraudReport.get_report_count(phone)
            return render(request, 'fraud/partials/_warning_banner.html', {
                'level': 'warning',
                'phone': phone,
                'message': f'⚠️ Warning: This number has {report_count} fraud report(s). Proceed with caution.',
                'report_count': report_count,
            })
        
        return HttpResponse('')
    
    def post(self, request):
        """JSON API version for non-HTMX requests."""
        import json
        
        try:
            data = json.loads(request.body)
            phone = data.get('phone', '').strip()
        except:
            phone = request.POST.get('phone', '').strip()
        
        if not phone:
            return JsonResponse({'status': 'ok', 'blacklisted': False})
        
        is_verified = FraudReport.is_verified_threat(phone)
        is_blacklisted = FraudReport.is_blacklisted(phone)
        report_count = FraudReport.get_report_count(phone) if is_blacklisted else 0
        
        return JsonResponse({
            'status': 'ok',
            'blacklisted': is_blacklisted,
            'verified_threat': is_verified,
            'report_count': report_count,
        })
