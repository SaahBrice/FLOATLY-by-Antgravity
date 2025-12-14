"""
Admin configuration for Daily Balance models.
"""

from django.contrib import admin
from core.models import DailyOpeningBalance, NetworkFloatBalance


class NetworkFloatBalanceInline(admin.TabularInline):
    """Inline admin for network float balances."""
    model = NetworkFloatBalance
    extra = 0
    readonly_fields = ['network']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(DailyOpeningBalance)
class DailyOpeningBalanceAdmin(admin.ModelAdmin):
    """Admin for daily opening balances."""
    list_display = ['kiosk', 'date', 'opening_cash', 'adjustment_reason', 'created_by', 'created_at']
    list_filter = ['date', 'adjustment_reason', 'kiosk']
    search_fields = ['kiosk__name', 'adjustment_notes']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [NetworkFloatBalanceInline]
    ordering = ['-date', 'kiosk']
    date_hierarchy = 'date'
