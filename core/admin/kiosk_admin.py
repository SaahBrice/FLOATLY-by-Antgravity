"""
Kiosk Admin configuration for Floatly.
"""

from django.contrib import admin
from django.utils.html import format_html

from ..models import Kiosk, KioskMember


class KioskMemberInline(admin.TabularInline):
    """Inline editor for kiosk team members."""
    model = KioskMember
    extra = 0
    autocomplete_fields = ['user']
    readonly_fields = ['joined_at']


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
