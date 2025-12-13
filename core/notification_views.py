"""
Notification Views for Floatly.

Handles:
- Notification center (full page with filters)
- Mark as read/unread
- Unread count for badge
- Push subscription registration
"""

import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Notification, PushSubscription, NotificationPreference

logger = logging.getLogger('core.notifications')


# =============================================================================
# NOTIFICATION CENTER
# =============================================================================

class NotificationCenterView(LoginRequiredMixin, ListView):
    """
    Full notification center page with filtering and pagination.
    """
    model = Notification
    template_name = 'notifications/center.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        
        # Filter by type if specified
        filter_type = self.request.GET.get('type', 'all')
        if filter_type != 'all':
            qs = qs.filter(notification_type=filter_type.upper())
        
        # Filter by read status
        read_filter = self.request.GET.get('read')
        if read_filter == 'unread':
            qs = qs.filter(is_read=False)
        elif read_filter == 'read':
            qs = qs.filter(is_read=True)
        
        return qs.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_type'] = self.request.GET.get('type', 'all')
        context['read_filter'] = self.request.GET.get('read', 'all')
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user, 
            is_read=False
        ).count()
        
        # Notification type choices for filter
        context['type_choices'] = [
            ('all', 'All'),
            ('invite', 'Invitations'),
            ('fraud', 'Fraud Alerts'),
            ('system', 'System'),
            ('summary', 'Summaries'),
            ('transaction', 'Transactions'),
        ]
        
        return context


class NotificationListPartialView(LoginRequiredMixin, View):
    """
    HTMX partial for loading more notifications (infinite scroll).
    """
    
    def get(self, request):
        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 20)
        filter_type = request.GET.get('type', 'all')
        
        qs = Notification.objects.filter(user=request.user)
        
        if filter_type != 'all':
            qs = qs.filter(notification_type=filter_type.upper())
        
        qs = qs.order_by('-created_at')
        
        paginator = Paginator(qs, limit)
        notifications = paginator.get_page(page)
        
        return render(request, 'notifications/partials/_notification_list.html', {
            'notifications': notifications,
            'has_next': notifications.has_next(),
            'next_page': notifications.next_page_number() if notifications.has_next() else None
        })


# =============================================================================
# NOTIFICATION ACTIONS
# =============================================================================

class MarkAsReadView(LoginRequiredMixin, View):
    """
    Mark a single notification as read.
    Returns the action_url to redirect to if specified.
    """
    
    def post(self, request, pk):
        notification = get_object_or_404(
            Notification, 
            pk=pk, 
            user=request.user
        )
        
        notification.mark_as_read()
        logger.debug(f"Marked notification {pk} as read for user {request.user.email}")
        
        # For HTMX requests, return updated partial
        if request.headers.get('HX-Request'):
            return render(request, 'notifications/partials/_notification_item.html', {
                'notification': notification
            })
        
        # For regular requests, redirect to action_url or notifications
        if notification.action_url:
            return redirect(notification.action_url)
        return redirect('core:notifications')


class MarkAllReadView(LoginRequiredMixin, View):
    """
    Mark all notifications as read for the current user.
    """
    
    def post(self, request):
        from .notification_service import mark_all_as_read
        
        count = mark_all_as_read(request.user)
        
        if request.headers.get('HX-Request'):
            return HttpResponse(
                f'<span class="text-sm text-green-500">✓ Marked {count} as read</span>',
                headers={'HX-Trigger': 'notificationsUpdated'}
            )
        
        return redirect('core:notifications')


class UnreadCountView(LoginRequiredMixin, View):
    """
    Return unread notification count as JSON.
    Used by the bell badge to update count.
    """
    
    def get(self, request):
        count = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        return JsonResponse({'count': count})


# =============================================================================
# PUSH SUBSCRIPTION
# =============================================================================

class RegisterPushView(LoginRequiredMixin, View):
    """
    Register a push notification subscription.
    Called when user enables push notifications.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            endpoint = data.get('endpoint')
            keys = data.get('keys', {})
            
            if not endpoint:
                return JsonResponse({'error': 'Missing endpoint'}, status=400)
            
            # Create or update subscription
            subscription, created = PushSubscription.objects.update_or_create(
                user=request.user,
                endpoint=endpoint,
                defaults={
                    'p256dh_key': keys.get('p256dh', ''),
                    'auth_key': keys.get('auth', ''),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                    'is_active': True
                }
            )
            
            action = 'registered' if created else 'updated'
            logger.info(f"Push subscription {action} for user {request.user.email}")
            
            return JsonResponse({
                'success': True,
                'message': f'Push subscription {action}'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Push registration failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)


class UnregisterPushView(LoginRequiredMixin, View):
    """
    Unregister a push notification subscription.
    Called when user disables push notifications.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            endpoint = data.get('endpoint')
            
            if endpoint:
                PushSubscription.objects.filter(
                    user=request.user,
                    endpoint=endpoint
                ).update(is_active=False)
            else:
                # Disable all subscriptions for user
                PushSubscription.objects.filter(
                    user=request.user
                ).update(is_active=False)
            
            logger.info(f"Push subscription(s) disabled for user {request.user.email}")
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Push unregistration failed: {e}")
            return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# NOTIFICATION PREFERENCES
# =============================================================================

class NotificationPreferencesView(LoginRequiredMixin, View):
    """
    View and update notification preferences.
    """
    
    def get(self, request):
        prefs = NotificationPreference.get_or_create_for_user(request.user)
        
        # For HTMX partial
        if request.headers.get('HX-Request'):
            return render(request, 'settings/partials/_notification_prefs.html', {
                'prefs': prefs
            })
        
        return render(request, 'settings/notification_preferences.html', {
            'prefs': prefs
        })
    
    def post(self, request):
        prefs = NotificationPreference.get_or_create_for_user(request.user)
        
        # Update boolean fields
        boolean_fields = [
            'push_enabled', 'email_enabled', 'invites_enabled',
            'fraud_alerts_enabled', 'system_messages_enabled',
            'transaction_alerts_enabled', 'daily_summary_enabled'
        ]
        
        for field in boolean_fields:
            if field in request.POST:
                setattr(prefs, field, request.POST.get(field) == 'on')
            else:
                # Unchecked checkboxes don't appear in POST data
                setattr(prefs, field, False)
        
        # Update summary time
        summary_time = request.POST.get('summary_time')
        if summary_time:
            try:
                prefs.summary_time = summary_time
            except Exception:
                pass
        
        prefs.save()
        
        logger.info(f"Notification preferences updated for user {request.user.email}")
        
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<span class="text-green-500">✓ Preferences saved</span>',
                headers={'HX-Trigger': 'preferencesSaved'}
            )
        
        return redirect('core:notification_preferences')


# =============================================================================
# DROPDOWN PREVIEW
# =============================================================================

class NotificationDropdownView(LoginRequiredMixin, View):
    """
    Return recent notifications for dropdown preview in header.
    """
    
    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return render(request, 'notifications/partials/_dropdown.html', {
            'notifications': notifications,
            'unread_count': unread_count
        })
