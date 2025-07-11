#!/usr/bin/env python3
"""
Demonstration of RegionAI's Behavioral Summary Generation.

This script shows how the system can describe not just what concepts
exist in code, but what actions those concepts perform - explaining
the behavior and dynamics of the software.
"""
from src.regionai.knowledge import (
    KnowledgeGraph, BayesianUpdater, ActionDiscoverer
)
from src.regionai.language import DocumentationGenerator
from src.regionai.pipeline.api import (
    generate_docs_for_function,
    generate_behavioral_docs_for_function
)

# Example code with rich behaviors
code = '''
class OrderProcessor:
    """Handles order processing workflow."""
    
    def process_customer_order(self, customer_id, order_details):
        """Process a customer's order through the entire workflow."""
        # Validate and load customer
        customer = self.customer_service.load(customer_id)
        if not customer.validate():
            raise ValueError("Invalid customer")
        
        # Create and validate order
        order = Order(customer_id, order_details)
        order.calculate_totals()
        order.validate_items()
        
        # Check inventory
        for item in order.items:
            if not self.inventory.check(item.product_id, item.quantity):
                raise OutOfStockError(item.product_id)
            self.inventory.reserve(item.product_id, item.quantity)
        
        # Process payment
        payment = self.payment_service.process(
            customer.payment_method,
            order.total
        )
        
        if payment.success:
            # Finalize order
            order.confirm()
            self.db.save(order)
            
            # Update inventory
            for item in order.items:
                self.inventory.decrease(item.product_id, item.quantity)
            
            # Send notifications
            self.notification_service.send(customer.email, "order_confirmed", order)
            
            # Update analytics
            self.analytics.track("order_completed", {
                "customer_id": customer_id,
                "order_value": order.total,
                "item_count": len(order.items)
            })
        else:
            # Rollback inventory reservation
            for item in order.items:
                self.inventory.release(item.product_id, item.quantity)
            
            raise PaymentFailedError(payment.error)
        
        return order
    
    def update_order_status(self, order_id, new_status):
        """Update the status of an existing order."""
        order = self.db.load(Order, order_id)
        order.update_status(new_status)
        
        # Log status change
        self.logger.info(f"Order {order_id} status changed to {new_status}")
        
        # Notify customer
        customer = self.customer_service.load(order.customer_id)
        self.notification_service.send(
            customer.email,
            "status_update",
            {"order_id": order_id, "status": new_status}
        )
        
        self.db.save(order)
        
    def cancel_order(self, order_id, reason):
        """Cancel an order and handle all cleanup."""
        order = self.db.load(Order, order_id)
        
        if order.status == "shipped":
            raise CannotCancelError("Order already shipped")
        
        # Restore inventory
        for item in order.items:
            self.inventory.increase(item.product_id, item.quantity)
        
        # Process refund
        if order.payment_id:
            self.payment_service.refund(order.payment_id, order.total)
        
        # Update order
        order.cancel(reason)
        self.db.save(order)
        
        # Notify stakeholders
        customer = self.customer_service.load(order.customer_id)
        self.notification_service.send(customer.email, "order_cancelled", order)
        
        # Update analytics
        self.analytics.track("order_cancelled", {
            "order_id": order_id,
            "reason": reason
        })
'''

print("RegionAI Behavioral Summary Demo")
print("=" * 60)

# Build knowledge graph and discover actions manually for demonstration
print("\nBuilding knowledge graph with action discovery...")
kg = KnowledgeGraph()
updater = BayesianUpdater(kg)
discoverer = ActionDiscoverer()

# Analyze each function
functions = [
    ("process_customer_order", code.split("def process_customer_order")[1].split("def ")[0]),
    ("update_order_status", code.split("def update_order_status")[1].split("def ")[0]),
    ("cancel_order", code.split("def cancel_order")[1].split("def ")[0])
]

# Discover actions for each function
all_actions = []
for func_name, func_code in functions:
    full_code = f"def {func_name}{func_code}"
    actions = discoverer.discover_actions(full_code, func_name)
    
    for action in actions:
        # Update the knowledge graph
        updater.update_concept_belief(action.concept.title(), 'function_analysis', 0.8)
        updater.update_action_belief(
            action.concept.title(),
            action.verb,
            'method_call' if '.' in action.method_name else 'function_name',
            action.confidence
        )
        all_actions.append((func_name, action))

# Create documentation generator
doc_gen = DocumentationGenerator(kg)

print(f"\nDiscovered {len(all_actions)} total actions across functions")
print(f"Knowledge graph contains {len(kg.get_concepts())} concepts")

# Generate both types of summaries for comparison
print("\n" + "=" * 60)
print("Comparing Summary Types")
print("=" * 60)

for func_name, _ in functions:
    print(f"\nFunction: {func_name}")
    print("-" * 40)
    
    # Traditional concept summary
    traditional = doc_gen.generate_summary(func_name)
    print(f"Traditional: {traditional}")
    
    # Behavioral summary
    behavioral = doc_gen.generate_behavioral_summary(func_name)
    print(f"Behavioral:  {behavioral}")

# Show detailed action analysis
print("\n" + "=" * 60)
print("Detailed Action Analysis")
print("=" * 60)

# Group actions by concept
from collections import defaultdict
concept_actions = defaultdict(set)
for _, action in all_actions:
    concept_actions[action.concept.title()].add(action.verb)

# Show top concepts and their actions
top_concepts = sorted(
    concept_actions.items(),
    key=lambda x: len(x[1]),
    reverse=True
)[:5]

print("\nTop concepts by number of distinct actions:")
for concept, verbs in top_concepts:
    print(f"\n{concept}:")
    for verb in sorted(verbs):
        # Get confidence for this action
        rels = kg.get_relations_with_confidence(concept)
        perf_rel = next((r for r in rels 
                        if str(r['relation']) == "PERFORMS" and 
                        str(r['target']).lower() == verb), None)
        if perf_rel:
            print(f"  - {verb} (confidence: {perf_rel['confidence']:.3f})")

# Test the API endpoints
print("\n" + "=" * 60)
print("API Endpoint Comparison")
print("=" * 60)

test_func = "process_customer_order"
print(f"\nUsing API for: {test_func}")
print("-" * 40)

# Traditional API
traditional_api = generate_docs_for_function(test_func, code)
print(f"Traditional API: {traditional_api}")

# Behavioral API
behavioral_api = generate_behavioral_docs_for_function(test_func, code)
print(f"Behavioral API:  {behavioral_api}")

print("\n" + "=" * 60)
print("Demo complete! RegionAI can now describe both:")
print("- WHAT code is about (concepts)")
print("- HOW code behaves (actions)")
print("This enables true functional understanding of software.")
print("=" * 60)