"""
Django Admin configuration for Floatly.

Provides rich admin interfaces for all models with:
- Custom list displays
- Filters and search
- Inline editing
- Bulk actions
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Sum

from .models import (
    User, Kiosk, KioskMember, Network, 
    CommissionRate, Transaction, Notification,
    PushSubscription, NotificationPreference,
    KioskInvitation, FraudReport
)


# =============================================================================
# CUSTOM ADMIN SITE
# =============================================================================

admin.site.site_header = "Floatly Administration"
admin.site.site_title = "Floatly Admin"
admin.site.index_title = "Welcome to Floatly Admin Dashboard"


# =============================================================================
# INLINE ADMINS
# =============================================================================

class KioskMemberInline(admin.TabularInline):
    """Inline editor for kiosk team members."""
    model = KioskMember
    extra = 0
    autocomplete_fields = ['user']
    readonly_fields = ['joined_at']


class CommissionRateInline(admin.TabularInline):
    """Inline editor for commission rates."""
    model = CommissionRate
    extra = 0
    fields = ['min_amount', 'max_amount', 'rate_type', 'rate_value', 'is_active']


# =============================================================================
# USER ADMIN
# =============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""
    
    list_display = [
        'email', 'display_name', 'phone_number', 
        'email_verified', 'is_active', 'date_joined'
    ]
    list_filter = ['email_verified', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'username', 'full_name', 'phone_number']
    ordering = ['-date_joined']
    
    # Override fieldsets for email-based auth
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('username', 'full_name', 'phone_number', 'profile_picture')}),
        ('Verification', {'fields': ('email_verified', 'google_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        ('Personal Info', {
            'fields': ('username', 'full_name', 'phone_number'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
    
    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = 'Display Name'


# =============================================================================
# KIOSK ADMIN
# =============================================================================

@admin.register(Kiosk)
class KioskAdmin(admin.ModelAdmin):
    """Admin configuration for Kiosk model."""
    
    list_display = [
        'name', 'owner_display', 'location', 'member_count_display',
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'location', 'owner__email', 'owner__full_name']
    autocomplete_fields = ['owner']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    inlines = [KioskMemberInline]
    
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'owner')}),
        ('Location', {'fields': ('location',)}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    def owner_display(self, obj):
        return obj.owner.display_name
    owner_display.short_description = 'Owner'
    owner_display.admin_order_field = 'owner__email'
    
    def member_count_display(self, obj):
        count = obj.member_count
        return format_html(
            '<span style="color: {};">{} members</span>',
            '#22c55e' if count > 0 else '#6b7280',
            count
        )
    member_count_display.short_description = 'Team'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner').prefetch_related('members')


# =============================================================================
# KIOSK MEMBER ADMIN
# =============================================================================

@admin.register(KioskMember)
class KioskMemberAdmin(admin.ModelAdmin):
    """Admin configuration for KioskMember model."""
    
    list_display = ['user_display', 'kiosk', 'role_badge', 'joined_at']
    list_filter = ['role', 'kiosk', 'joined_at']
    search_fields = ['user__email', 'user__full_name', 'kiosk__name']
    autocomplete_fields = ['user', 'kiosk']
    readonly_fields = ['joined_at']
    
    def user_display(self, obj):
        return obj.user.display_name
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__email'
    
    def role_badge(self, obj):
        color = '#3b82f6' if obj.role == 'ADMIN' else '#6b7280'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'


# =============================================================================
# NETWORK ADMIN
# =============================================================================

@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    """Admin configuration for Network model."""
    
    list_display = ['name', 'code', 'color_preview', 'rate_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    inlines = [CommissionRateInline]
    
    def color_preview(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; '
            'background-color: {}; border-radius: 4px; vertical-align: middle;"></span> '
            '<code>{}</code>',
            obj.color, obj.color
        )
    color_preview.short_description = 'Brand Color'
    
    def rate_count(self, obj):
        count = obj.commission_rates.filter(is_active=True).count()
        return f"{count} rates"
    rate_count.short_description = 'Active Rates'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('commission_rates')


# =============================================================================
# COMMISSION RATE ADMIN
# =============================================================================

@admin.register(CommissionRate)
class CommissionRateAdmin(admin.ModelAdmin):
    """Admin configuration for CommissionRate model."""
    
    list_display = [
        'network', 'amount_range', 'rate_display', 
        'is_active', 'updated_at'
    ]
    list_filter = ['network', 'rate_type', 'is_active']
    search_fields = ['network__name', 'network__code']
    autocomplete_fields = ['network']
    
    fieldsets = (
        ('Network', {'fields': ('network',)}),
        ('Amount Range', {'fields': (('min_amount', 'max_amount'),)}),
        ('Commission', {'fields': (('rate_type', 'rate_value'),)}),
        ('Status', {'fields': ('is_active',)}),
    )
    
    def amount_range(self, obj):
        return f"{obj.min_amount:,.0f} - {obj.max_amount:,.0f} CFA"
    amount_range.short_description = 'Amount Range'
    amount_range.admin_order_field = 'min_amount'
    
    def rate_display(self, obj):
        if obj.rate_type == 'FIXED':
            return format_html(
                '<span style="color: #22c55e; font-weight: bold;">{:,.0f} CFA</span>',
                obj.rate_value
            )
        return format_html(
            '<span style="color: #3b82f6; font-weight: bold;">{}%</span>',
            obj.rate_value
        )
    rate_display.short_description = 'Commission'


# =============================================================================
# TRANSACTION ADMIN
# =============================================================================

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin configuration for Transaction model."""
    
    list_display = [
        'id', 'kiosk', 'type_badge', 'network_display', 
        'amount_display', 'profit_display', 'recorded_by_display', 
        'timestamp'
    ]
    list_filter = [
        'transaction_type', 'network', 'kiosk', 
        ('timestamp', admin.DateFieldListFilter),
        'profit_was_edited'
    ]
    search_fields = [
        'customer_phone', 'transaction_ref', 
        'kiosk__name', 'recorded_by__email'
    ]
    autocomplete_fields = ['kiosk', 'recorded_by', 'network']
    readonly_fields = ['calculated_profit', 'created_at', 'updated_at']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('kiosk', 'recorded_by', 'transaction_type', 'network', 'amount')
        }),
        ('Profit', {
            'fields': ('calculated_profit', 'profit', 'profit_was_edited'),
            'description': 'Profit is auto-calculated based on commission rules. '
                          'Edit "Actual Profit" if you need to override.'
        }),
        ('Customer Info', {
            'fields': ('customer_phone', 'transaction_ref'),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('notes', 'receipt_photo', 'sms_text'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def type_badge(self, obj):
        if obj.transaction_type == 'DEPOSIT':
            color, icon = '#22c55e', '↓'
        else:
            color, icon = '#ef4444', '↑'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_transaction_type_display()
        )
    type_badge.short_description = 'Type'
    type_badge.admin_order_field = 'transaction_type'
    
    def network_display(self, obj):
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            obj.network.color, obj.network.code
        )
    network_display.short_description = 'Network'
    
    def amount_display(self, obj):
        return format_html(
            '<span style="font-weight: bold;">{:,.0f} CFA</span>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def profit_display(self, obj):
        edited = ' ✏️' if obj.profit_was_edited else ''
        return format_html(
            '<span style="color: #22c55e;">{:,.0f} CFA{}</span>',
            obj.profit, edited
        )
    profit_display.short_description = 'Profit'
    
    def recorded_by_display(self, obj):
        if obj.recorded_by:
            return obj.recorded_by.display_name
        return '-'
    recorded_by_display.short_description = 'Agent'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'kiosk', 'network', 'recorded_by'
        )
    
    def save_model(self, request, obj, form, change):
        """Track if profit was manually edited."""
        if change and 'profit' in form.changed_data:
            obj.profit_was_edited = True
        super().save_model(request, obj, form, change)


# =============================================================================
# NOTIFICATION ADMIN
# =============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for Notification model."""
    
    list_display = [
        'title', 'user_display', 'type_badge', 
        'read_status', 'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__email']
    autocomplete_fields = ['user', 'related_kiosk']
    readonly_fields = ['created_at', 'read_at']
    actions = ['mark_as_read', 'mark_as_unread']
    
    fieldsets = (
        ('Recipient', {'fields': ('user',)}),
        ('Content', {'fields': ('title', 'message', 'notification_type')}),
        ('Action', {'fields': ('action_url', 'related_kiosk')}),
        ('Status', {'fields': ('is_read', 'read_at')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )
    
    def user_display(self, obj):
        return obj.user.display_name
    user_display.short_description = 'User'
    
    def type_badge(self, obj):
        colors = {
            'INVITE': '#3b82f6',
            'ALERT': '#f59e0b',
            'FRAUD': '#ef4444',
            'SYSTEM': '#6b7280',
            'SUMMARY': '#8b5cf6',
        }
        color = colors.get(obj.notification_type, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_notification_type_display()
        )
    type_badge.short_description = 'Type'
    
    def read_status(self, obj):
        if obj.is_read:
            return format_html('<span style="color: #22c55e;">✓ Read</span>')
        return format_html('<span style="color: #3b82f6; font-weight: bold;">● Unread</span>')
    read_status.short_description = 'Status'
    
    @admin.action(description='Mark selected as read')
    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{count} notifications marked as read.')
    
    @admin.action(description='Mark selected as unread')
    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{count} notifications marked as unread.')


# =============================================================================
# PUSH SUBSCRIPTION ADMIN
# =============================================================================

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    """Admin configuration for PushSubscription model."""
    
    list_display = ['user_display', 'is_active', 'last_used_at', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__email', 'endpoint']
    autocomplete_fields = ['user']
    readonly_fields = ['endpoint', 'p256dh_key', 'auth_key', 'user_agent', 'created_at', 'last_used_at']
    
    def user_display(self, obj):
        return obj.user.display_name
    user_display.short_description = 'User'


# =============================================================================
# NOTIFICATION PREFERENCE ADMIN
# =============================================================================

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationPreference model."""
    
    list_display = [
        'user_display', 'push_enabled', 'email_enabled', 
        'daily_summary_enabled', 'summary_time', 'updated_at'
    ]
    list_filter = ['push_enabled', 'email_enabled', 'daily_summary_enabled']
    search_fields = ['user__email']
    autocomplete_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Channel Preferences', {'fields': ('push_enabled', 'email_enabled')}),
        ('Notification Types', {'fields': (
            'invites_enabled', 'fraud_alerts_enabled', 
            'system_messages_enabled', 'transaction_alerts_enabled'
        )}),
        ('Daily Summary', {'fields': ('daily_summary_enabled', 'summary_time')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    def user_display(self, obj):
        return obj.user.display_name
    user_display.short_description = 'User'


# =============================================================================
# KIOSK INVITATION ADMIN
# =============================================================================

@admin.register(KioskInvitation)
class KioskInvitationAdmin(admin.ModelAdmin):
    """Admin interface for kiosk invitations."""
    
    list_display = ['email', 'kiosk', 'role', 'status', 'invited_by', 'created_at', 'expires_at']
    list_filter = ['status', 'role', 'created_at']
    search_fields = ['email', 'kiosk__name', 'invited_by__email']
    date_hierarchy = 'created_at'
    readonly_fields = ['token', 'created_at', 'accepted_at']
    
    fieldsets = (
        ('Invitation', {'fields': ('kiosk', 'email', 'role', 'status')}),
        ('Inviter', {'fields': ('invited_by', 'message')}),
        ('Token & Dates', {'fields': ('token', 'created_at', 'expires_at', 'accepted_at')}),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('kiosk', 'invited_by')


# =============================================================================
# FRAUD REPORT ADMIN
# =============================================================================

@admin.register(FraudReport)
class FraudReportAdmin(admin.ModelAdmin):
    """Admin interface for fraud reports."""
    
    list_display = ['phone_number', 'scammer_name', 'report_type', 'is_verified', 'reporter', 'created_at']
    list_filter = ['report_type', 'is_verified', 'created_at']
    search_fields = ['phone_number', 'scammer_name', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'is_verified']
    
    fieldsets = (
        ('Scammer Info', {'fields': ('phone_number', 'scammer_name', 'report_type')}),
        ('Report', {'fields': ('description', 'proof_image')}),
        ('Reporter', {'fields': ('reporter', 'reporter_kiosk', 'reporter_location')}),
        ('Status', {'fields': ('is_verified', 'created_at')}),
    )
    
    actions = ['mark_as_verified', 'mark_as_unverified']
    
    @admin.action(description='Mark selected as verified threat')
    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)
    
    @admin.action(description='Mark selected as unverified')
    def mark_as_unverified(self, request, queryset):
        queryset.update(is_verified=False)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reporter', 'reporter_kiosk')

