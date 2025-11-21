"""
Data Retrieval Module - Unified context orchestration
Combines structured data (orders, customers) with unstructured knowledge (policies)
Provides grounded context for LLM generation
"""

from typing import Dict, List, Optional, Any
from loguru import logger

try:
    from backend.data_store import get_data_store
    from backend.knowledge_base import get_knowledge_base
    DATA_GROUNDING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Data grounding modules not available: {e}")
    DATA_GROUNDING_AVAILABLE = False


def initialize() -> None:
    """
    Initialize data grounding modules (data store and knowledge base).
    Triggers singleton creation for both modules.
    Should be called once at application startup.
    
    Raises:
        Exception if initialization fails
    """
    if not DATA_GROUNDING_AVAILABLE:
        logger.warning("Data grounding modules not available")
        return
    
    try:
        # Initialize data store singleton
        data_store = get_data_store()
        logger.info("✅ DataStore initialized successfully")
        
        # Initialize knowledge base singleton (may fail due to vector DB)
        try:
            kb = get_knowledge_base()
            logger.info("✅ KnowledgeBase initialized successfully")
        except Exception as kb_error:
            logger.warning(f"⚠️ KnowledgeBase initialization failed: {kb_error}")
            logger.info("Continuing without policy vector search (keyword search will be used)")
        
    except Exception as e:
        logger.error(f"Data grounding initialization failed: {e}")
        # Don't raise - allow server to start without data grounding
        logger.warning("Support agent will work without database grounding")


