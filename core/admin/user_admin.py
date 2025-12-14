"""
User Admin configuration for Floatly.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from ..models import User


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
