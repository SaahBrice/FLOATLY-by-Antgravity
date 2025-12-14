"""
AI-powered views for Floatly.

Handles:
- Receipt image processing with AI extraction
- Voice recording processing with AI transcription
"""

import logging
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse

from .models import Network
from .gemini_service import extract_transaction_from_image, extract_transaction_from_voice

# Logger for AI operations
logger = logging.getLogger('core.ai')


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
        
        logger.info(
            f"Receipt processed: user={request.user.email}, "
            f"network={result.get('network')}, amount={result.get('amount')}"
        )
        
        return JsonResponse(result)


class ProcessVoiceView(LoginRequiredMixin, View):
    """
    Endpoint for processing voice recordings with AI.
    Returns extracted transaction data as JSON.
    """
    
    def post(self, request):
        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No audio provided'}, status=400)
        
        audio_file = request.FILES['audio']
        
        # Validate file type
        allowed_types = ['audio/webm', 'audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/ogg']
        content_type = audio_file.content_type
        
        # Be lenient with content type matching
        is_valid = any(t in content_type for t in ['audio', 'webm', 'ogg'])
        if not is_valid:
            return JsonResponse({'error': f'Invalid audio type: {content_type}'}, status=400)
        
        # Validate file size (max 2MB for 10s audio)
        if audio_file.size > 2 * 1024 * 1024:
            return JsonResponse({'error': 'Audio too large (max 2MB)'}, status=400)
        
        # Extract data using Gemini
        audio_data = audio_file.read()
        result = extract_transaction_from_voice(audio_data, content_type)
        
        # Map network code to ID
        if result.get('network'):
            try:
                network = Network.objects.get(code=result['network'])
                result['network_id'] = network.id
            except Network.DoesNotExist:
                pass
        
        logger.info(
            f"Voice processed: user={request.user.email}, "
            f"network={result.get('network')}, amount={result.get('amount')}"
        )
        
        return JsonResponse(result)
