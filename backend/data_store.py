"""
Data Store Module - CSV-based data storage with flexible schema mapping
Loads customer, order, product data from CSV files with fuzzy matching support
"""

import os
import pandas as pd
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any
from loguru import logger
from thefuzz import fuzz
from datetime import datetime

class DataStore:
    """
    Flexible CSV-based data store with schema-aware loading
    Supports fuzzy matching for typo-tolerant lookups
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize data store and load CSV files
        
        Args:
            config_path: Path to schema configuration YAML (defaults to config/data_schema.yaml in project root)
        """
        # Default to project root /config/data_schema.yaml
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "data_schema.yaml"
        
        self.config_path = Path(config_path)
        self.project_root = self.config_path.parent.parent  # config/data_schema.yaml -> project root
        self.config = self._load_config()
        self.data = {}
        self.fuzzy_threshold = self.config.get('fuzzy_matching', {}).get('threshold', 80)
        self.fuzzy_enabled = self.config.get('fuzzy_matching', {}).get('enabled', True)
        self.privacy_settings = self.config.get('privacy', {})
        
        # Load all data tables
        self._load_all_tables()
        
        logger.info(f"✅ DataStore initialized with {len(self.data)} tables")
    
    def _load_config(self) -> dict:
        """Load schema configuration from YAML"""
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            return {}
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        logger.debug(f"Loaded config with tables: {list(config.keys())}")
        return config
    
    def _load_all_tables(self):
        """Load all CSV tables defined in config"""
        for table_name, table_config in self.config.items():
            if table_name in ['fuzzy_matching', 'privacy']:
                continue  # Skip non-table config sections
            
            if 'file' not in table_config:
                continue
            
            # Resolve relative paths from project root
            file_path = Path(table_config['file'])
            if not file_path.is_absolute():
                file_path = self.project_root / file_path
            
            if not file_path.exists():
                logger.warning(f"Data file not found: {file_path}, skipping {table_name}")
                continue
            
            try:
                df = pd.read_csv(file_path)
                self.data[table_name] = df
                logger.info(f"✅ Loaded {table_name}: {len(df)} rows, columns: {list(df.columns)}")
            except Exception as e:
                logger.error(f"Failed to load {table_name} from {file_path}: {e}")
    
    def _apply_privacy_mask(self, value: str, field_type: str) -> str:
        """Apply privacy masking to sensitive fields"""
        if not value or pd.isna(value):
            return ""
        
        value = str(value)
        
        if field_type == 'phone' and self.privacy_settings.get('mask_phone', True):
            # Show only last 4 digits: 555-0101 -> ***-0101
            if len(value) >= 4:
                return f"***-{value[-4:]}"
        
        if field_type == 'email' and self.privacy_settings.get('mask_email', False):
            # Show first char and domain: john@email.com -> j***@email.com
            if '@' in value:
                local, domain = value.split('@', 1)
                return f"{local[0]}***@{domain}"
        
        return value
    
    def _fuzzy_match(self, query: str, candidates: List[str], threshold: int = None) -> Optional[str]:
        """
        Find best fuzzy match for query in candidates
        
        Args:
            query: Query string to match
            candidates: List of candidate strings
            threshold: Minimum similarity score (0-100)
        
        Returns:
            Best matching candidate or None
        """
        if not self.fuzzy_enabled:
            return None
        
        threshold = threshold or self.fuzzy_threshold
        query = str(query).strip().upper()
        
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            if pd.isna(candidate):
                continue
            
            candidate_str = str(candidate).strip().upper()
            score = fuzz.ratio(query, candidate_str)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
        
        if best_match:
            logger.debug(f"Fuzzy match: '{query}' -> '{best_match}' (score: {best_score})")
        
        return best_match
    
    def get_order_by_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve order by order number (with fuzzy matching support)
        
        Args:
            order_number: Order number to search for
        
        Returns:
            Order dict or None if not found
        """
        if 'orders' not in self.data:
            logger.warning("Orders table not loaded")
            return None
        
        df = self.data['orders']
        order_number = str(order_number).strip()
        
        # Try exact match first
        matches = df[df['order_id'].str.upper() == order_number.upper()]
        
        if not matches.empty:
            order = matches.iloc[0].to_dict()
            logger.info(f"✅ Found order (exact match): {order_number}")
            return order
        
        # Try fuzzy match
        if self.fuzzy_enabled:
            candidates = df['order_id'].dropna().tolist()
            fuzzy_match = self._fuzzy_match(order_number, candidates)
            
            if fuzzy_match:
                matches = df[df['order_id'] == fuzzy_match]
                if not matches.empty:
                    order = matches.iloc[0].to_dict()
                    logger.info(f"✅ Found order (fuzzy match): {order_number} -> {fuzzy_match}")
                    return order
        
        logger.warning(f"Order not found: {order_number}")
        return None
    
    def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve customer by email address
        
        Args:
            email: Customer email
        
        Returns:
            Customer dict or None if not found
        """
        if 'customers' not in self.data:
            logger.warning("Customers table not loaded")
            return None
        
        df = self.data['customers']
        email = str(email).strip().lower()
        
        matches = df[df['email'].str.lower() == email]
        
        if not matches.empty:
            customer = matches.iloc[0].to_dict()
            # Apply privacy masking
            customer['phone'] = self._apply_privacy_mask(customer.get('phone', ''), 'phone')
            logger.info(f"✅ Found customer: {email}")
            return customer
        
        logger.warning(f"Customer not found: {email}")
        return None
    
    def get_orders_by_email(self, email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve all orders for a customer email
        
        Args:
            email: Customer email
            limit: Maximum number of orders to return
        
        Returns:
            List of order dicts
        """
        if 'orders' not in self.data:
            return []
        
        df = self.data['orders']
        email = str(email).strip().lower()
        
        matches = df[df['customer_email'].str.lower() == email]
        orders = matches.head(limit).to_dict('records')
        
        logger.info(f"✅ Found {len(orders)} orders for {email}")
        return orders
    
    def get_order_history(self, email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Alias for get_orders_by_email"""
        return self.get_orders_by_email(email, limit)
    
    def get_product_by_name(self, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve product by name (fuzzy matching supported)
        
        Args:
            product_name: Product name to search
        
        Returns:
            Product dict or None if not found
        """
        if 'products' not in self.data:
            logger.warning("Products table not loaded")
            return None
        
        df = self.data['products']
        product_name = str(product_name).strip()
        
        # Try exact match (case-insensitive)
        matches = df[df['name'].str.lower() == product_name.lower()]
        
        if not matches.empty:
            product = matches.iloc[0].to_dict()
            logger.info(f"✅ Found product (exact): {product_name}")
            return product
        
        # Try fuzzy match
        if self.fuzzy_enabled:
            candidates = df['name'].dropna().tolist()
            fuzzy_match = self._fuzzy_match(product_name, candidates)
            
            if fuzzy_match:
                matches = df[df['name'] == fuzzy_match]
                if not matches.empty:
                    product = matches.iloc[0].to_dict()
                    logger.info(f"✅ Found product (fuzzy): {product_name} -> {fuzzy_match}")
                    return product
        
        logger.warning(f"Product not found: {product_name}")
        return None
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve product by product ID
        
        Args:
            product_id: Product ID to search
        
        Returns:
            Product dict or None if not found
        """
        if 'products' not in self.data:
            logger.warning("Products table not loaded")
            return None
        
        df = self.data['products']
        product_id = str(product_id).strip()
        
        matches = df[df['product_id'].astype(str).str.strip() == product_id]
        
        if not matches.empty:
            product = matches.iloc[0].to_dict()
            logger.info(f"✅ Found product by ID: {product_id}")
            return product
        
        logger.warning(f"Product not found: {product_id}")
        return None
    
    def format_order_context(self, order: Dict[str, Any]) -> str:
        """
        Format order data into readable context string
        
        Args:
            order: Order dictionary
        
        Returns:
            Formatted order context
        """
        if not order:
            return "No order data available"
        
        # Handle NaN/None values
        def safe_get(key, default="Not available"):
            val = order.get(key)
            if pd.isna(val) or val == '' or val is None:
                return default
            return str(val)
        
        context = f"""ORDER INFORMATION:
- Order Number: {safe_get('order_id')}
- Product: {safe_get('product_name')}
- Order Date: {safe_get('order_date')}
- Status: {safe_get('status').upper()}
- Total Amount: ${safe_get('order_total')}
- Tracking Number: {safe_get('tracking_number', 'Not yet assigned')}
- Carrier: {safe_get('carrier', 'Not yet shipped')}
- Expected Delivery: {safe_get('expected_delivery', 'TBD')}
- Actual Delivery: {safe_get('actual_delivery', 'Not delivered yet')}
"""
        return context.strip()
    
    def format_customer_context(self, customer: Dict[str, Any]) -> str:
        """
        Format customer data into readable context string
        
        Args:
            customer: Customer dictionary
        
        Returns:
            Formatted customer context
        """
        if not customer:
            return "No customer data available"
        
        def safe_get(key, default="Not available"):
            val = customer.get(key)
            if pd.isna(val) or val == '' or val is None:
                return default
            return str(val)
        
        context = f"""CUSTOMER INFORMATION:
- Name: {safe_get('name')}
- Email: {safe_get('email')}
- Phone: {safe_get('phone')}
- Loyalty Tier: {safe_get('loyalty_tier').title()}
- Total Orders: {safe_get('total_orders')}
- Lifetime Value: ${safe_get('total_spent')}
- Member Since: {safe_get('join_date')}
"""
        return context.strip()
    
    def search_orders(self, **filters) -> List[Dict[str, Any]]:
        """
        Search orders with flexible filters
        
        Args:
            **filters: Key-value pairs to filter by (e.g., status='shipped')
        
        Returns:
            List of matching order dicts
        """
        if 'orders' not in self.data:
            return []
        
        df = self.data['orders']
        
        for key, value in filters.items():
            if key in df.columns:
                df = df[df[key] == value]
        
        results = df.to_dict('records')
        logger.info(f"✅ Search found {len(results)} orders with filters: {filters}")
        return results
    
    def get_table_stats(self) -> Dict[str, int]:
        """Get row counts for all loaded tables"""
        return {table: len(df) for table, df in self.data.items()}


# Global singleton instance
_data_store_instance: Optional[DataStore] = None


def get_data_store() -> DataStore:
    """
    Get or create global DataStore instance (singleton pattern)
    
    Returns:
        DataStore instance
    """
    global _data_store_instance
    
    if _data_store_instance is None:
        try:
            _data_store_instance = DataStore()
            logger.info("✅ Global DataStore instance created")
        except Exception as e:
            logger.error(f"Failed to create DataStore: {e}")
            raise
    
    return _data_store_instance


def reload_data_store():
    """Force reload of DataStore (useful for testing or data updates)"""
    global _data_store_instance
    _data_store_instance = None
    return get_data_store()