class DataRetrieval:
    """
    Orchestrates retrieval of structured data and knowledge base content
    Provides unified context for LLM prompt injection
    """
    
    def __init__(self):
        """Initialize data retrieval with data store and knowledge base"""
        self.data_store = None
        self.knowledge_base = None
        
        if DATA_GROUNDING_AVAILABLE:
            try:
                self.data_store = get_data_store()
                logger.info("✅ DataStore connected")
            except Exception as e:
                logger.error(f"Failed to initialize DataStore: {e}")
            
            try:
                self.knowledge_base = get_knowledge_base()
                logger.info("✅ KnowledgeBase connected")
            except Exception as e:
                logger.error(f"Failed to initialize KnowledgeBase: {e}")
    
    def get_grounded_context(
        self,
        message: str,
        extracted_info: Dict[str, str],
        intent: str,
        conversation_history: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all relevant context (data + policies) for a message
        
        Args:
            message: Current customer message
            extracted_info: Extracted identifiers (order_number, email, etc.)
            intent: Detected intent (complaint, inquiry, request)
            conversation_history: Optional conversation history
        
        Returns:
            Dict with 'context_text', 'has_data', 'data_sources'
        """
        context_parts = []
        data_sources = []
        has_order_data = False
        has_customer_data = False
        has_policies = False
        
        # 1. Try to retrieve order data
        order_number = extracted_info.get('order_number')
        if order_number and self.data_store:
            order = self.data_store.get_order_by_number(order_number)
            if order:
                order_context = self.data_store.format_order_context(order)
                context_parts.append(order_context)
                data_sources.append(f"Order {order_number}")
                has_order_data = True
                logger.info(f"✅ Retrieved order data: {order_number}")
        
        # 2. Try to retrieve customer data
        email = extracted_info.get('email')
        if email and self.data_store:
            customer = self.data_store.get_customer_by_email(email)
            if customer:
                customer_context = self.data_store.format_customer_context(customer)
                context_parts.append(customer_context)
                data_sources.append(f"Customer {email}")
                has_customer_data = True
                logger.info(f"✅ Retrieved customer data: {email}")
                
                # Also get customer's order history if we don't have specific order
                if not has_order_data:
                    orders = self.data_store.get_orders_by_email(email, limit=3)
                    if orders:
                        context_parts.append(f"\nRECENT ORDERS FOR THIS CUSTOMER:")
                        for order in orders:
                            context_parts.append(
                                f"- {order.get('order_id')}: {order.get('product_name')} "
                                f"({order.get('status')}) - {order.get('order_date')}"
                            )
                        data_sources.append(f"{len(orders)} recent orders")
        
        # 3. Retrieve relevant policies based on intent and message
        if self.knowledge_base:
            # Map intent to policy types
            intent_policy_map = {
                'complaint': ['returns', 'refund', 'damaged', 'warranty'],
                'request': ['returns', 'cancellation', 'refund'],
                'inquiry': ['shipping', 'tracking', 'payment', 'warranty']
            }
            
            # Try to get relevant policies via semantic search
            policies = self.knowledge_base.get_relevant_policies(
                query=message,
                k=2  # Get top 2 most relevant policies
            )
            
            # If no policies found via semantic search, try intent-based lookup
            if not policies and intent in intent_policy_map:
                for policy_type in intent_policy_map[intent]:
                    policy_list = self.knowledge_base.get_policy_by_type(policy_type)
                    if policy_list:
                        policies.extend(policy_list[:1])  # Add first policy of each type
                        if len(policies) >= 2:
                            break
            
            if policies:
                policy_context = self.knowledge_base.format_policy_context(policies)
                context_parts.append("\n" + policy_context)
                data_sources.extend([f"{p['policy_type']} policy" for p in policies])
                has_policies = True
                logger.info(f"✅ Retrieved {len(policies)} relevant policies")
        
        # 4. Build final context
        if not context_parts:
            # No data found
            return {
                'context_text': self._get_no_data_message(extracted_info),
                'has_data': False,
                'has_order_data': False,
                'has_customer_data': False,
                'has_policies': False,
                'data_sources': [],
                'order_data': None,
                'customer_data': None
            }
        
        # Combine all context with clear section headers
        full_context = "\n\n".join(context_parts)
        
        return {
            'context_text': full_context,
            'has_data': True,
            'has_order_data': has_order_data,
            'has_customer_data': has_customer_data,
            'has_policies': has_policies,
            'data_sources': data_sources,
            'order_data': order if has_order_data else None,
            'customer_data': customer if has_customer_data else None
        }
    
    def _get_no_data_message(self, extracted_info: Dict[str, str]) -> str:
        """Generate helpful message when no data is found"""
        order_number = extracted_info.get('order_number')
        email = extracted_info.get('email')
        
        if order_number:
            return f"""DATA LOOKUP RESULT:
❌ Order {order_number} not found in database.

INSTRUCTIONS FOR AGENT:
- Inform customer: "I'm unable to locate order {order_number} in our system."
- Ask customer to verify the order number (format should be like ORD-12345)
- Alternatively, ask for the email address used to place the order
- Offer to search by other identifiers (order date, product name)
- DO NOT make up order details or delivery dates
"""
        elif email:
            return f"""DATA LOOKUP RESULT:
❌ No orders found for email {email} in database.

INSTRUCTIONS FOR AGENT:
- Inform customer: "I don't see any orders associated with {email}."
- Ask if they used a different email address
- Verify the email spelling
- DO NOT make up order information
"""
        else:
            return """DATA LOOKUP RESULT:
❌ No order number or email provided.

INSTRUCTIONS FOR AGENT:
- Ask customer for their order number (format: ORD-12345) or email address
- Explain: "To help you with your order, I'll need either your order number or the email you used to place the order."
- DO NOT make up or assume order details
"""
    
    def validate_response_against_data(
        self, 
        response: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate LLM response against retrieved data to detect hallucinations
        
        Args:
            response: Generated LLM response
            context: Retrieved context from get_grounded_context()
        
        Returns:
            Validation result dict with 'is_valid', 'warnings', 'errors'
        """
        warnings = []
        errors = []
        
        # Skip validation if no data was retrieved
        if not context.get('has_data'):
            return {
                'is_valid': True,
                'warnings': [],
                'errors': []
            }
        
        order_data = context.get('order_data')
        
        # Check for hallucinated dates
        import re
        date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b'
        dates_in_response = re.findall(date_pattern, response, re.IGNORECASE)
        
        if dates_in_response and order_data:
            # Check if dates in response match data
            valid_dates = [
                str(order_data.get('order_date', '')),
                str(order_data.get('expected_delivery', '')),
                str(order_data.get('actual_delivery', ''))
            ]
            
            for date in dates_in_response:
                # Simple check: if date mentioned but not in valid dates
                if not any(date.lower() in vd.lower() for vd in valid_dates if vd):
                    warnings.append(f"Response mentions date '{date}' not found in order data")
        
        # Check for hallucinated tracking numbers
        tracking_pattern = r'\b[A-Z]{3}\d{10,}\b'
        tracking_in_response = re.findall(tracking_pattern, response)
        
        if tracking_in_response and order_data:
            valid_tracking = str(order_data.get('tracking_number', ''))
            for tracking in tracking_in_response:
                if valid_tracking and tracking != valid_tracking:
                    errors.append(f"Response mentions tracking '{tracking}' but actual tracking is '{valid_tracking}'")
        
        # Check for hallucinated order status claims
        status_claims = [
            'has been delivered', 'was delivered', 'delivered on',
            'has shipped', 'was shipped', 'shipped on',
            'is being processed', 'being processed'
        ]
        
        if order_data:
            actual_status = str(order_data.get('status', '')).lower()
            for claim in status_claims:
                if claim in response.lower():
                    # Check if claim matches actual status
                    if 'delivered' in claim and actual_status != 'delivered':
                        errors.append(f"Response claims delivery but order status is '{actual_status}'")
                    elif 'shipped' in claim and actual_status not in ['shipped', 'delivered']:
                        errors.append(f"Response claims shipped but order status is '{actual_status}'")
        
        # Check if response says "I checked" or "I've located" when data wasn't found
        if not context.get('has_order_data'):
            checked_phrases = [
                "i've checked", "i checked", "i've located", "i located",
                "i've found", "i found", "i see that", "i can see"
            ]
            if any(phrase in response.lower() for phrase in checked_phrases):
                errors.append("Response claims to have found data but no data was retrieved")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"❌ Response validation failed: {errors}")
        elif warnings:
            logger.warning(f"⚠️ Response validation warnings: {warnings}")
        
        return {
            'is_valid': is_valid,
            'warnings': warnings,
            'errors': errors
        }


# Global singleton instance
_data_retrieval_instance: Optional[DataRetrieval] = None


def get_data_retrieval() -> DataRetrieval:
    """
    Get or create global DataRetrieval instance (singleton pattern)
    
    Returns:
        DataRetrieval instance
    """
    global _data_retrieval_instance
    
    if _data_retrieval_instance is None:
        try:
            _data_retrieval_instance = DataRetrieval()
            logger.info("✅ Global DataRetrieval instance created")
        except Exception as e:
            logger.error(f"Failed to create DataRetrieval: {e}")
            # Return a dummy instance that returns empty context
            _data_retrieval_instance = DataRetrieval()
    
    return _data_retrieval_instance
