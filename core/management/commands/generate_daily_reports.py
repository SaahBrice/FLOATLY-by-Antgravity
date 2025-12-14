"""
Management command to generate daily analytics reports.

Should be run daily via scheduled task (e.g., PythonAnywhere scheduled task at 9pm).
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Kiosk, DailyReport, Notification, NotificationPreference
from core.report_service import generate_report_data

logger = logging.getLogger('core')


class Command(BaseCommand):
    help = 'Generate daily analytics reports for all kiosks and send notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to generate report for (YYYY-MM-DD). Defaults to today.',
        )
        parser.add_argument(
            '--kiosk',
            type=str,
            help='Specific kiosk slug to generate report for. Defaults to all.',
        )
        parser.add_argument(
            '--no-notify',
            action='store_true',
            help='Skip sending notifications.',
        )
    
    def handle(self, *args, **options):
        from datetime import datetime
        
        # Parse date
        if options['date']:
            try:
                report_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {options['date']}"))
                return
        else:
            report_date = timezone.now().date()
        
        # Get kiosks
        if options['kiosk']:
            kiosks = Kiosk.objects.filter(slug=options['kiosk'], is_active=True)
            if not kiosks.exists():
                self.stderr.write(self.style.ERROR(f"Kiosk not found: {options['kiosk']}"))
                return
        else:
            kiosks = Kiosk.objects.filter(is_active=True)
        
        self.stdout.write(f"Generating reports for {kiosks.count()} kiosks for {report_date}...")
        
        success_count = 0
        error_count = 0
        
        for kiosk in kiosks:
            try:
                # Generate report data
                report_data = generate_report_data(kiosk, report_date)
                
                # Create or update report
                report, created = DailyReport.objects.update_or_create(
                    kiosk=kiosk,
                    date=report_date,
                    defaults={'data': report_data}
                )
                
                status = "Created" if created else "Updated"
                self.stdout.write(f"  {status} report for {kiosk.name}")
                
                # Send notifications
                if not options['no_notify']:
                    self._send_notifications(kiosk, report)
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error generating report for {kiosk.name}: {e}")
                self.stderr.write(self.style.ERROR(f"  Error for {kiosk.name}: {e}"))
                error_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"Done! Generated {success_count} reports, {error_count} errors."
        ))
    
    def _send_notifications(self, kiosk, report):
        """Send notifications to kiosk owner and members."""
        from core.notification_service import send_push_notification
        
        users_to_notify = set()
        
        # Add owner
        users_to_notify.add(kiosk.owner)
        
        # Add members
        for member in kiosk.members.all():
            users_to_notify.add(member.user)
        
        report_url = f"/reports/{report.date.isoformat()}/"
        
        for user in users_to_notify:
            try:
                # Check user preferences
                prefs = NotificationPreference.objects.filter(user=user).first()
                
                # Create in-app notification
                Notification.objects.create(
                    user=user,
                    notification_type='SYSTEM',
                    title=f"📊 Daily Report Ready",
                    message=f"Your daily analytics for {kiosk.name} is ready. Profit today: {report.total_profit:,.0f} CFA",
                    action_url=report_url,
                )
                
                # Send push notification
                if prefs and prefs.push_enabled:
                    try:
                        send_push_notification(
                            user=user,
                            title="📊 Daily Report Ready",
                            body=f"Profit today: {report.total_profit:,.0f} CFA",
                            url=report_url,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send push to {user.email}: {e}")
                
                # TODO: Send email if enabled (prefs.email_enabled)
                
            except Exception as e:
                logger.error(f"Error notifying {user.email}: {e}")
