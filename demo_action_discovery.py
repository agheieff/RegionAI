#!/usr/bin/env python3
"""
Demonstration of RegionAI's Action Discovery capabilities.

This script shows how the system can identify not just what concepts exist,
but what actions are performed on them - understanding behavior, not just structure.
"""
from src.regionai.pipeline.api import build_knowledge_graph, analyze_code
from src.regionai.knowledge.linker import KnowledgeLinker

# Example code with rich behavior
code = '''
class CustomerService:
    """Service for managing customer operations."""
    
    def create_customer(self, name, email):
        """Create a new customer account."""
        # Validate input data
        if not self.validate_email(email):
            raise ValueError("Invalid email address")
        
        # Create customer object
        customer = Customer(name=name, email=email)
        customer.generate_id()
        
        # Save to database
        self.db.save(customer)
        
        # Send welcome email
        self.email_service.send_welcome(customer)
        
        # Log the creation
        self.logger.info(f"Created customer: {customer.id}")
        
        return customer
    
    def update_customer_preferences(self, customer_id, preferences):
        """Update customer preferences."""
        customer = self.db.load(Customer, customer_id)
        customer.update_preferences(preferences)
        customer.validate()
        self.db.save(customer)
        
        # Notify customer of changes
        self.notification_service.notify(customer, "preferences_updated")
    
    def delete_customer(self, customer_id):
        """Delete a customer and all associated data."""
        customer = self.db.load(Customer, customer_id)
        
        # Archive data before deletion
        self.archive_service.archive(customer)
        
        # Delete from all systems
        self.db.delete(customer)
        self.cache.remove(customer_id)
        self.search_index.remove(customer_id)
        
        self.logger.info(f"Deleted customer: {customer_id}")
    
    def calculate_customer_value(self, customer_id):
        """Calculate the lifetime value of a customer."""
        customer = self.db.load(Customer, customer_id)
        orders = self.order_service.get_orders(customer_id)
        
        total_value = 0
        for order in orders:
            total_value += order.calculate_total()
        
        # Apply predictive modeling
        predicted_value = self.ml_model.predict(customer, orders)
        
        return {
            'historical': total_value,
            'predicted': predicted_value,
            'total': total_value + predicted_value
        }
'''

print("RegionAI Action Discovery Demo")
print("=" * 60)

# Analyze the code
print("\nAnalyzing code to discover concepts and actions...")
result = analyze_code(code, include_source=True)

# Build knowledge graph with action discovery
print("\nBuilding knowledge graph with behavior understanding...")
kg = build_knowledge_graph(code, include_source=True, enrich_from_docs=True)

# Create a linker to access discovered actions
linker = KnowledgeLinker(result.semantic_db, kg)

# Process the code to discover actions
for entry in result.semantic_db:
    if hasattr(entry, 'documented_fingerprint') and entry.documented_fingerprint:
        linker._process_documentation(entry)

# Get discovered actions
actions = linker.get_discovered_actions()

print(f"\nDiscovered {len(actions)} actions:")
print("-" * 40)

# Group actions by concept
from collections import defaultdict
actions_by_concept = defaultdict(list)
for action in actions:
    actions_by_concept[action['concept']].append(action)

# Display actions organized by concept
for concept, concept_actions in sorted(actions_by_concept.items()):
    print(f"\n{concept.title()}:")
    
    # Group by verb for cleaner display
    verbs = defaultdict(list)
    for action in concept_actions:
        verbs[action['action']].append(action)
    
    for verb, verb_actions in sorted(verbs.items()):
        # Calculate average confidence
        avg_confidence = sum(a['confidence'] for a in verb_actions) / len(verb_actions)
        sources = {a['source_function'] for a in verb_actions}
        
        print(f"  - {verb} (confidence: {avg_confidence:.2f})")
        print(f"    Found in: {', '.join(sources)}")

# Show the knowledge graph with action relationships
print("\n" + "=" * 60)
print("Knowledge Graph with Behaviors:")
print("-" * 40)

# Find all PERFORMS relationships
performs_count = 0
for concept in kg.get_concepts():
    relations = kg.get_relations_with_confidence(concept)
    performs = [r for r in relations if str(r['relation']) == "PERFORMS"]
    
    if performs:
        print(f"\n{concept}:")
        for rel in sorted(performs, key=lambda r: r['confidence'], reverse=True):
            print(f"  PERFORMS -> {rel['target']} (confidence: {rel['confidence']:.3f})")
            performs_count += 1

print(f"\nTotal PERFORMS relationships: {performs_count}")

# Generate natural language summary
print("\n" + "=" * 60)
print("Natural Language Summary:")
print("-" * 40)

from src.regionai.language.doc_generator import DocumentationGenerator
doc_gen = DocumentationGenerator(kg)

functions = ['create_customer', 'update_customer_preferences', 
             'delete_customer', 'calculate_customer_value']

for func in functions:
    summary = doc_gen.generate_summary(func)
    print(f"\n{func}:")
    print(f"  {summary}")

print("\n" + "=" * 60)
print("Demo complete! RegionAI now understands not just what exists,")
print("but what happens - the behaviors and actions in the code.")
print("=" * 60)