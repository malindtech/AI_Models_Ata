"""
Simple Data Loader API
Provides clean, client-friendly wrapper for CSV data access
Makes it easy to swap backend (CSV → Excel → JSON → REST API)
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Simple wrapper for loading company data from CSV files"""
    
    def __init__(self, data_dir: str = "data/company"):
        self.data_dir = Path(data_dir)
        self._customers = None
        self._orders = None
        self._products = None
        self._policies = None
        self._support_history = None
    
    def load_customers(self) -> pd.DataFrame:
        """Load customer data"""
        if self._customers is None:
            file_path = self.data_dir / "customers.csv"
            if file_path.exists():
                self._customers = pd.read_csv(file_path)
                logger.info(f"✅ Loaded {len(self._customers)} customers")
            else:
                logger.warning(f"⚠️ customers.csv not found at {file_path}")
                self._customers = pd.DataFrame()
        return self._customers
    
    def load_orders(self) -> pd.DataFrame:
        """Load order data"""
        if self._orders is None:
            file_path = self.data_dir / "orders.csv"
            if file_path.exists():
                self._orders = pd.read_csv(file_path)
                logger.info(f"✅ Loaded {len(self._orders)} orders")
            else:
                logger.warning(f"⚠️ orders.csv not found at {file_path}")
                self._orders = pd.DataFrame()
        return self._orders
    
    def load_products(self) -> pd.DataFrame:
        """Load product data"""
        if self._products is None:
            file_path = self.data_dir / "products.csv"
            if file_path.exists():
                self._products = pd.read_csv(file_path)
                logger.info(f"✅ Loaded {len(self._products)} products")
            else:
                logger.warning(f"⚠️ products.csv not found at {file_path}")
                self._products = pd.DataFrame()
        return self._products
    
    def load_policies(self) -> pd.DataFrame:
        """Load company policy data"""
        if self._policies is None:
            file_path = self.data_dir / "policies.csv"
            if file_path.exists():
                self._policies = pd.read_csv(file_path)
                logger.info(f"✅ Loaded {len(self._policies)} policies")
            else:
                logger.warning(f"⚠️ policies.csv not found at {file_path}")
                self._policies = pd.DataFrame()
        return self._policies
    
    def load_support_history(self) -> pd.DataFrame:
        """Load past support conversation history"""
        if self._support_history is None:
            file_path = self.data_dir / "support_history.csv"
            if file_path.exists():
                self._support_history = pd.read_csv(file_path)
                logger.info(f"✅ Loaded {len(self._support_history)} support tickets")
            else:
                logger.warning(f"⚠️ support_history.csv not found at {file_path}")
                self._support_history = pd.DataFrame()
        return self._support_history
    
    def get_customer_history(self, customer_id: Optional[str] = None, 
                           customer_email: Optional[str] = None) -> Dict:
        """
        Get comprehensive customer history (profile + orders + support tickets)
        
        Args:
            customer_id: Customer ID (e.g., "CUST-001")
            customer_email: Customer email address
        
        Returns:
            Dict with customer profile, order history, and past support tickets
        """
        result = {
            "customer": None,
            "orders": [],
            "support_history": [],
            "found": False
        }
        
        # Load all data
        customers = self.load_customers()
        orders = self.load_orders()
        support_history = self.load_support_history()
        
        # Find customer
        customer_row = None
        if customer_id and not customers.empty:
            customer_row = customers[customers['customer_id'] == customer_id]
        elif customer_email and not customers.empty:
            customer_row = customers[customers['email'].str.lower() == customer_email.lower()]
        
        if customer_row is not None and not customer_row.empty:
            result["found"] = True
            result["customer"] = customer_row.iloc[0].to_dict()
            
            # Get customer identifier for lookups
            cust_id = result["customer"].get("customer_id")
            cust_email = result["customer"].get("email")
            
            # Get orders
            if not orders.empty:
                if cust_id and 'customer_id' in orders.columns:
                    order_matches = orders[orders['customer_id'] == cust_id]
                elif cust_email:
                    order_matches = orders[orders['customer_email'].str.lower() == cust_email.lower()]
                else:
                    order_matches = pd.DataFrame()
                
                if not order_matches.empty:
                    result["orders"] = order_matches.to_dict('records')
            
            # Get support history
            if not support_history.empty:
                if cust_id and 'customer_id' in support_history.columns:
                    ticket_matches = support_history[support_history['customer_id'] == cust_id]
                elif cust_email:
                    ticket_matches = support_history[support_history['customer_email'].str.lower() == cust_email.lower()]
                else:
                    ticket_matches = pd.DataFrame()
                
                if not ticket_matches.empty:
                    result["support_history"] = ticket_matches.to_dict('records')
        
        return result
    
    def reload_all(self):
        """Clear cache and reload all data files"""
        self._customers = None
        self._orders = None
        self._products = None
        self._policies = None
        self._support_history = None
        logger.info("🔄 Data cache cleared, will reload on next access")


# Singleton instance for easy import
_loader = DataLoader()

# Convenience functions for quick access
def load_customers() -> pd.DataFrame:
    """Quick access: Load customer data"""
    return _loader.load_customers()

def load_orders() -> pd.DataFrame:
    """Quick access: Load order data"""
    return _loader.load_orders()

def load_products() -> pd.DataFrame:
    """Quick access: Load product data"""
    return _loader.load_products()

def load_policies() -> pd.DataFrame:
    """Quick access: Load policy data"""
    return _loader.load_policies()

def load_support_history() -> pd.DataFrame:
    """Quick access: Load support history"""
    return _loader.load_support_history()

def get_customer_history(customer_id: Optional[str] = None, 
                        customer_email: Optional[str] = None) -> Dict:
    """Quick access: Get complete customer profile + history"""
    return _loader.get_customer_history(customer_id, customer_email)

def reload_all():
    """Quick access: Reload all data files"""
    _loader.reload_all()


if __name__ == "__main__":
    # Test the data loader
    logging.basicConfig(level=logging.INFO)
    
    print("\n=== Testing Data Loader ===")
    
    print("\n1. Loading customers...")
    customers = load_customers()
    print(f"   Found {len(customers)} customers")
    
    print("\n2. Loading orders...")
    orders = load_orders()
    print(f"   Found {len(orders)} orders")
    
    print("\n3. Loading support history...")
    support = load_support_history()
    print(f"   Found {len(support)} tickets")
    
    print("\n4. Testing customer history lookup...")
    history = get_customer_history(customer_email="john.smith@email.com")
    if history["found"]:
        print(f"   ✅ Found customer: {history['customer']['name']}")
        print(f"   - Orders: {len(history['orders'])}")
        print(f"   - Support tickets: {len(history['support_history'])}")
    else:
        print("   ❌ Customer not found")
    
    print("\n✅ Data loader test complete!")
