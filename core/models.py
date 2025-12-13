"""
Floatly Database Models

Complete data structure for the mobile money agent logbook:
- User: Custom user model with email login and Google OAuth support
- Kiosk: Agent kiosk locations
- KioskMember: Team management with roles
- Network: Mobile money networks (MTN, Orange, etc.)
- CommissionRate: Commission rules per network and amount range
- Transaction: Every money movement with auto-calculated profit
- Notification: Alerts, invites, and system messages
"""

import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from django.utils.text import slugify

from .managers import UserManager, TransactionManager, KioskManager


# =============================================================================
# VALIDATORS
# =============================================================================

phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{9,15}$',
    message='Phone number must be 9-15 digits, optionally starting with +'
)


# =============================================================================
# USER MODEL
# =============================================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model where email is the unique identifier for authentication.
    Supports future Google OAuth integration.
    """
    
    # Primary identification
    email = models.EmailField(
        'email address',
        unique=True,
        db_index=True,
        help_text='Primary login identifier'
    )
    
    # Profile information
    username = models.CharField(
        'username',
        max_length=50,
        blank=True,
        help_text='Display name (how the user wants to be called)'
    )
    full_name = models.CharField(
        'full name',
        max_length=150,
        blank=True,
        help_text='Full legal name for records'
    )
    phone_number = models.CharField(
        'phone number',
        max_length=20,
        blank=True,
        validators=[phone_validator],
        help_text='With country code, e.g., +237677123456'
    )
    
    # Email verification
    email_verified = models.BooleanField(
        'email verified',
        default=False,
        help_text='Has the user verified their email address?'
    )
    
    # Google OAuth fields (for future integration)
    google_id = models.CharField(
        'Google ID',
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text='Google account identifier for OAuth'
    )
    profile_picture = models.URLField(
        'profile picture URL',
        max_length=500,
        blank=True,
        help_text='URL to profile picture (from Google or uploaded)'
    )
    
    # Django permission fields
    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Can access admin site'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Account is active and can log in'
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        'date joined',
        default=timezone.now
    )
    last_login = models.DateTimeField(
        'last login',
        blank=True,
        null=True
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by USERNAME_FIELD
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.display_name
    
    @property
    def display_name(self):
        """Return the best available display name."""
        if self.username:
            return self.username
        if self.full_name:
            return self.full_name.split()[0]  # First name
        return self.email.split('@')[0]
    
    def get_full_name(self):
        return self.full_name or self.display_name
    
    def get_short_name(self):
        return self.display_name


# =============================================================================
# KIOSK MODEL
# =============================================================================

class Kiosk(models.Model):
    """
    A kiosk represents a physical location where an agent operates.
    One user can own multiple kiosks.
    """
    
    name = models.CharField(
        'kiosk name',
        max_length=100,
        help_text='Unique name like "Akwa Shop" or "Molyko Kiosk"'
    )
    slug = models.SlugField(
        'URL slug',
        max_length=120,
        unique=True,
        help_text='Auto-generated unique identifier'
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_kiosks',
        help_text='The user who created and owns this kiosk'
    )
    location = models.CharField(
        'location description',
        max_length=255,
        blank=True,
        help_text='Physical location or address description'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this kiosk currently operational?'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )
    
    objects = KioskManager()
    
    class Meta:
        verbose_name = 'kiosk'
        verbose_name_plural = 'kiosks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.owner.display_name})"
    
    def save(self, *args, **kwargs):
        """Auto-generate unique slug if not provided."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)
    
    def _generate_unique_slug(self):
        """Generate a unique slug for the kiosk."""
        base_slug = slugify(self.name)
        if not base_slug:
            base_slug = 'kiosk'
        
        slug = base_slug
        counter = 1
        
        # Check if slug exists (excluding self for updates)
        while Kiosk.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def get_balances(self):
        """Calculate current cash and float balances for this kiosk."""
        return self.transactions.calculate_balances()
    
    def get_today_stats(self):
        """Get today's transaction statistics."""
        return self.transactions.today().calculate_totals()
    
    @property
    def member_count(self):
        """Number of team members (excluding owner)."""
        return self.members.count()


# =============================================================================
# KIOSK MEMBER MODEL
# =============================================================================

