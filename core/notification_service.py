"""
Notification Service for Floatly.

Handles sending notifications through three channels:
1. In-app notifications (always)
2. Push notifications (via VAPID web push)
3. Email notifications (via SMTP)

Respects user preferences for each channel and type.
"""

import logging
import json
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

logger = logging.getLogger('core.notifications')


# =============================================================================
# MAIN NOTIFICATION DISPATCHER
# =============================================================================

def send_notification(
    user,
    title,
    message,
    notification_type='SYSTEM',
    priority='NORMAL',
    action_url='',
    related_kiosk=None,
    related_transaction=None
):
    """
    Create in-app notification and dispatch to appropriate channels.
    
    Priority determines channels:
    - LOW: In-app only
    - NORMAL: In-app + Push (if enabled)
    - HIGH: In-app + Push + Email (if enabled)
    
    Args:
        user: User to notify
        title: Notification title
        message: Notification body
        notification_type: One of INVITE, ALERT, FRAUD, SYSTEM, SUMMARY, TRANSACTION
        priority: LOW, NORMAL, or HIGH
        action_url: URL to navigate when clicked
        related_kiosk: Optional kiosk reference
        related_transaction: Optional transaction reference
        
    Returns:
        Notification: The created notification object
    """
    from .models import Notification, NotificationPreference
    
    # Check if user wants this type of notification
    prefs = NotificationPreference.get_or_create_for_user(user)
    
    # Type-based filtering
    type_enabled = _is_notification_type_enabled(prefs, notification_type)
    if not type_enabled:
        logger.debug(f"Notification type {notification_type} disabled for user {user.email}")
        return None
    
    # Create in-app notification
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        related_kiosk=related_kiosk,
        related_transaction=related_transaction
    )
    
    logger.info(f"Created notification '{title}' for user {user.email} [type={notification_type}, priority={priority}]")
    
    # Dispatch to other channels based on priority
    if priority in ('NORMAL', 'HIGH') and prefs.push_enabled:
        push_sent = send_push_notification(user, title, message, action_url)
        if push_sent:
            notification.push_sent = True
            notification.save(update_fields=['push_sent'])
    
    if priority == 'HIGH' and prefs.email_enabled:
        email_sent = send_email_notification(user, notification)
        if email_sent:
            notification.email_sent = True
            notification.save(update_fields=['email_sent'])
    
    return notification


def _is_notification_type_enabled(prefs, notification_type):
    """Check if a notification type is enabled in user preferences."""
    type_map = {
        'INVITE': prefs.invites_enabled,
        'FRAUD': prefs.fraud_alerts_enabled,
        'SYSTEM': prefs.system_messages_enabled,
        'SUMMARY': prefs.daily_summary_enabled,
        'TRANSACTION': prefs.transaction_alerts_enabled,
        'ALERT': True,  # Always enabled
    }
    return type_map.get(notification_type, True)


# =============================================================================
# PUSH NOTIFICATIONS (VAPID Web Push)
# =============================================================================

def send_push_notification(user, title, body, url=None, icon=None):
    """
    Send push notification to all active subscriptions for a user.
    
    Args:
        user: User to send push to
        title: Notification title
        body: Notification body text
        url: Optional URL to open when clicked
        icon: Optional icon URL
        
    Returns:
        bool: True if at least one push was sent successfully
    """
    from .models import PushSubscription
    
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush not installed, skipping push notification")
        return False
    
    subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
    
    if not subscriptions.exists():
        logger.debug(f"No active push subscriptions for user {user.email}")
        return False
    
    # Build notification payload
    payload = json.dumps({
        'title': title,
        'body': body,
        'icon': icon or '/static/images/icon-192x192.png',
        'badge': '/static/images/badge-72x72.png',
        'tag': 'floatly-notification',
        'data': {
            'url': url or '/notifications/'
        }
    })
    
    vapid_claims = {
        'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'
    }
    
    success_count = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {
                        'p256dh': sub.p256dh_key,
                        'auth': sub.auth_key
                    }
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims
            )
            
            # Update last used timestamp
            sub.last_used_at = timezone.now()
            sub.save(update_fields=['last_used_at'])
            success_count += 1
            
            logger.debug(f"Push sent to subscription {sub.id} for user {user.email}")
            
        except WebPushException as e:
            logger.warning(f"Push failed for subscription {sub.id}: {e}")
            
            # Mark subscription as inactive if it's no longer valid
            if e.response and e.response.status_code in (404, 410):
                sub.is_active = False
                sub.save(update_fields=['is_active'])
                logger.info(f"Deactivated invalid push subscription {sub.id}")
        
        except Exception as e:
            logger.error(f"Unexpected push error for subscription {sub.id}: {e}")
    
    logger.info(f"Push notifications: {success_count}/{subscriptions.count()} sent for user {user.email}")
    return success_count > 0


# =============================================================================
# EMAIL NOTIFICATIONS
# =============================================================================

