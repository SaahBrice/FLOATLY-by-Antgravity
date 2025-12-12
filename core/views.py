"""
Views for the Core app.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """
    Health check endpoint to verify the application is running.
    Returns JSON with system status.
    """
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return JsonResponse({
        "status": "ok",
        "service": "Floatly",
        "version": "1.0.0",
        "database": db_status,
        "features": {
            "transactions": "pending",
            "kiosks": "pending",
            "notifications": "pending",
            "auto_profit": "pending",
        }
    })


def home(request):
    """
    Home page view.
    Shows the landing page or dashboard based on authentication status.
    """
    context = {
        'app_name': 'Floatly',
        'tagline': 'Digital Logbook for Mobile Money Agents',
    }
    return render(request, 'core/home.html', context)
