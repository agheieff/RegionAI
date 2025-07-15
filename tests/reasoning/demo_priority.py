#!/usr/bin/env python3
"""
Demonstration of priority-based heuristic execution in RegionAI.

Shows how the reasoning engine respects utility scores and budget constraints.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from regionai.knowledge.hub import KnowledgeHub
from regionai.reasoning import ReasoningEngine
from regionai.reasoning.budget import DiscoveryBudget


def demo_priority_execution():
    """Demonstrate how budget affects which heuristics run."""
    print("=== Priority-Based Heuristic Execution Demo ===\n")
    
    # Test code that can trigger multiple heuristics
    test_code = '''
def handle_customer_payment(customer, payment):
    """Handle a customer payment transaction."""
    # Validate inputs
    customer.validate()
    payment.validate()
    
    # Process payment
    payment.authorize()
    payment.capture()
    
    # Update records
    customer.update_balance()
    customer.save()
    
    # Send notifications
    customer.send_receipt()
    payment.log_transaction()
'''
    
    context = {
        'code': test_code,
        'function_name': 'handle_customer_payment',
        'confidence': 0.85
    }
    
    # Test with different budget values
    for budget_size in [1, 2, 3]:
        print(f"\n{'='*50}")
        print(f"Running with budget = {budget_size}")
        print('='*50)
        
        # Create fresh hub and engine for each test
        hub = KnowledgeHub()
        engine = ReasoningEngine(hub)
        
        # Get available heuristics
        available = engine.get_available_heuristics()
        implemented = [(name, info) for name, info in available.items() 
                      if info['has_implementation']]
        implemented.sort(key=lambda x: x[1]['utility_score'], reverse=True)
        
        print("\nHeuristic Priority Order:")
        for i, (name, info) in enumerate(implemented):
            print(f"{i+1}. {name} (score: {info['utility_score']})")
        
        # Run discovery with budget
        budget = DiscoveryBudget(max_heuristics_to_run=budget_size)
        results = engine.run_prioritized_discovery_cycle(context, budget)
        
        print(f"\nExecution Results:")
        print(f"  Heuristics Considered: {results['heuristics_considered']}")
        print(f"  Heuristics Executed: {results['heuristics_executed']}")
        print(f"  Budget Exhausted: {results['budget_exhausted']}")
        
        # Show what was discovered
        if results['discoveries']:
            print(f"\nDiscoveries:")
            for discovery in results['discoveries']:
                print(f"  • {discovery}")
        
        # Show relation types to indicate which heuristics ran
        all_edges = list(hub.wkg.graph.edges(data=True))
        relation_types = {}
        for edge in all_edges:
            rel_type = edge[2]['label']
            relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
        
        if relation_types:
            print(f"\nRelation Types Created:")
            for rel_type, count in sorted(relation_types.items()):
                print(f"  • {rel_type}: {count} instances")
                # Map relation types to heuristics
                if rel_type == 'PRECEDES':
                    print(f"    (from Sequential AST nodes heuristic)")
                elif rel_type == 'PERFORMS':
                    print(f"    (from Method call heuristic)")
                elif rel_type == 'RELATED_TO':
                    print(f"    (from Co-occurrence heuristic)")
    
    print("\n" + "="*50)
    print("Demo Complete - Budget controls which heuristics execute!")
    print("="*50)


if __name__ == "__main__":
    demo_priority_execution()