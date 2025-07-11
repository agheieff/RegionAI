#!/usr/bin/env python3
"""
Demonstration of the RegionAI Reasoning Engine.

Shows how the reasoning engine dynamically discovers knowledge from code
using the heuristic-function bridge architecture.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from regionai.knowledge.hub import KnowledgeHub
from regionai.reasoning import ReasoningEngine
from regionai.reasoning.budget import DiscoveryBudget


def demo_reasoning_engine():
    """Demonstrate the reasoning engine's knowledge discovery capabilities."""
    print("=== RegionAI Reasoning Engine Demo ===\n")
    
    # Create knowledge hub and reasoning engine
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    # Show available heuristics
    print("Available Heuristics:")
    print("-" * 50)
    heuristics = engine.get_available_heuristics()
    for name, info in heuristics.items():
        print(f"• {name}")
        print(f"  Implementation: {info['implementation_id']}")
        print(f"  Utility Score: {info['utility_score']}")
        print(f"  Has Implementation: {info['has_implementation']}")
        print()
    
    # Test code for analysis
    test_code = '''
def process_customer_order(customer, order):
    """Process a customer's order through the system."""
    # Validate customer first
    customer.validate()
    customer.check_credit_limit()
    
    # Then process the order
    order.calculate_tax()
    order.apply_discounts()
    order.calculate_total()
    
    # Save everything
    customer.save()
    order.save()
    
    # Send notifications
    customer.send_confirmation_email()
    order.notify_warehouse()
    
    return order
'''
    
    print("\nAnalyzing Code:")
    print("-" * 50)
    print(test_code)
    
    # Run discovery cycle
    context = {
        'code': test_code,
        'function_name': 'process_customer_order',
        'confidence': 0.85
    }
    
    print("\nRunning Prioritized Discovery Cycle...")
    print("-" * 50)
    
    # Create a discovery budget
    budget = DiscoveryBudget(max_heuristics_to_run=2)
    print(f"Budget: Execute top {budget.max_heuristics_to_run} heuristics\n")
    
    results = engine.run_prioritized_discovery_cycle(context, budget)
    
    print(f"Heuristics Considered: {results.get('heuristics_considered', 'N/A')}")
    print(f"Heuristics Executed: {results['heuristics_executed']}")
    print(f"Budget Exhausted: {results.get('budget_exhausted', False)}")
    print(f"Discoveries Made: {len(results['discoveries'])}")
    print(f"Errors: {len(results['errors'])}")
    
    if results['discoveries']:
        print("\nDiscoveries:")
        for discovery in results['discoveries']:
            print(f"  • {discovery}")
    
    # Show knowledge graph state
    print("\n\nKnowledge Graph State:")
    print("-" * 50)
    print(f"Concepts: {len(hub.wkg.get_concepts())}")
    print(f"Relations: {len(hub.wkg.graph.edges())}")
    
    # Show some discovered knowledge
    print("\nDiscovered Concepts:")
    for concept in sorted(hub.wkg.get_concepts())[:10]:  # Show first 10
        metadata = hub.wkg.get_concept_metadata(concept)
        if metadata:
            print(f"  • {concept} (belief: {metadata.belief:.2f})")
        else:
            print(f"  • {concept}")
    
    print("\nSample Relationships:")
    # Show relationships for Customer concept
    from regionai.knowledge.graph import Concept
    customer = Concept("Customer")
    if customer in hub.wkg:
        relations = hub.wkg.get_relations_with_confidence(customer)
        for rel in relations[:5]:  # Show first 5
            if rel['source'] == customer:
                print(f"  • Customer {rel['relation']} {rel['target']} "
                      f"(confidence: {rel['confidence']:.2f})")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    demo_reasoning_engine()