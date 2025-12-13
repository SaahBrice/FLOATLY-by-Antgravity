"""
URL configuration for the Core app.
"""

from django.urls import path, include
from . import views
from . import auth_views
from . import dashboard_views
from . import transaction_views
from . import kiosk_views
from . import notification_views
from . import team_views
from . import fraud_views
from . import feedback_views

app_name = 'core'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    
    # Registration
    path('auth/register/', auth_views.RegisterView.as_view(), name='register'),
    
    # Login/Logout
    path('auth/login/', auth_views.LoginView.as_view(), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Email verification
    path('auth/verification-pending/', auth_views.VerificationPendingView.as_view(), name='verification_pending'),
    path('auth/verification-success/', auth_views.VerificationSuccessView.as_view(), name='verification_success'),
    path('auth/resend-verification/', auth_views.ResendVerificationView.as_view(), name='resend_verification'),
    
    # Onboarding
    path('onboarding/', auth_views.OnboardingView.as_view(), name='onboarding'),
    
    # =========================================================================
    # DASHBOARD & KIOSKS
    # =========================================================================
    
    # Main dashboard
    path('dashboard/', dashboard_views.DashboardView.as_view(), name='dashboard'),
    
    # Kiosk switching (HTMX)
    path('kiosk/<slug:slug>/switch/', dashboard_views.KioskSwitchView.as_view(), name='kiosk_switch'),
    
    # Dashboard chart data API
    path('api/chart-data/', dashboard_views.ChartDataView.as_view(), name='chart_data'),
    
    # Kiosk management
    path('kiosk/<slug:slug>/edit/', kiosk_views.EditKioskView.as_view(), name='edit_kiosk'),
    path('kiosk/<slug:slug>/delete/', kiosk_views.DeleteKioskView.as_view(), name='delete_kiosk'),
    
    # =========================================================================
    # TRANSACTIONS
    # =========================================================================
    
    # Transaction list/search
    path('transactions/', transaction_views.TransactionListView.as_view(), name='transactions'),
    
    # Add transaction
    path('transactions/add/', transaction_views.AddTransactionView.as_view(), name='add_transaction'),
    path('transactions/add/<slug:kiosk_slug>/', transaction_views.AddTransactionView.as_view(), name='add_transaction_kiosk'),
    
    # Edit/Delete transaction
    path('transactions/<int:pk>/edit/', transaction_views.EditTransactionView.as_view(), name='edit_transaction'),
    path('transactions/<int:pk>/delete/', transaction_views.DeleteTransactionView.as_view(), name='delete_transaction'),
    path('transactions/<int:pk>/actions/', transaction_views.TransactionActionsView.as_view(), name='transaction_actions'),
    
    # HTMX profit calculation
    path('transactions/calculate-profit/', transaction_views.CalculateProfitView.as_view(), name='calculate_profit'),
    
    # Receipt image processing (AI)
    path('transactions/process-receipt/', transaction_views.ProcessReceiptImageView.as_view(), name='process_receipt'),
    
    # Voice recording processing (AI)
    path('transactions/process-voice/', transaction_views.ProcessVoiceView.as_view(), name='process_voice'),
    
    # PWA Share Target
    path('share/', transaction_views.ShareTargetView.as_view(), name='share_target'),
    
    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    
    # Notification center
    path('notifications/', notification_views.NotificationCenterView.as_view(), name='notifications'),
    path('notifications/load/', notification_views.NotificationListPartialView.as_view(), name='notifications_load'),
    path('notifications/dropdown/', notification_views.NotificationDropdownView.as_view(), name='notification_dropdown'),
    
    # Notification actions
    path('notifications/<int:pk>/read/', notification_views.MarkAsReadView.as_view(), name='mark_notification_read'),
    path('notifications/mark-all-read/', notification_views.MarkAllReadView.as_view(), name='mark_all_notifications_read'),
    path('notifications/unread-count/', notification_views.UnreadCountView.as_view(), name='notification_unread_count'),
    
    # Push subscription
    path('api/push/register/', notification_views.RegisterPushView.as_view(), name='register_push'),
    path('api/push/unregister/', notification_views.UnregisterPushView.as_view(), name='unregister_push'),
    
    # Notification preferences
    path('settings/notifications/', notification_views.NotificationPreferencesView.as_view(), name='notification_preferences'),
    
    # =========================================================================
    # TEAM MANAGEMENT
    # =========================================================================
    
    path('kiosk/<slug:slug>/team/', team_views.TeamManagementView.as_view(), name='team_manage'),
    path('kiosk/<slug:slug>/team/invite/', team_views.InviteMemberView.as_view(), name='team_invite'),
    path('kiosk/<slug:slug>/team/<int:member_id>/remove/', team_views.RemoveMemberView.as_view(), name='team_remove'),
    path('kiosk/<slug:slug>/team/<int:member_id>/role/', team_views.ChangeMemberRoleView.as_view(), name='team_role'),
    path('kiosk/<slug:slug>/team/invite/<int:invite_id>/cancel/', team_views.CancelInvitationView.as_view(), name='team_cancel_invite'),
    
    # Invitation acceptance (token-based, no login required initially)
    path('invite/<uuid:token>/', team_views.AcceptInvitationView.as_view(), name='accept_invitation'),
    
    # =========================================================================
    # FRAUD REPORTING
    # =========================================================================
    
    path('fraud/report/', fraud_views.ReportFraudView.as_view(), name='fraud_report'),
    path('blacklist/', fraud_views.BlacklistView.as_view(), name='blacklist'),
    path('fraud/report/<int:pk>/', fraud_views.ReportDetailView.as_view(), name='fraud_detail'),
    path('api/check-phone/', fraud_views.CheckPhoneView.as_view(), name='check_phone'),
    
    # =========================================================================
    # FEEDBACK
    # =========================================================================
    
    path('feedback/', feedback_views.FeedbackSubmitView.as_view(), name='feedback'),
    
    # Include allauth URLs for email confirmation and social auth
    path('accounts/', include('allauth.urls')),
]




