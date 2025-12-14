"""
Floatly Database Models Package

Complete data structure for the mobile money agent logbook:
- User: Custom user model with email login and Google OAuth support
- Kiosk: Agent kiosk locations
- KioskMember: Team management with roles
- Network: Mobile money networks (MTN, Orange, etc.)
- CommissionRate: Commission rules per network and amount range
- Transaction: Every money movement with auto-calculated profit
- Notification: Alerts, invites, and system messages
- PushSubscription: Push notification subscriptions
- NotificationPreference: User notification settings
- KioskInvitation: Team invitations
- FraudReport: Community fraud reporting
- Feedback: User feedback system
"""

# Import all models for backward compatibility
# Any code using `from core.models import User` will continue working

from .user import User, phone_validator
from .kiosk import Kiosk, KioskMember
from .network import Network, CommissionRate
from .transaction import Transaction
from .notification import Notification, PushSubscription, NotificationPreference
from .invitation import KioskInvitation
from .fraud import FraudReport, Feedback


# Define __all__ for explicit exports
__all__ = [
    # Validators
    'phone_validator',
    
    # User
    'User',
    
    # Kiosk
    'Kiosk',
    'KioskMember',
    
    # Network
    'Network',
    'CommissionRate',
    
    # Transaction
    'Transaction',
    
    # Notification
    'Notification',
    'PushSubscription',
    'NotificationPreference',
    
    # Invitation
    'KioskInvitation',
    
    # Fraud & Feedback
    'FraudReport',
    'Feedback',
]
