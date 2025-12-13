"""
Feedback views for Floatly.
Handles feature suggestions and bug reports.
"""

from django.views import View
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import render

from .models import Feedback


class FeedbackSubmitView(LoginRequiredMixin, View):
    """
    Handle feedback submissions via HTMX modal.
    """
    login_url = '/auth/login/'
    
    def get(self, request):
        """Return the feedback form modal."""
        return render(request, 'feedback/modal.html', {
            'feedback_types': Feedback.FEEDBACK_TYPES
        })
    
    def post(self, request):
        """Handle feedback submission."""
        feedback_type = request.POST.get('feedback_type', 'FEATURE')
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        screenshot = request.FILES.get('screenshot')
        
        # Validation
        errors = []
        if not title:
            errors.append('Title is required')
        if not message:
            errors.append('Message is required')
        if len(title) > 200:
            errors.append('Title must be less than 200 characters')
        
        if errors:
            return render(request, 'feedback/modal.html', {
                'feedback_types': Feedback.FEEDBACK_TYPES,
                'errors': errors,
                'title': title,
                'message': message,
                'feedback_type': feedback_type,
            })
        
        # Create feedback
        feedback = Feedback.objects.create(
            user=request.user,
            feedback_type=feedback_type,
            title=title,
            message=message,
            screenshot=screenshot
        )
        
        # Return success response
        return render(request, 'feedback/success.html', {
            'feedback': feedback
        })
