"""
Daily Report model for Floatly.

Stores computed daily analytics for each kiosk.
"""

from django.db import models
from django.utils import timezone


class DailyReport(models.Model):
    """
    Stores a computed daily analytics report for a kiosk.
    
    The report data is stored as JSON for flexibility.
    Generated once daily by a scheduled management command.
    """
    
    kiosk = models.ForeignKey(
        'Kiosk',
        on_delete=models.CASCADE,
        related_name='daily_reports',
        help_text='Which kiosk this report is for'
    )
    date = models.DateField(
        'report date',
        db_index=True,
        help_text='The date this report covers'
    )
    data = models.JSONField(
        'report data',
        default=dict,
        help_text='All computed metrics stored as JSON'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'daily report'
        verbose_name_plural = 'daily reports'
        ordering = ['-date']
        unique_together = ['kiosk', 'date']
        indexes = [
            models.Index(fields=['kiosk', '-date']),
        ]
    
    def __str__(self):
        return f"{self.kiosk.name} - {self.date}"
    
    @classmethod
    def get_or_generate(cls, kiosk, date=None):
        """Get existing report or generate a new one."""
        from .report_service import generate_report_data
        
        if date is None:
            date = timezone.now().date()
        
        report, created = cls.objects.get_or_create(
            kiosk=kiosk,
            date=date,
            defaults={'data': generate_report_data(kiosk, date)}
        )
        
        return report
    
    # Convenience properties to access report data
    @property
    def total_profit(self):
        return self.data.get('total_profit', 0)
    
    @property
    def cash_balance(self):
        return self.data.get('cash_balance', 0)
    
    @property
    def float_balance(self):
        return self.data.get('float_balance', 0)
    
    @property
    def transaction_count(self):
        return self.data.get('transaction_count', 0)
    
    @property
    def has_low_balance_alert(self):
        alerts = self.data.get('low_balance_alerts', [])
        return len(alerts) > 0
