"""
Django Admin configuration for Floatly.

This package provides rich admin interfaces for all models with:
- Custom list displays
- Filters and search
- Inline editing
- Bulk actions
"""

from django.contrib import admin

# Custom admin site configuration
admin.site.site_header = "Floatly Administration"
admin.site.site_title = "Floatly Admin"
admin.site.index_title = "Welcome to Floatly Admin Dashboard"

# Import all admin registrations
from .user_admin import UserAdmin
from .kiosk_admin import KioskAdmin, KioskMemberAdmin
from .transaction_admin import NetworkAdmin, CommissionRateAdmin, TransactionAdmin
from .notification_admin import (
    NotificationAdmin, 
    PushSubscriptionAdmin, 
    NotificationPreferenceAdmin,
    KioskInvitationAdmin
)
from .fraud_admin import FraudReportAdmin
from .daily_balance_admin import DailyOpeningBalanceAdmin


__all__ = [
    'UserAdmin',
    'KioskAdmin',
    'KioskMemberAdmin',
    'NetworkAdmin',
    'CommissionRateAdmin',
    'TransactionAdmin',
    'NotificationAdmin',
    'PushSubscriptionAdmin',
    'NotificationPreferenceAdmin',
    'KioskInvitationAdmin',
    'FraudReportAdmin',
    'DailyOpeningBalanceAdmin',
]

