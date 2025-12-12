"""
Transaction views for Floatly.

Handles:
- Transaction entry form
- Profit calculation (HTMX)
- SMS text share handling
- Photo upload and AI extraction
"""

import logging
import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.urls import reverse

from .models import Kiosk, KioskMember, Network, CommissionRate, Transaction
from .transaction_forms import TransactionForm
from .sms_parser import parse_sms
from .gemini_service import extract_transaction_from_image

# Logger for transaction operations
logger = logging.getLogger('core.transactions')


class AddTransactionView(LoginRequiredMixin, FormView):
    """
    Main transaction entry view.
    Supports manual entry, SMS pre-fill, and photo upload.
    """
    template_name = 'transactions/add.html'
    form_class = TransactionForm
    login_url = '/auth/login/'
    
    def dispatch(self, request, *args, **kwargs):
        # Get kiosk from URL or session
        kiosk_slug = kwargs.get('kiosk_slug') or request.GET.get('kiosk')
        
        if kiosk_slug:
            self.kiosk = get_object_or_404(Kiosk, slug=kiosk_slug, is_active=True)
        else:
            # Try to get from session or first owned kiosk
            self.kiosk = self._get_default_kiosk(request.user)
        
        if not self.kiosk:
            messages.error(request, 'Please select a kiosk first.')
            return redirect('core:dashboard')
        
        # Verify access
        if not self._user_can_access_kiosk(request.user, self.kiosk):
            raise Http404("Access denied")
        
        return super().dispatch(request, *args, **kwargs)
    
    def _get_default_kiosk(self, user):
        """Get user's default kiosk (first owned or member of)."""
        if not user.is_authenticated:
            return None
        
        kiosk = Kiosk.objects.filter(owner=user, is_active=True).first()
        if not kiosk:
            membership = KioskMember.objects.filter(user=user, kiosk__is_active=True).first()
            if membership:
                kiosk = membership.kiosk
        
        return kiosk
    
    def _user_can_access_kiosk(self, user, kiosk):
        """Check if user has access to kiosk."""
        if kiosk.owner == user:
            return True
        return KioskMember.objects.filter(kiosk=kiosk, user=user).exists()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['kiosk'] = self.kiosk
        kwargs['user'] = self.request.user
        
        # Check for SMS text in GET params (from share)
        sms_text = self.request.GET.get('text', '')
        if sms_text:
            # Parse SMS and use as initial data
            parsed = parse_sms(sms_text)
            initial = kwargs.get('initial', {})
            
            if parsed.get('network'):
                try:
                    network = Network.objects.get(code=parsed['network'])
                    initial['network'] = network.id
                except Network.DoesNotExist:
                    pass
            
            if parsed.get('transaction_type'):
                initial['transaction_type'] = parsed['transaction_type']
            
            if parsed.get('amount'):
                initial['amount'] = parsed['amount']
            
            if parsed.get('customer_phone'):
                initial['customer_phone'] = parsed['customer_phone']
            
            if parsed.get('transaction_ref'):
                initial['transaction_ref'] = parsed['transaction_ref']
            
            initial['sms_text'] = sms_text
            
            kwargs['initial'] = initial
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Add Transaction'
        context['kiosk'] = self.kiosk
        context['networks'] = Network.objects.filter(is_active=True)
        
        # Check if this was from SMS share
        context['from_sms'] = bool(self.request.GET.get('text'))
        context['sms_confidence'] = 0
        
        if context['from_sms']:
            parsed = parse_sms(self.request.GET.get('text', ''))
            context['sms_confidence'] = int(parsed.get('confidence', 0) * 100)
        
        return context
    
    def form_valid(self, form):
        transaction = form.save()
        
        # Log transaction creation
        logger.info(
            f"Transaction created: user={self.request.user.email}, "
            f"kiosk={self.kiosk.name}, type={transaction.transaction_type}, "
            f"amount={transaction.amount}, profit={transaction.profit}, "
            f"network={transaction.network.code}"
        )
        
        messages.success(
            self.request,
            f'✅ Transaction saved! Profit: {transaction.profit:,.0f} CFA'
        )
        
        return redirect('core:dashboard')


