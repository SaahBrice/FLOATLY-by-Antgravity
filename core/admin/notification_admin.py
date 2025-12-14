"""
Notification Admin configuration for Floatly.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from ..models import Notification, PushSubscription, NotificationPreference, KioskInvitation


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
