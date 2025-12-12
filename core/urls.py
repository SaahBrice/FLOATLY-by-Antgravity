"""
URL configuration for the Core app.
"""

from django.urls import path, include
from . import views
from . import auth_views
from . import dashboard_views
from . import transaction_views
from . import kiosk_views

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
    
    # Kiosk management
    path('kiosk/<slug:slug>/edit/', kiosk_views.EditKioskView.as_view(), name='edit_kiosk'),
    path('kiosk/<slug:slug>/delete/', kiosk_views.DeleteKioskView.as_view(), name='delete_kiosk'),
    
    # =========================================================================
    # TRANSACTIONS
    # =========================================================================
    
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
    
    # PWA Share Target
    path('share/', transaction_views.ShareTargetView.as_view(), name='share_target'),
    
    # Include allauth URLs for email confirmation and social auth
    path('accounts/', include('allauth.urls')),
]


