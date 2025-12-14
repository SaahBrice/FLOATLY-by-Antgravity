"""
Transaction and Network Admin configuration for Floatly.
"""

from django.contrib import admin
from django.utils.html import format_html

from ..models import Network, CommissionRate, Transaction


class CommissionRateInline(admin.TabularInline):
    """Inline editor for commission rates."""
    model = CommissionRate
    extra = 0
    fields = ['min_amount', 'max_amount', 'rate_type', 'rate_value', 'is_active']


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
