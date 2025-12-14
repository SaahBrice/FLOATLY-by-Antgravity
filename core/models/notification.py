"""
Notification models for Floatly.

Notification, PushSubscription, and NotificationPreference models.
"""

from django.db import models
from django.utils import timezone


# =============================================================================
# NOTIFICATION MODEL
# =============================================================================

class Notification(models.Model):
    """
    Alerts, invites, and system messages for users.
    Supports actionable notifications with click-through URLs.
    """
    
    class NotificationType(models.TextChoices):
        INVITE = 'INVITE', 'Kiosk Invitation'
        ALERT = 'ALERT', 'Alert'
        FRAUD = 'FRAUD', 'Fraud Warning'
        SYSTEM = 'SYSTEM', 'System Message'
        SUMMARY = 'SUMMARY', 'Daily Summary'
        TRANSACTION = 'TRANSACTION', 'Transaction Alert'
    
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High'
    
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='The user this notification is for'
    )
    title = models.CharField(
        'title',
        max_length=200,
        help_text='Short notification title'
    )
    message = models.TextField(
        'message',
        help_text='Detailed notification content'
    )
    notification_type = models.CharField(
        'type',
        max_length=15,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        help_text='Category of notification'
    )
    is_read = models.BooleanField(
        'read',
        default=False,
        help_text='Has the user seen this notification?'
    )
    action_url = models.CharField(
        'action URL',
        max_length=500,
        blank=True,
        help_text='URL to navigate to when clicked (e.g., invitation acceptance)'
    )
    
    # Optional reference to related objects
    related_kiosk = models.ForeignKey(
        'Kiosk',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Related kiosk if applicable'
    )
    related_transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Related transaction if applicable'
    )
    
    # Priority and delivery tracking
    priority = models.CharField(
        'priority',
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        help_text='Notification priority level'
    )
    push_sent = models.BooleanField(
        'push sent',
        default=False,
        help_text='Was push notification sent?'
    )
    email_sent = models.BooleanField(
        'email sent',
        default=False,
        help_text='Was email notification sent?'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True,
        db_index=True
    )
    read_at = models.DateTimeField(
        'read at',
        null=True,
        blank=True,
        help_text='When the notification was marked as read'
    )
    
    class Meta:
        verbose_name = 'notification'
        verbose_name_plural = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        status = '✓' if self.is_read else '●'
        return f"{status} {self.title} → {self.user.display_name}"
    
    def mark_as_read(self):
        """Mark notification as read and set read timestamp."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @classmethod
    def create_invite(cls, user, kiosk, invited_by):
        """Create an invitation notification."""
        return cls.objects.create(
            user=user,
            title=f"Invitation to {kiosk.name}",
            message=f"{invited_by.display_name} has invited you to join {kiosk.name} as a team member.",
            notification_type=cls.NotificationType.INVITE,
            action_url=f"/kiosks/{kiosk.slug}/accept-invite/",
            related_kiosk=kiosk
        )
    
    @classmethod
    def create_fraud_alert(cls, user, phone_number, details):
        """Create a fraud warning notification."""
        return cls.objects.create(
            user=user,
            title=f"⚠️ Fraud Alert: {phone_number}",
            message=details,
            notification_type=cls.NotificationType.FRAUD,
            action_url="/blacklist/"
        )
    
    @classmethod
    def create_system_notification(cls, user, title, message, action_url='', priority='NORMAL'):
        """Create a system notification."""
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=cls.NotificationType.SYSTEM,
            action_url=action_url,
            priority=priority
        )
    
    @classmethod
    def create_daily_summary(cls, user, kiosk, summary_data):
        """Create a daily summary notification."""
        return cls.objects.create(
            user=user,
            title=f"📊 Daily Summary - {kiosk.name}",
            message=f"Transactions: {summary_data.get('count', 0)}, Profit: {summary_data.get('profit', 0):,.0f} CFA",
            notification_type=cls.NotificationType.SUMMARY,
            action_url=f"/dashboard/?kiosk={kiosk.slug}",
            related_kiosk=kiosk
        )


# =============================================================================
# PUSH SUBSCRIPTION MODEL
# =============================================================================

class PushSubscription(models.Model):
    """
    Store push notification subscriptions for users.
    Supports VAPID web push and FCM tokens.
    """
    
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        help_text='User who owns this subscription'
    )
    endpoint = models.TextField(
        'endpoint URL',
        help_text='Push service endpoint URL'
    )
    p256dh_key = models.TextField(
        'p256dh key',
        blank=True,
        help_text='Client public key for encryption'
    )
    auth_key = models.TextField(
        'auth key',
        blank=True,
        help_text='Authentication secret'
    )
    user_agent = models.CharField(
        'user agent',
        max_length=500,
        blank=True,
        help_text='Browser/device user agent'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this subscription still valid?'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    last_used_at = models.DateTimeField(
        'last used at',
        null=True,
        blank=True,
        help_text='Last time a push was sent to this subscription'
    )
    
    class Meta:
        verbose_name = 'push subscription'
        verbose_name_plural = 'push subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        status = '✓' if self.is_active else '✗'
        return f"{status} Push sub for {self.user.display_name}"


# =============================================================================
# NOTIFICATION PREFERENCES MODEL
# =============================================================================

class NotificationPreference(models.Model):
    """
    User preferences for notification delivery.
    Controls which channels and types of notifications to receive.
    """
    
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text='User these preferences belong to'
    )
    
    # Channel preferences
    push_enabled = models.BooleanField(
        'push notifications enabled',
        default=True,
        help_text='Receive browser push notifications'
    )
    email_enabled = models.BooleanField(
        'email notifications enabled',
        default=True,
        help_text='Receive email notifications'
    )
    
    # Type preferences
    invites_enabled = models.BooleanField(
        'invitation notifications',
        default=True,
        help_text='Receive kiosk invitation notifications'
    )
    fraud_alerts_enabled = models.BooleanField(
        'fraud alert notifications',
        default=True,
        help_text='Receive fraud warning notifications'
    )
    system_messages_enabled = models.BooleanField(
        'system message notifications',
        default=True,
        help_text='Receive system updates and announcements'
    )
    transaction_alerts_enabled = models.BooleanField(
        'transaction notifications',
        default=True,
        help_text='Receive notifications when team members make transactions'
    )
    daily_summary_enabled = models.BooleanField(
        'daily summary',
        default=True,
        help_text='Receive daily summary at specified time'
    )
    summary_time = models.TimeField(
        'summary delivery time',
        default='20:00',
        help_text='Time to receive daily summary (local time)'
    )
    
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'notification preference'
        verbose_name_plural = 'notification preferences'
    
    def __str__(self):
        return f"Notification prefs for {self.user.display_name}"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create notification preferences for a user."""
        prefs, created = cls.objects.get_or_create(user=user)
        return prefs
