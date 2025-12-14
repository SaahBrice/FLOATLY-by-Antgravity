"""
Fraud Report Admin configuration for Floatly.
"""

from django.contrib import admin

from ..models import FraudReport


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
