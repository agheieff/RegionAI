#!/usr/bin/env python3
"""
Demonstration of the Reasoning Engine's learning capabilities.

Shows how the engine adapts its utility scores based on discovery success.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from regionai.knowledge.hub import KnowledgeHub
from regionai.reasoning import ReasoningEngine
from regionai.reasoning.budget import DiscoveryBudget


def demo_learning():
    """Demonstrate how the engine learns from experience."""
    print("=== Reasoning Engine Learning Demo ===\n")
    
    # Create hub and engine
    hub = KnowledgeHub()
    engine = ReasoningEngine(hub)
    
    # Show initial scores
    print("Initial Heuristic Scores:")
    print("-" * 50)
    for name, info in engine.get_available_heuristics().items():
        if info['has_implementation']:
            print(f"  {name}: {info['utility_score']:.3f}")
    
    # First discovery cycle - fresh knowledge graph
    print("\n\nCycle 1: Fresh Knowledge Graph")
    print("-" * 50)
    
    test_code1 = '''
def create_user_account(user, account):
    """Create a new user account."""
    user.validate()
    account.create()
    account.save()
    user.send_welcome_email()
'''
    
    context1 = {
        'code': test_code1,
        'function_name': 'create_user_account',
        'confidence': 0.8
    }
    
    budget = DiscoveryBudget(max_heuristics_to_run=3)
    results1 = engine.run_prioritized_discovery_cycle(context1, budget)
    
    print(f"Executed: {results1['heuristics_executed']} heuristics")
    print(f"Discoveries: {results1['discoveries']}")
    
    # Show updated scores after first cycle
    print("\nScores After Cycle 1:")
    for name, info in engine.get_available_heuristics().items():
        if info['has_implementation']:
            print(f"  {name}: {info['utility_score']:.3f}")
    
    # Second discovery cycle - same code (no new discoveries)
    print("\n\nCycle 2: Same Code (No New Discoveries)")
    print("-" * 50)
    
    results2 = engine.run_prioritized_discovery_cycle(context1, budget)
    
    print(f"Executed: {results2['heuristics_executed']} heuristics")
    print(f"Discoveries: {results2['discoveries']}")
    
    # Show updated scores after second cycle
    print("\nScores After Cycle 2 (penalties for no discoveries):")
    for name, info in engine.get_available_heuristics().items():
        if info['has_implementation']:
            print(f"  {name}: {info['utility_score']:.3f}")
    
    # Third discovery cycle - new code with different patterns
    print("\n\nCycle 3: New Code Pattern")
    print("-" * 50)
    
    test_code3 = '''
def update_inventory(product):
    """Update product inventory."""
    product.check_stock()
    product.update_quantity()
    product.log_change()
'''
    
    context3 = {
        'code': test_code3,
        'function_name': 'update_inventory',
        'confidence': 0.8
    }
    
    results3 = engine.run_prioritized_discovery_cycle(context3, budget)
    
    print(f"Executed: {results3['heuristics_executed']} heuristics")
    print(f"Discoveries: {results3['discoveries']}")
    
    # Show final scores
    print("\nFinal Scores After 3 Cycles:")
    print("-" * 50)
    for name, info in engine.get_available_heuristics().items():
        if info['has_implementation']:
            print(f"  {name}: {info['utility_score']:.3f}")
    
    # Show the knowledge graph state
    print(f"\n\nKnowledge Graph Summary:")
    print("-" * 50)
    print(f"Total Concepts: {len(hub.wkg.get_concepts())}")
    print(f"Total Relations: {len(hub.wkg.graph.edges())}")
    
    # Show how the priority order might have changed
    print("\n\nHeuristic Priority Order (by score):")
    print("-" * 50)
    heuristics = [(name, info) for name, info in engine.get_available_heuristics().items()
                  if info['has_implementation']]
    heuristics.sort(key=lambda x: x[1]['utility_score'], reverse=True)
    
    for i, (name, info) in enumerate(heuristics, 1):
        print(f"{i}. {name}: {info['utility_score']:.3f}")
    
    print("\n=== Demo Complete ===")
    print("\nKey Observations:")
    print("- Heuristics that find new knowledge get score boosts")
    print("- Heuristics that find nothing get score penalties")
    print("- The engine adapts its priorities based on experience")
    print("- Over time, the most effective heuristics rise to the top")


if __name__ == "__main__":
    demo_learning()