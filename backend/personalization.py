# backend/personalization.py
"""
Day 6: Personalization Engine

Replaces personalization tokens in generated content with actual values:
- {customer_name}, {company}, {product}, etc.
- Context-aware replacement with validation
- Fallback handling for missing values
- Production-level error handling

Usage:
    personalizer = Personalizer(context={"customer_name": "John", "company": "Acme"})
    personalized = personalizer.personalize(content)
"""

from typing import Dict, Optional, List, Set
from loguru import logger
import re


# Default fallback values for common tokens
DEFAULT_FALLBACKS = {
    "customer_name": "Valued Customer",
    "company": "our company",
    "product": "our product",
    "order_number": "[Order Number]",
    "email": "[Email Address]",
    "phone": "[Phone Number]",
    "date": "[Date]",
    "time": "[Time]",
    "price": "[Price]",
    "quantity": "[Quantity]",
    "tracking_number": "[Tracking Number]",
    "support_agent": "Support Team",
    "brand_name": "our brand",
}


class Personalizer:
    """
    Production-grade personalization engine for content
    """
    
    def __init__(
        self,
        context: Optional[Dict[str, str]] = None,
        fallbacks: Optional[Dict[str, str]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize personalizer
        
        Args:
            context: Dictionary of token values (e.g., {"customer_name": "John"})
            fallbacks: Custom fallback values (merges with defaults)
            strict_mode: If True, raise error on missing tokens without fallbacks
        """
        self.context = context or {}
        self.fallbacks = {**DEFAULT_FALLBACKS, **(fallbacks or {})}
        self.strict_mode = strict_mode
        self._token_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
        
        logger.debug(f"Personalizer initialized with {len(self.context)} context values")
    
    def personalize(self, content: str, additional_context: Optional[Dict[str, str]] = None) -> str:
        """
        Replace personalization tokens in content
        
        Args:
            content: Content with tokens like {customer_name}
            additional_context: Additional context to merge (temporary)
        
        Returns:
            Personalized content with tokens replaced
        
        Raises:
            ValueError: If strict_mode=True and required token is missing
        """
        if not content:
            return content
        
        # Merge contexts (additional_context takes priority)
        merged_context = {**self.context, **(additional_context or {})}
        
        # Find all tokens in content
        tokens = self._token_pattern.findall(content)
        
        if not tokens:
            logger.debug("No personalization tokens found in content")
            return content
        
        # Track replacements
        replacements_made = {}
        missing_tokens = []
        
        # Replace each token
        personalized = content
        for token in set(tokens):  # Deduplicate
            value = self._get_token_value(token, merged_context)
            
            if value is None:
                missing_tokens.append(token)
                if self.strict_mode:
                    raise ValueError(f"Missing required personalization token: {token}")
                # In non-strict mode, leave token as-is
                logger.warning(f"No value found for token '{token}' - leaving unchanged")
            else:
                personalized = personalized.replace(f"{{{token}}}", value)
                replacements_made[token] = value
        
        # Log results
        if replacements_made:
            logger.info(f"Personalized content: {len(replacements_made)} tokens replaced")
            logger.debug(f"Replacements: {list(replacements_made.keys())}")
        
        if missing_tokens:
            logger.warning(f"Missing tokens: {missing_tokens}")
        
        return personalized
    
    def _get_token_value(self, token: str, context: Dict[str, str]) -> Optional[str]:
        """
        Get value for a token from context or fallbacks
        
        Args:
            token: Token name (without braces)
            context: Context dictionary
        
        Returns:
            Token value or None if not found
        """
        # Priority: context > fallbacks
        if token in context:
            return str(context[token])
        elif token in self.fallbacks:
            logger.debug(f"Using fallback for token '{token}': {self.fallbacks[token]}")
            return self.fallbacks[token]
        else:
            return None
    
    def extract_tokens(self, content: str) -> List[str]:
        """
        Extract all tokens from content
        
        Args:
            content: Content to analyze
        
        Returns:
            List of unique token names (without braces)
        """
        tokens = self._token_pattern.findall(content)
        return list(set(tokens))
    
    def validate_tokens(self, content: str) -> Dict[str, bool]:
        """
        Check which tokens in content can be replaced
        
        Args:
            content: Content to validate
        
        Returns:
            Dict mapping token names to availability (True if can replace)
        """
        tokens = self.extract_tokens(content)
        validation = {}
        
        for token in tokens:
            has_value = (
                token in self.context or 
                token in self.fallbacks
            )
            validation[token] = has_value
        
        return validation
    
    def get_missing_tokens(self, content: str) -> List[str]:
        """
        Get list of tokens that cannot be replaced
        
        Args:
            content: Content to check
        
        Returns:
            List of token names without values
        """
        validation = self.validate_tokens(content)
        return [token for token, has_value in validation.items() if not has_value]
    
    def update_context(self, new_context: Dict[str, str]):
        """
        Update personalization context
        
        Args:
            new_context: New context values to merge
        """
        self.context.update(new_context)
        logger.debug(f"Context updated: now has {len(self.context)} values")
    
    def clear_context(self):
        """Clear all context values"""
        self.context.clear()
        logger.debug("Personalization context cleared")
    
    def get_context_summary(self) -> Dict[str, any]:
        """
        Get summary of personalization state
        
        Returns:
            Dict with context info
        """
        return {
            "context_keys": list(self.context.keys()),
            "context_count": len(self.context),
            "fallback_keys": list(self.fallbacks.keys()),
            "strict_mode": self.strict_mode
        }


def personalize_content(
    content: str,
    context: Dict[str, str],
    strict: bool = False
) -> str:
    """
    Simple function-based personalization (stateless)
    
    Args:
        content: Content with tokens
        context: Token values
        strict: Raise error on missing tokens
    
    Returns:
        Personalized content
    """
    personalizer = Personalizer(context=context, strict_mode=strict)
    return personalizer.personalize(content)


def extract_customer_context(text: str) -> Dict[str, str]:
    """
    Extract potential personalization context from text
    
    Uses regex patterns to find:
    - Names (capitalized words after "Mr.", "Ms.", "Dear", etc.)
    - Order numbers (ORDER-XXX, #12345, etc.)
    - Email addresses
    - Phone numbers
    
    Args:
        text: Text to analyze
    
    Returns:
        Dict with extracted values
    """
    context = {}
    
    # Extract names (after salutations)
    name_patterns = [
        r'(?:Dear|Hello|Hi)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            context['customer_name'] = match.group(1)
            break
    
    # Extract order numbers
    order_patterns = [
        r'(?:order|ORDER)\s*[#:-]?\s*([A-Z0-9]{5,})',
        r'#([0-9]{5,})',
    ]
    for pattern in order_patterns:
        match = re.search(pattern, text)
        if match:
            context['order_number'] = match.group(1)
            break
    
    # Extract email
    email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
    email_match = re.search(email_pattern, text)
    if email_match:
        context['email'] = email_match.group(1)
    
    # Extract phone (simple pattern)
    phone_pattern = r'\b(\+?[0-9]{1,3}[-.\s]?)?(\([0-9]{3}\)|[0-9]{3})[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
    phone_match = re.search(phone_pattern, text)
    if phone_match:
        context['phone'] = phone_match.group(0)
    
    if context:
        logger.debug(f"Extracted context: {list(context.keys())}")
    
    return context


# Global personalizer instance for reuse
_global_personalizer: Optional[Personalizer] = None


def get_global_personalizer() -> Personalizer:
    """
    Get or create global personalizer instance
    
    Returns:
        Personalizer: Global instance with default config
    """
    global _global_personalizer
    
    if _global_personalizer is None:
        _global_personalizer = Personalizer()
        logger.info("Global Personalizer initialized")
    
    return _global_personalizer


def reset_global_personalizer():
    """Reset global personalizer (for testing)"""
    global _global_personalizer
    _global_personalizer = None
    logger.debug("Global personalizer reset")