class CalculateProfitView(LoginRequiredMixin, View):
    """
    HTMX endpoint for live profit calculation.
    Returns the calculated profit based on amount, network, and type.
    """
    
    def get(self, request):
        try:
            network_id = request.GET.get('network')
            amount_str = request.GET.get('amount', '0')
            transaction_type = request.GET.get('transaction_type', 'DEPOSIT')
            
            # Parse amount
            amount_str = amount_str.replace(',', '').replace(' ', '')
            try:
                amount = Decimal(amount_str) if amount_str else Decimal('0')
            except (InvalidOperation, ValueError):
                amount = Decimal('0')
            
            if not network_id or amount <= 0:
                return render(request, 'transactions/partials/profit_display.html', {
                    'profit': None,
                    'warning': None,
                })
            
            # Get network
            try:
                network = Network.objects.get(id=network_id)
            except Network.DoesNotExist:
                return render(request, 'transactions/partials/profit_display.html', {
                    'profit': None,
                    'warning': 'Invalid network',
                })
            
            # Look up commission rate (rates apply to both deposit and withdrawal)
            rate = CommissionRate.objects.filter(
                network=network,
                min_amount__lte=amount,
                max_amount__gte=amount,
                is_active=True
            ).first()
            
            if rate:
                # Calculate profit and round to 2 decimal places (model constraint)
                if rate.rate_type == 'PERCENTAGE':
                    profit = (amount * rate.rate_value / 100).quantize(Decimal('0.01'))
                else:
                    profit = rate.rate_value.quantize(Decimal('0.01'))
                
                return render(request, 'transactions/partials/profit_display.html', {
                    'profit': profit,
                    'warning': None,
                    'rate_info': f'{rate.rate_value}{"%" if rate.rate_type == "PERCENTAGE" else " CFA"}',
                })
            else:
                return render(request, 'transactions/partials/profit_display.html', {
                    'profit': None,
                    'warning': 'No commission rate found for this amount. Enter profit manually.',
                })
                
        except Exception as e:
            return render(request, 'transactions/partials/profit_display.html', {
                'profit': None,
                'warning': f'Error calculating profit: {str(e)}',
            })


class ProcessReceiptImageView(LoginRequiredMixin, View):
    """
    Endpoint for processing receipt images with AI.
    Returns extracted transaction data as JSON.
    """
    
    def post(self, request):
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        image_file = request.FILES['image']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Invalid image type'}, status=400)
        
        # Validate file size (max 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'Image too large (max 5MB)'}, status=400)
        
        # Extract data using Gemini
        image_data = image_file.read()
        result = extract_transaction_from_image(image_data, image_file.content_type)
        
        # Map network code to ID
        if result.get('network'):
            try:
                network = Network.objects.get(code=result['network'])
                result['network_id'] = network.id
            except Network.DoesNotExist:
                pass
        
        return JsonResponse(result)


class ShareTargetView(LoginRequiredMixin, View):
    """
    PWA Share Target handler.
    Receives shared text (SMS) and redirects to transaction form with pre-filled data.
    """
    
    def get(self, request):
        # Share target sends data as query params
        text = request.GET.get('text', '') or request.GET.get('title', '')
        
        if not text:
            messages.info(request, 'No text was shared.')
            return redirect('core:dashboard')
        
        # Redirect to add transaction with parsed SMS
        return redirect(f"{reverse('core:add_transaction')}?text={text}")
    
    def post(self, request):
        # Some share methods use POST
        text = request.POST.get('text', '') or request.POST.get('title', '')
        
        if not text:
            messages.info(request, 'No text was shared.')
            return redirect('core:dashboard')
        
        return redirect(f"{reverse('core:add_transaction')}?text={text}")
