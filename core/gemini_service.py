"""
Gemini AI service for Floatly.

Uses Google Gemini Flash to extract transaction data from receipt images.
"""

import os
import json
import base64
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Logger for AI/OCR operations
logger = logging.getLogger('core.transactions')


@dataclass
class ExtractedTransactionData:
    """Data extracted from receipt image via AI."""
    network: Optional[str] = None
    transaction_type: Optional[str] = None
    amount: Optional[Decimal] = None
    customer_phone: Optional[str] = None
    transaction_ref: Optional[str] = None
    sender_name: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: float = 0.0
    raw_response: str = ""


class GeminiService:
    """
    Service for interacting with Google Gemini API for image analysis.
    """
    
    MODEL = "gemini-1.5-flash"
    
    EXTRACTION_PROMPT = """Analyze this mobile money transaction receipt/screenshot and extract the following information in JSON format:

{
    "network": "MTN" or "OM" (Orange Money) or "EU" (Express Union) or null,
    "transaction_type": "DEPOSIT" (cash in/received money) or "WITHDRAWAL" (cash out/sent money) or null,
    "amount": number (in CFA, without currency symbol),
    "customer_phone": "phone number" or null,
    "transaction_ref": "transaction ID/reference" or null,
    "sender_name": "sender's name" or null,
    "timestamp": "transaction date/time" or null,
    "confidence": 0.0 to 1.0 (your confidence in the extraction)
}

Important notes:
- For transaction_type: "DEPOSIT" means the kiosk RECEIVED money from a customer (cash in)
- For transaction_type: "WITHDRAWAL" means the kiosk GAVE money to a customer (cash out)
- Amount should be just the number, no currency symbol
- Phone numbers should include country code if visible
- Return ONLY valid JSON, no other text

If you cannot extract any field, set it to null."""

    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_GEMINI_API_KEY', '')
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.MODEL}:generateContent"
    
    def extract_from_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> ExtractedTransactionData:
        """
        Extract transaction data from a receipt image.
        
        Args:
            image_data: Raw image bytes
            mime_type: Image MIME type (image/jpeg, image/png, etc.)
            
        Returns:
            ExtractedTransactionData with the parsed information
        """
        if not self.api_key:
            logger.warning("GOOGLE_GEMINI_API_KEY not set, returning empty result")
            return ExtractedTransactionData(
                raw_response="API key not configured"
            )
        
        try:
            import requests
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare request
            payload = {
                "contents": [{
                    "parts": [
                        {"text": self.EXTRACTION_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 500,
                }
            }
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return ExtractedTransactionData(
                    raw_response=f"API error: {response.status_code}"
                )
            
            # Parse response
            result = response.json()
            text_content = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            return self._parse_ai_response(text_content)
            
        except Exception as e:
            logger.exception(f"Error calling Gemini API: {e}")
            return ExtractedTransactionData(
                raw_response=f"Error: {str(e)}"
            )
    
    def _parse_ai_response(self, response_text: str) -> ExtractedTransactionData:
        """Parse the AI's JSON response into structured data."""
        result = ExtractedTransactionData(raw_response=response_text)
        
        try:
            # Try to extract JSON from the response
            json_match = response_text.strip()
            
            # Remove markdown code blocks if present
            if json_match.startswith("```"):
                lines = json_match.split("\n")
                json_match = "\n".join(lines[1:-1])
            
            data = json.loads(json_match)
            
            result.network = data.get("network")
            result.transaction_type = data.get("transaction_type")
            
            if data.get("amount"):
                try:
                    result.amount = Decimal(str(data["amount"]))
                except:
                    pass
            
            result.customer_phone = data.get("customer_phone")
            result.transaction_ref = data.get("transaction_ref")
            result.sender_name = data.get("sender_name")
            result.timestamp = data.get("timestamp")
            result.confidence = float(data.get("confidence", 0.0))
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            result.confidence = 0.0
        
        return result


# Singleton instance
gemini_service = GeminiService()


def extract_transaction_from_image(image_data: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """
    Convenience function to extract transaction data from image.
    
    Args:
        image_data: Raw image bytes
        mime_type: Image MIME type
        
    Returns:
        Dictionary with extracted transaction data
    """
    result = gemini_service.extract_from_image(image_data, mime_type)
    
    return {
        'network': result.network,
        'transaction_type': result.transaction_type,
        'amount': str(result.amount) if result.amount else None,
        'customer_phone': result.customer_phone,
        'transaction_ref': result.transaction_ref,
        'sender_name': result.sender_name,
        'timestamp': result.timestamp,
        'confidence': result.confidence,
    }
