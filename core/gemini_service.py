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
    customer_name: Optional[str] = None
    transaction_ref: Optional[str] = None
    timestamp: Optional[str] = None
    confidence: float = 0.0
    raw_response: str = ""


class GeminiService:
    """
    Service for interacting with Google Gemini API for image analysis.
    """
    
    MODEL = "gemini-2.5-flash-lite"
    
    EXTRACTION_PROMPT = """You are REEPLS AI, specialized in extracting data from Cameroon mobile money transaction receipts.

Analyze this receipt image and extract transaction information in JSON format:

{
    "network": "MTN" or "OM" (Orange Money) or "EU" (Express Union) or null,
    "transaction_type": "DEPOSIT" (cash in/received money) or "WITHDRAWAL" (cash out/sent money) or null,
    "amount": number (in CFA, without currency symbol),
    "customer_phone": "phone number" or null,
    "customer_name": "customer/sender/recipient name" or null,
    "transaction_ref": "transaction ID/reference number" or null,
    "timestamp": "transaction date/time in ISO format" or null,
    "confidence": 0.0 to 1.0 (your confidence in the extraction)
}

NETWORK DETECTION RULES (Cameroon):
- MTN: Phone starts with 67, 650-654, 680-681 (e.g., 670xxxxxx, 651xxxxxx)
- Orange (OM): Phone starts with 69, 655-659 (e.g., 690xxxxxx, 656xxxxxx)
- If receipt shows MTN logo/colors (yellow) → "MTN"
- If receipt shows Orange logo/colors (orange) → "OM"

TRANSACTION TYPE RULES:
- "DEPOSIT" = Customer sent money TO the kiosk (cash in, received)
- "WITHDRAWAL" = Customer took cash FROM the kiosk (cash out, sent, transfer)
- Look for keywords: "Reçu", "Envoyé", "Retrait", "Dépôt", "Cash In", "Cash Out"

IMPORTANT:
- Amount should be the main transaction value (number only, no "CFA" or "FCFA")
- customer_name is the sender OR recipient name shown on receipt
- transaction_ref is the unique transaction ID (often starts with letters/numbers mix)
- Return ONLY valid JSON, no markdown or extra text

If you cannot extract a field, set it to null."""

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
        print(f"DEBUG: Gemini API Key present: {bool(self.api_key)}")
        if self.api_key:
            print(f"DEBUG: API Key length: {len(self.api_key)}")
            print(f"DEBUG: API Key prefix: {self.api_key[:4]}...")

        if not self.api_key:
            logger.warning("GOOGLE_GEMINI_API_KEY not set, returning empty result")
            print("DEBUG: GOOGLE_GEMINI_API_KEY is missing!")
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
            
            print(f"DEBUG: Sending request to Gemini API... URL: {self.api_url}")
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"DEBUG: Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                print(f"DEBUG: API Error Body: {response.text}")
                return ExtractedTransactionData(
                    raw_response=f"API error: {response.status_code}"
                )
            
            # Parse response
            result = response.json()
            # print(f"DEBUG: Full API Response: {json.dumps(result, indent=2)}")
            
            text_content = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            print(f"DEBUG: Extracted text content: {text_content}")
            
            return self._parse_ai_response(text_content)
            
        except Exception as e:
            logger.exception(f"Error calling Gemini API: {e}")
            print(f"DEBUG: Exception during API call: {e}")
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
                # Handle cases where language identifier is present or not
                if lines[0].strip().startswith("```"):
                    # Remove first and last lines
                    json_match = "\n".join(lines[1:-1])
            
            print(f"DEBUG: JSON to parse: {json_match}")
            data = json.loads(json_match)
            
            result.network = data.get("network")
            result.transaction_type = data.get("transaction_type")
            
            if data.get("amount"):
                try:
                    result.amount = Decimal(str(data["amount"]))
                except:
                    pass
            
            result.customer_phone = data.get("customer_phone")
            result.customer_name = data.get("customer_name")
            result.transaction_ref = data.get("transaction_ref")
            result.timestamp = data.get("timestamp")
            result.confidence = float(data.get("confidence", 0.0))
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            print(f"DEBUG: JSON Parse Error: {e}")
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
        'customer_name': result.customer_name,
        'transaction_ref': result.transaction_ref,
        'timestamp': result.timestamp,
        'confidence': result.confidence,
    }
