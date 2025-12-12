"""
SMS parsing service for Floatly.

Extracts transaction information from mobile money SMS messages
for MTN, Orange Money, and Express Union networks.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    """Represents data extracted from an SMS message."""
    network: Optional[str] = None
    transaction_type: Optional[str] = None  # 'DEPOSIT' or 'WITHDRAWAL'
    amount: Optional[Decimal] = None
    customer_phone: Optional[str] = None
    transaction_ref: Optional[str] = None
    sender_name: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0  # 0-1 confidence score


class SMSParser:
    """
    Parser for mobile money transaction SMS messages.
    Supports MTN Mobile Money, Orange Money, and Express Union.
    """
    
    # Network detection patterns
    NETWORK_PATTERNS = {
        'MTN': [
            r'mtn\s*mobile\s*money',
            r'mtn\s*momo',
            r'mobile\s*money',
            r'momo',
            r'from\s*\d+\s*to\s*\d+',  # MTN format
        ],
        'OM': [
            r'orange\s*money',
            r'om\s*transfer',
            r'orange',
        ],
        'EU': [
            r'express\s*union',
            r'eu\s*mobile',
        ],
    }
    
    # Amount patterns
    AMOUNT_PATTERNS = [
        r'(\d{1,3}(?:[,.\s]\d{3})*(?:[,.]\d{2})?)\s*(?:fcfa|cfa|xaf|f)',  # Amount followed by currency
        r'(?:fcfa|cfa|xaf|f)\s*(\d{1,3}(?:[,.\s]\d{3})*(?:[,.]\d{2})?)',  # Currency followed by amount
        r'montant[:\s]*(\d{1,3}(?:[,.\s]\d{3})*)',  # French "montant"
        r'amount[:\s]*(\d{1,3}(?:[,.\s]\d{3})*)',  # English "amount"
        r'(\d{1,3}(?:[,.\s]\d{3})+)',  # Just a large number with separators
    ]
    
    # Transaction type patterns
    DEPOSIT_PATTERNS = [
        r'vous\s+avez\s+re[çc]u',  # French: you received
        r'you\s+have\s+received',
        r're[çc]u\s+de',  # received from
        r'received\s+from',
        r'cash\s*in',
        r'depot',  # deposit (French)
        r'deposit',
        r'credit',
        r'\+\s*\d',  # Plus sign before amount
    ]
    
    WITHDRAWAL_PATTERNS = [
        r'vous\s+avez\s+envoy[ée]',  # French: you sent
        r'you\s+have\s+sent',
        r'envoy[ée]\s+[àa]',  # sent to
        r'sent\s+to',
        r'cash\s*out',
        r'retrait',  # withdrawal (French)
        r'withdrawal',
        r'debit',
        r'transfer\s+to',
        r'-\s*\d',  # Minus sign before amount
    ]
    
    # Phone number patterns
    PHONE_PATTERNS = [
        r'\+?237\s*(\d{9})',  # Cameroon format
        r'(\d{3}[\s.-]?\d{3}[\s.-]?\d{3})',  # 9 digits with separators
        r'(?:de|from|to|a)\s*(\d{9})',  # After common prepositions
        r'(?:tel|phone)[:\s]*(\d{9,})',  # After tel/phone
    ]
    
    # Transaction reference patterns
    REFERENCE_PATTERNS = [
        r'(?:ref|reference|id|transaction\s*id)[:\s]*([A-Z0-9]{6,})',
        r'(?:txn|tx)[:\s]*([A-Z0-9]{6,})',
        r'#([A-Z0-9]{6,})',
        r'\b([A-Z]{2,}\d{6,})\b',  # Code like MP123456789
    ]
    
    def parse(self, sms_text: str) -> ParsedTransaction:
        """
        Parse SMS text and extract transaction information.
        
        Args:
            sms_text: The raw SMS message text
            
        Returns:
            ParsedTransaction with extracted data
        """
        result = ParsedTransaction(raw_text=sms_text)
        text = sms_text.lower()
        
        # Detect network
        result.network = self._detect_network(text)
        
        # Detect transaction type
        result.transaction_type = self._detect_transaction_type(text)
        
        # Extract amount
        result.amount = self._extract_amount(sms_text)
        
        # Extract phone number
        result.customer_phone = self._extract_phone(sms_text)
        
        # Extract transaction reference
        result.transaction_ref = self._extract_reference(sms_text)
        
        # Calculate confidence
        result.confidence = self._calculate_confidence(result)
        
        return result
    
    def _detect_network(self, text: str) -> Optional[str]:
        """Detect which network the SMS is from."""
        for network, patterns in self.NETWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return network
        return None
    
    def _detect_transaction_type(self, text: str) -> Optional[str]:
        """Detect if this is a deposit or withdrawal."""
        # Check for deposit patterns
        for pattern in self.DEPOSIT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 'DEPOSIT'
        
        # Check for withdrawal patterns
        for pattern in self.WITHDRAWAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 'WITHDRAWAL'
        
        return None
    
    def _extract_amount(self, text: str) -> Optional[Decimal]:
        """Extract the transaction amount."""
        for pattern in self.AMOUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                # Clean up the amount string
                amount_str = re.sub(r'[,\s]', '', amount_str)
                amount_str = amount_str.replace('.', '')
                
                try:
                    amount = Decimal(amount_str)
                    # Filter out unrealistic amounts
                    if 100 <= amount <= 10000000:
                        return amount
                except (InvalidOperation, ValueError):
                    continue
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract customer phone number."""
        for pattern in self.PHONE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phone = match.group(1)
                # Clean up phone
                phone = re.sub(r'[\s.-]', '', phone)
                if len(phone) >= 9:
                    return phone
        
        return None
    
    def _extract_reference(self, text: str) -> Optional[str]:
        """Extract transaction reference/ID."""
        for pattern in self.REFERENCE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _calculate_confidence(self, result: ParsedTransaction) -> float:
        """
        Calculate a confidence score based on how much data was extracted.
        """
        score = 0.0
        
        if result.network:
            score += 0.2
        if result.transaction_type:
            score += 0.3
        if result.amount:
            score += 0.3
        if result.customer_phone:
            score += 0.1
        if result.transaction_ref:
            score += 0.1
        
        return min(1.0, score)


# Singleton instance
sms_parser = SMSParser()


def parse_sms(text: str) -> Dict[str, Any]:
    """
    Convenience function to parse SMS and return dict.
    
    Args:
        text: SMS message text
        
    Returns:
        Dictionary with extracted transaction data
    """
    result = sms_parser.parse(text)
    
    return {
        'network': result.network,
        'transaction_type': result.transaction_type,
        'amount': str(result.amount) if result.amount else None,
        'customer_phone': result.customer_phone,
        'transaction_ref': result.transaction_ref,
        'raw_text': result.raw_text,
        'confidence': result.confidence,
    }
