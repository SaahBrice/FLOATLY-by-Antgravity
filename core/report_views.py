"""
Report views for Floatly.

Handles displaying daily analytics reports.
"""

import logging
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.utils import timezone

from .models import Kiosk, KioskMember, DailyReport
from .report_service import generate_report_data

logger = logging.getLogger('core')


class ReportListView(LoginRequiredMixin, View):
    """
    List all daily reports for the user's kiosks.
    """
    template_name = 'reports/list.html'
    login_url = '/auth/login/'
    
    def get(self, request):
        # Get user's kiosks
        owned_kiosks = Kiosk.objects.filter(owner=request.user, is_active=True)
        member_kiosks = Kiosk.objects.filter(
            members__user=request.user, is_active=True
        ).exclude(owner=request.user)
        
        all_kiosks = list(owned_kiosks) + list(member_kiosks)
        
        if not all_kiosks:
            return render(request, self.template_name, {
                'page_title': 'Reports',
                'reports': [],
                'no_kiosks': True,
            })
        
        # Get selected kiosk (default to first)
        kiosk_slug = request.GET.get('kiosk')
        if kiosk_slug:
            active_kiosk = get_object_or_404(Kiosk, slug=kiosk_slug, is_active=True)
        else:
            active_kiosk = all_kiosks[0]
        
        # Get reports for this kiosk
        reports = DailyReport.objects.filter(kiosk=active_kiosk).order_by('-date')[:30]
        
        context = {
            'page_title': 'Reports',
            'reports': reports,
            'active_kiosk': active_kiosk,
            'owned_kiosks': owned_kiosks,
            'member_kiosks': member_kiosks,
            'today': timezone.now().date().isoformat(),
        }
        
        return render(request, self.template_name, context)


class ReportDetailView(LoginRequiredMixin, View):
    """
    Show detailed analytics report for a specific date.
    """
    template_name = 'reports/detail.html'
    login_url = '/auth/login/'
    
    def get(self, request, date_str=None):
        # Parse date
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise Http404("Invalid date format")
        else:
            report_date = timezone.now().date()
        
        # Get kiosk
        kiosk_slug = request.GET.get('kiosk')
        if kiosk_slug:
            kiosk = get_object_or_404(Kiosk, slug=kiosk_slug, is_active=True)
        else:
            # Get user's first kiosk
            kiosk = Kiosk.objects.filter(owner=request.user, is_active=True).first()
            if not kiosk:
                membership = KioskMember.objects.filter(
                    user=request.user, kiosk__is_active=True
                ).first()
                if membership:
                    kiosk = membership.kiosk
        
        if not kiosk:
            return redirect('core:report_list')
        
        # Verify access
        is_owner = kiosk.owner == request.user
        is_member = KioskMember.objects.filter(kiosk=kiosk, user=request.user).exists()
        if not is_owner and not is_member:
            raise Http404("Access denied")
        
        # Get or generate report
        report, created = DailyReport.objects.get_or_create(
            kiosk=kiosk,
            date=report_date,
            defaults={'data': generate_report_data(kiosk, report_date)}
        )
        
        # Check if today and allow regeneration
        is_today = report_date == timezone.now().date()
        
        context = {
            'page_title': f'Report - {report_date}',
            'report': report,
            'kiosk': kiosk,
            'is_today': is_today,
            'data': report.data,
        }
        
        return render(request, self.template_name, context)


class RegenerateReportView(LoginRequiredMixin, View):
    """
    Regenerate a report for today.
    """
    login_url = '/auth/login/'
    
    def post(self, request, date_str):
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise Http404("Invalid date format")
        
        kiosk_slug = request.GET.get('kiosk') or request.POST.get('kiosk')
        if kiosk_slug:
            kiosk = get_object_or_404(Kiosk, slug=kiosk_slug, is_active=True)
        else:
            kiosk = Kiosk.objects.filter(owner=request.user, is_active=True).first()
        
        if not kiosk or kiosk.owner != request.user:
            raise Http404("Access denied")
        
        # Regenerate
        report_data = generate_report_data(kiosk, report_date)
        DailyReport.objects.update_or_create(
            kiosk=kiosk,
            date=report_date,
            defaults={'data': report_data}
        )
        
        return redirect(f'/reports/{date_str}/?kiosk={kiosk.slug}')
