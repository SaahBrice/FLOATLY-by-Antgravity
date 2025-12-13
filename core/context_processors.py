"""
Custom context processors for Floatly templates.
"""

from django.conf import settings


def vapid_key(request):
    """
    Add VAPID public key to template context for push notification subscription.
    """
    return {
        'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
    }
