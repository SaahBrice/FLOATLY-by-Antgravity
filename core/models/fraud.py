"""
FraudReport and Feedback models for Floatly.

Community fraud reporting and user feedback system.
"""

from django.db import models

from .user import phone_validator


# =============================================================================
# FRAUD REPORT MODEL
# =============================================================================

class FraudReport(models.Model):
    """
    Community fraud report for warning other agents.
    Multiple reports create a verified threat.
    """
    
    class ReportType(models.TextChoices):
        FAKE_SMS = 'FAKE_SMS', 'Fake SMS'
        SCAM_CALL = 'SCAM_CALL', 'Scam Call'
        FAKE_CALLER = 'FAKE_CALLER', 'Fake Caller'
        DANGEROUS = 'DANGEROUS', 'Dangerous Warning'
        OTHER = 'OTHER', 'Other'
    
    phone_number = models.CharField(
        'scammer phone',
        max_length=20,
        validators=[phone_validator],
        db_index=True,
        help_text='Phone number of the suspected scammer'
    )
    scammer_name = models.CharField(
        'scammer name',
        max_length=100,
        blank=True,
        help_text='Name used by the scammer (if known)'
    )
    report_type = models.CharField(
        'type of fraud',
        max_length=15,
        choices=ReportType.choices,
        default=ReportType.OTHER
    )
    description = models.TextField(
        'description',
        help_text='What happened? Describe the incident'
    )
    proof_image = models.ImageField(
        'proof screenshot',
        upload_to='fraud_proofs/%Y/%m/',
        blank=True,
        null=True,
        help_text='Screenshot of fake SMS or other proof'
    )
    
    # Reporter info
    reporter = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='fraud_reports',
        help_text='User who submitted this report'
    )
    reporter_kiosk = models.ForeignKey(
        'Kiosk',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fraud_reports',
        help_text='Kiosk where the incident occurred'
    )
    reporter_location = models.CharField(
        'location',
        max_length=200,
        blank=True,
        help_text='Location for proximity alerts'
    )
    
    # Timestamps and status
    created_at = models.DateTimeField(
        'reported at',
        auto_now_add=True,
        db_index=True
    )
    is_verified = models.BooleanField(
        'verified threat',
        default=False,
        help_text='True if 3+ independent reports'
    )
    
    class Meta:
        verbose_name = 'fraud report'
        verbose_name_plural = 'fraud reports'
        ordering = ['-created_at']
    
    def __str__(self):
        status = "⚠️ VERIFIED" if self.is_verified else "Reported"
        return f"{status}: {self.phone_number} ({self.report_type})"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Check if this phone should be marked as verified
        self.check_verification()
    
    def check_verification(self):
        """Mark as verified if 3+ independent reports exist."""
        report_count = FraudReport.objects.filter(
            phone_number=self.phone_number
        ).values('reporter').distinct().count()
        
        if report_count >= 3 and not self.is_verified:
            FraudReport.objects.filter(
                phone_number=self.phone_number
            ).update(is_verified=True)
    
    @classmethod
    def get_report_count(cls, phone_number):
        """Get number of reports for a phone number."""
        return cls.objects.filter(phone_number=phone_number).count()
    
    @classmethod
    def is_blacklisted(cls, phone_number):
        """Check if a phone number is in the blacklist."""
        return cls.objects.filter(phone_number=phone_number).exists()
    
    @classmethod
    def is_verified_threat(cls, phone_number):
        """Check if a phone number is a verified threat."""
        return cls.objects.filter(
            phone_number=phone_number,
            is_verified=True
        ).exists()


# =============================================================================
# FEEDBACK MODEL
# =============================================================================

class Feedback(models.Model):
    """
    User feedback for feature suggestions and bug reports.
    """
    
    FEEDBACK_TYPES = [
        ('FEATURE', 'Feature Suggestion'),
        ('BUG', 'Bug Report'),
        ('IMPROVEMENT', 'Improvement'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('REVIEWING', 'Under Review'),
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('DECLINED', 'Declined'),
    ]
    
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='feedback_items'
    )
    
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_TYPES,
        default='FEATURE'
    )
    
    title = models.CharField(
        max_length=200,
        help_text='Brief summary of your feedback'
    )
    
    message = models.TextField(
        help_text='Detailed description of your suggestion or issue'
    )
    
    screenshot = models.ImageField(
        upload_to='feedback/',
        blank=True,
        null=True,
        help_text='Optional screenshot to help explain'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NEW'
    )
    
    admin_notes = models.TextField(
        blank=True,
        help_text='Internal notes for admin'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
    
    def __str__(self):
        return f"{self.get_feedback_type_display()}: {self.title}"