class KioskMember(models.Model):
    """
    Represents a user's membership in a kiosk team.
    One user can be a member of multiple kiosks (and owner of others).
    """
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        AGENT = 'AGENT', 'Agent'
    
    kiosk = models.ForeignKey(
        Kiosk,
        on_delete=models.CASCADE,
        related_name='members',
        help_text='The kiosk this membership belongs to'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='kiosk_memberships',
        help_text='The user who is a member'
    )
    role = models.CharField(
        'role',
        max_length=10,
        choices=Role.choices,
        default=Role.AGENT,
        help_text='Admin has full access, Agent has limited access'
    )
    joined_at = models.DateTimeField(
        'joined at',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'kiosk member'
        verbose_name_plural = 'kiosk members'
        ordering = ['-joined_at']
        # Ensure a user can only be added once per kiosk
        unique_together = ['kiosk', 'user']
        constraints = [
            models.UniqueConstraint(
                fields=['kiosk', 'user'],
                name='unique_kiosk_member'
            )
        ]
    
    def __str__(self):
        return f"{self.user.display_name} @ {self.kiosk.name} ({self.role})"
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN


# =============================================================================
# NETWORK MODEL
# =============================================================================

class Network(models.Model):
    """
    Mobile money network (MTN, Orange, etc.)
    Used for transaction categorization and commission rate lookup.
    """
    
    name = models.CharField(
        'network name',
        max_length=50,
        unique=True,
        help_text='e.g., MTN Mobile Money, Orange Money'
    )
    code = models.CharField(
        'network code',
        max_length=10,
        unique=True,
        help_text='Short code like MTN, OM, EU'
    )
    color = models.CharField(
        'brand color',
        max_length=7,
        default='#3b82f6',
        help_text='Hex color for UI display, e.g., #ffcc00 for MTN'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this network currently supported?'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'network'
        verbose_name_plural = 'networks'
        ordering = ['name']
    
    def __str__(self):
        return self.name


# =============================================================================
# COMMISSION RATE MODEL
# =============================================================================

class CommissionRate(models.Model):
    """
    Commission rules for each network based on transaction amount ranges.
    Commissions can be fixed amounts or percentages.
    """
    
    class RateType(models.TextChoices):
        FIXED = 'FIXED', 'Fixed Amount'
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
    
    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        related_name='commission_rates',
        help_text='Which network this rate applies to'
    )
    min_amount = models.DecimalField(
        'minimum amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Minimum transaction amount for this rate (inclusive)'
    )
    max_amount = models.DecimalField(
        'maximum amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Maximum transaction amount for this rate (inclusive)'
    )
    rate_type = models.CharField(
        'rate type',
        max_length=15,
        choices=RateType.choices,
        default=RateType.FIXED,
        help_text='Is the commission a fixed amount or percentage?'
    )
    rate_value = models.DecimalField(
        'rate value',
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Fixed amount in CFA or percentage (e.g., 0.3 for 0.3%)'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Is this rate currently in effect?'
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
        verbose_name = 'commission rate'
        verbose_name_plural = 'commission rates'
        ordering = ['network', 'min_amount']
        indexes = [
            models.Index(fields=['network', 'is_active']),
            models.Index(fields=['min_amount', 'max_amount']),
        ]
    
    def __str__(self):
        rate_display = (
            f"{self.rate_value} CFA" if self.rate_type == self.RateType.FIXED 
            else f"{self.rate_value}%"
        )
        return f"{self.network.code}: {self.min_amount}-{self.max_amount} → {rate_display}"
    
    def calculate_commission(self, amount):
        """Calculate commission for a given amount."""
        if self.rate_type == self.RateType.FIXED:
            return self.rate_value
        else:
            # Percentage calculation
            return (amount * self.rate_value / Decimal('100')).quantize(Decimal('0.01'))
    
    @classmethod
    def get_rate_for_amount(cls, network, amount):
        """
        Find the matching commission rate for a network and amount.
        Returns the CommissionRate object or None if not found.
        """
        return cls.objects.filter(
            network=network,
            is_active=True,
            min_amount__lte=amount,
            max_amount__gte=amount
        ).first()


# =============================================================================
# TRANSACTION MODEL
# =============================================================================

class Transaction(models.Model):
    """
    Every money movement recorded in the system.
    The most critical table - needs good indexing for performance.
    """
    
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit (Cash In)'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal (Cash Out)'
    
    # Relationships
    kiosk = models.ForeignKey(
        Kiosk,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text='Which kiosk this transaction belongs to'
    )
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_transactions',
        help_text='The agent who recorded this transaction'
    )
    network = models.ForeignKey(
        Network,
        on_delete=models.PROTECT,
        related_name='transactions',
        help_text='Which mobile network was used'
    )
    
    # Transaction details
    transaction_type = models.CharField(
        'type',
        max_length=15,
        choices=TransactionType.choices,
        help_text='Deposit = customer sending money, Withdrawal = customer taking cash'
    )
    amount = models.DecimalField(
        'amount',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Transaction amount in CFA'
    )
    
    # Profit tracking (both calculated and actual)
    calculated_profit = models.DecimalField(
        'calculated profit',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Auto-calculated commission based on rate rules'
    )
    profit = models.DecimalField(
        'actual profit',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Final profit (can be edited by user)'
    )
    profit_was_edited = models.BooleanField(
        'profit was edited',
        default=False,
        help_text='Was the profit manually overridden?'
    )
    
    # Customer information (optional)
    customer_phone = models.CharField(
        'customer phone',
        max_length=20,
        blank=True,
        validators=[phone_validator],
        help_text='Customer phone number if known'
    )
    customer_name = models.CharField(
        'customer name',
        max_length=100,
        blank=True,
        help_text='Customer/sender name if known'
    )
    transaction_ref = models.CharField(
        'transaction reference',
        max_length=100,
        blank=True,
        help_text='Transaction ID from the receipt'
    )
    
    # Additional details
    notes = models.TextField(
        'notes',
        blank=True,
        help_text='Any additional notes about this transaction'
    )
    receipt_photo = models.ImageField(
        'receipt photo',
        upload_to='receipts/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text='Photo of the transaction receipt'
    )
    sms_text = models.TextField(
        'SMS text',
        blank=True,
        help_text='Full text message from the receipt if shared'
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        'transaction time',
        default=timezone.now,
        db_index=True,
        help_text='When the transaction occurred'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )
    
    objects = TransactionManager()
    
    class Meta:
        verbose_name = 'transaction'
        verbose_name_plural = 'transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['kiosk', '-timestamp']),
            models.Index(fields=['recorded_by', '-timestamp']),
            models.Index(fields=['network', 'transaction_type']),
            models.Index(fields=['customer_phone']),
            models.Index(fields=['transaction_ref']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} CFA @ {self.kiosk.name}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate profit if not set or if amount changed."""
        # Calculate commission if this is a new transaction or amount changed
        is_new = self.pk is None
        
        if is_new or not self.profit_was_edited:
            # Look up commission rate
            rate = CommissionRate.get_rate_for_amount(self.network, self.amount)
            if rate:
                self.calculated_profit = rate.calculate_commission(self.amount)
                if not self.profit_was_edited:
                    self.profit = self.calculated_profit
            else:
                self.calculated_profit = Decimal('0')
                if not self.profit_was_edited:
                    self.profit = Decimal('0')
        
        super().save(*args, **kwargs)
    
    @property
    def is_deposit(self):
        return self.transaction_type == self.TransactionType.DEPOSIT
    
    @property
    def is_withdrawal(self):
        return self.transaction_type == self.TransactionType.WITHDRAWAL


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
        User,
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
        Kiosk,
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
        User,
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
        User,
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


# =============================================================================
# KIOSK INVITATION MODEL
# =============================================================================

class KioskInvitation(models.Model):
    """
    Invitation to join a kiosk team.
    Supports inviting both existing and new users by email.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'
        EXPIRED = 'EXPIRED', 'Expired'
    
    kiosk = models.ForeignKey(
        Kiosk,
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text='The kiosk the user is being invited to'
    )
    email = models.EmailField(
        'invitee email',
        help_text='Email address of the person being invited'
    )
    role = models.CharField(
        'role',
        max_length=10,
        choices=KioskMember.Role.choices,
        default=KioskMember.Role.AGENT,
        help_text='Role the invitee will have upon acceptance'
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        help_text='The user who sent the invitation'
    )
    token = models.UUIDField(
        'invitation token',
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text='Unique token for invitation link'
    )
    status = models.CharField(
        'status',
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    message = models.TextField(
        'personal message',
        blank=True,
        help_text='Optional message from inviter'
    )
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    expires_at = models.DateTimeField(
        'expires at',
        help_text='Invitation expiration date'
    )
    accepted_at = models.DateTimeField(
        'accepted at',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'kiosk invitation'
        verbose_name_plural = 'kiosk invitations'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invite {self.email} to {self.kiosk.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Set expiration to 7 days from now if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_pending(self):
        return self.status == self.Status.PENDING and not self.is_expired
    
    def accept(self, user):
        """Accept the invitation and add user to kiosk."""
        if not self.is_pending:
            raise ValueError("Invitation is no longer valid")
        
        # Create membership
        member, created = KioskMember.objects.get_or_create(
            kiosk=self.kiosk,
            user=user,
            defaults={'role': self.role}
        )
        
        # Update invitation status
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.save()
        
        return member
    
    def decline(self):
        """Decline the invitation."""
        if self.status == self.Status.PENDING:
            self.status = self.Status.DECLINED
            self.save()


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
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fraud_reports',
        help_text='User who submitted this report'
    )
    reporter_kiosk = models.ForeignKey(
        Kiosk,
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
        User,
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
