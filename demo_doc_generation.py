#!/usr/bin/env python3
"""
Demonstration of RegionAI's Documentation Generation capabilities.

This script shows how the system can generate human-readable summaries
of functions based on its semantic understanding.
"""
from src.regionai.pipeline.api import generate_docs_for_function

# Example code with various functions
code = '''
def get_customer_order_history(customer_id, start_date=None, end_date=None):
    """
    Retrieves the complete order history for a customer.
    
    This function fetches all orders placed by a customer within
    the specified date range. It includes order details, items,
    and payment information.
    """
    orders = db.query(Order).filter(
        Order.customer_id == customer_id
    )
    
    if start_date:
        orders = orders.filter(Order.created_at >= start_date)
    if end_date:
        orders = orders.filter(Order.created_at <= end_date)
    
    return orders.all()

def calculate_customer_lifetime_value(customer_id):
    """
    Calculates the total lifetime value of a customer.
    
    This aggregates all purchases made by the customer and
    applies predictive modeling to estimate future value.
    """
    # Get all customer orders
    orders = get_customer_order_history(customer_id)
    
    # Calculate total spent
    total_spent = sum(order.total for order in orders)
    
    # Apply predictive model for future value
    predicted_value = ml_model.predict_future_value(customer_id, orders)
    
    return {
        'historical_value': total_spent,
        'predicted_value': predicted_value,
        'lifetime_value': total_spent + predicted_value
    }

def update_product_inventory(product_id, quantity_change):
    """
    Updates the inventory count for a product.
    
    This function handles both increases (restocking) and
    decreases (sales) in inventory. It ensures inventory
    never goes negative and triggers reorder alerts when
    stock is low.
    """
    product = get_product(product_id)
    
    new_quantity = product.inventory_count + quantity_change
    
    if new_quantity < 0:
        raise ValueError("Insufficient inventory")
    
    product.inventory_count = new_quantity
    
    if new_quantity < product.reorder_threshold:
        trigger_reorder_alert(product)
    
    save_product(product)
    return product
'''

print("RegionAI Documentation Generation Demo")
print("=" * 60)

# Generate documentation for each function
functions = [
    'get_customer_order_history',
    'calculate_customer_lifetime_value',
    'update_product_inventory'
]

for func_name in functions:
    print(f"\nFunction: {func_name}")
    print("-" * 40)
    
    summary = generate_docs_for_function(func_name, code)
    print(summary)

print("\n" + "=" * 60)
print("Demo complete!")