def send_email_notification(user, notification):
    """
    Send email notification to user.
    
    Args:
        user: User to email
        notification: Notification object with details
        
    Returns:
        bool: True if email was sent successfully
    """
    if not user.email:
        logger.warning(f"User {user.id} has no email address")
        return False
    
    # Select template based on notification type
    template_map = {
        'INVITE': 'emails/notification_invite.html',
        'FRAUD': 'emails/notification_fraud.html',
        'SUMMARY': 'emails/notification_summary.html',
    }
    template_name = template_map.get(notification.notification_type, 'emails/notification_base.html')
    
    # Build context
    context = {
        'user': user,
        'notification': notification,
        'action_url': notification.action_url,
        'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
        'year': timezone.now().year,
    }
    
    try:
        # Render HTML email
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=notification.title,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Email notification sent to {user.email}: {notification.title}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {user.email}: {e}")
        return False


# =============================================================================
# SPECIALIZED NOTIFICATION CREATORS
# =============================================================================

def notify_kiosk_invitation(user, kiosk, invited_by, invitation=None):
    """Send invitation notification through all channels."""
    from .models import Notification
    
    title = f"🎉 Invitation to {kiosk.name}"
    message = f"{invited_by.display_name} has invited you to join {kiosk.name} as a team member. Accept to start managing transactions."
    
    # Use token URL if invitation provided, else fallback
    if invitation:
        action_url = f"/invite/{invitation.token}/"
    else:
        action_url = f"/kiosks/{kiosk.slug}/accept-invite/"
    
    return send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='INVITE',
        priority='HIGH',
        action_url=action_url,
        related_kiosk=kiosk
    )


def notify_fraud_alert(user, phone_number, details, reporter=None):
    """Send fraud alert notification through all channels."""
    title = f"🚨 Fraud Alert: {phone_number}"
    message = details
    if reporter:
        message = f"Reported by {reporter.display_name}: {details}"
    
    return send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='FRAUD',
        priority='HIGH',
        action_url="/blacklist/"
    )


def notify_transaction_activity(user, transaction, action='created', actor=None):
    """
    Notify user about transaction activity by team members.
    
    Args:
        user: User to notify
        transaction: Transaction object
        action: 'created', 'edited', or 'deleted'
        actor: User who performed the action
    """
    # Don't notify the user who performed the action
    if actor and actor.id == user.id:
        return None
    
    action_text = {
        'created': 'added',
        'edited': 'edited',
        'deleted': 'deleted'
    }.get(action, action)
    
    actor_name = actor.display_name if actor else 'Someone'
    
    title = f"💰 Transaction {action_text}"
    message = f"{actor_name} {action_text} a {transaction.get_transaction_type_display()} of {transaction.amount:,.0f} CFA in {transaction.kiosk.name}."
    
    return send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='TRANSACTION',
        priority='NORMAL',
        action_url=f"/dashboard/?kiosk={transaction.kiosk.slug}",
        related_kiosk=transaction.kiosk,
        related_transaction=transaction
    )


def notify_kiosk_change(user, kiosk, action='edited', actor=None):
    """
    Notify user about kiosk changes.
    
    Args:
        user: User to notify
        kiosk: Kiosk object
        action: 'edited' or 'deleted'
        actor: User who performed the action
    """
    # Don't notify the user who performed the action
    if actor and actor.id == user.id:
        return None
    
    actor_name = actor.display_name if actor else 'Someone'
    
    if action == 'deleted':
        title = f"🗑️ Kiosk Deleted"
        message = f"{actor_name} has deleted the kiosk '{kiosk.name}'. All associated data has been removed."
        priority = 'HIGH'
    else:
        title = f"✏️ Kiosk Updated"
        message = f"{actor_name} has updated the settings for {kiosk.name}."
        priority = 'NORMAL'
    
    return send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='SYSTEM',
        priority=priority,
        action_url=f"/dashboard/?kiosk={kiosk.slug}" if action != 'deleted' else "/dashboard/",
        related_kiosk=kiosk if action != 'deleted' else None
    )


def create_daily_summary(user, kiosk, stats):
    """
    Create daily summary notification.
    
    Args:
        user: User to send summary to
        kiosk: Kiosk to summarize
        stats: Dict with 'count', 'profit', 'deposits', 'withdrawals'
    """
    title = f"📊 Daily Summary - {kiosk.name}"
    message = (
        f"Today's activity:\n"
        f"• Transactions: {stats.get('count', 0)}\n"
        f"• Deposits: {stats.get('deposits', 0):,.0f} CFA\n"
        f"• Withdrawals: {stats.get('withdrawals', 0):,.0f} CFA\n"
        f"• Profit: {stats.get('profit', 0):,.0f} CFA"
    )
    
    return send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='SUMMARY',
        priority='HIGH',  # Daily summaries are high priority
        action_url=f"/dashboard/?kiosk={kiosk.slug}",
        related_kiosk=kiosk
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_unread_count(user):
    """Get count of unread notifications for a user."""
    from .models import Notification
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_all_as_read(user):
    """Mark all unread notifications as read for a user."""
    from .models import Notification
    count = Notification.objects.filter(user=user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    logger.info(f"Marked {count} notifications as read for user {user.email}")
    return count
