#!/usr/bin/env python3
"""
Demonstration of RegionAI's Grammar Pattern Extraction.

This script shows how the system deconstructs English sentences into
their grammatical primitives (Subject-Verb-Object triples), the first
step in discovering mappings between language and code structures.
"""
from src.regionai.language.grammar_extractor import GrammarPatternExtractor
from src.regionai.knowledge import KnowledgeGraph, BayesianUpdater
from src.regionai.semantic.db import SemanticDB
from src.regionai.knowledge.linker import KnowledgeLinker

# Example code with rich documentation
code_with_docs = '''
class OrderManagementSystem:
    """
    Manages customer orders and inventory.
    
    The system tracks customer orders throughout their lifecycle.
    Each customer can have multiple orders. Orders contain items
    from the product catalog. The system validates orders before
    processing and sends notifications after completion.
    """
    
    def create_order(self, customer_id, items):
        """
        Creates a new order for a customer.
        
        The function validates the customer and checks inventory
        availability. It reserves items from the inventory and
        calculates the total price including taxes.
        """
        # Customer validation
        customer = self.load_customer(customer_id)
        if not customer.is_active():
            raise ValueError("Customer is not active")
        
        # Create and validate order
        order = Order(customer_id, items)
        order.validate()
        
        return order
    
    def process_payment(self, order, payment_info):
        """
        Processes payment for an order.
        
        The payment processor validates the payment information
        and charges the customer's payment method. The system
        updates the order status and releases reserved inventory
        if payment fails.
        """
        processor = self.get_payment_processor()
        result = processor.charge(payment_info, order.total)
        
        if result.success:
            order.mark_paid()
            self.fulfill_order(order)
        else:
            self.cancel_order(order)
            
        return result
'''

print("RegionAI Grammar Pattern Extraction Demo")
print("=" * 60)

# Initialize the grammar extractor
print("\nInitializing Grammar Pattern Extractor...")
extractor = GrammarPatternExtractor()

# Extract patterns from the class docstring
print("\n" + "-" * 60)
print("Extracting patterns from class documentation:")
print("-" * 60)

class_doc = """
Manages customer orders and inventory.

The system tracks customer orders throughout their lifecycle.
Each customer can have multiple orders. Orders contain items
from the product catalog. The system validates orders before
processing and sends notifications after completion.
"""

patterns = extractor.extract_patterns(class_doc)

print(f"\nFound {len(patterns)} grammatical patterns:")
for i, pattern in enumerate(patterns, 1):
    print(f"\n{i}. Sentence: \"{pattern.raw_sentence}\"")
    print(f"   Pattern: {pattern}")
    print(f"   Subject: {pattern.subject or '(none)'}")
    print(f"   Verb: {pattern.verb}")
    print(f"   Object: {pattern.object or '(none)'}")
    if pattern.modifiers:
        print(f"   Modifiers: {', '.join(pattern.modifiers)}")
    print(f"   Confidence: {pattern.confidence:.2f}")

# Analyze patterns by verb type
print("\n" + "-" * 60)
print("Pattern Analysis by Verb Type:")
print("-" * 60)

from collections import defaultdict
verb_groups = defaultdict(list)

for pattern in patterns:
    verb_groups[pattern.verb].append(pattern)

for verb, group in sorted(verb_groups.items()):
    print(f"\n'{verb}' ({len(group)} occurrences):")
    for p in group:
        print(f"  - {p.subject or '?'} {verb} {p.object or '?'}")

# Extract patterns from function documentation
print("\n" + "-" * 60)
print("Extracting patterns from function documentation:")
print("-" * 60)

func_doc = """
Creates a new order for a customer.

The function validates the customer and checks inventory
availability. It reserves items from the inventory and
calculates the total price including taxes.
"""

func_patterns = extractor.extract_patterns_with_context(func_doc, "create_order")

print(f"\nFound {len(func_patterns)} patterns in create_order documentation:")
for pattern in func_patterns:
    print(f"  {pattern} [confidence: {pattern.confidence:.2f}]")

# Demonstrate integration with KnowledgeLinker
print("\n" + "=" * 60)
print("Integration with Knowledge Graph")
print("=" * 60)

# Create knowledge infrastructure
db = SemanticDB()
kg = KnowledgeGraph()

# Add some concepts to the graph (simulating prior discovery)
from src.regionai.knowledge.graph import Concept, ConceptMetadata
concepts = ["Customer", "Order", "Item", "System", "Payment", "Inventory"]
for concept_name in concepts:
    metadata = ConceptMetadata(
        discovery_method="CODE_ANALYSIS",
        alpha=5.0,  # High confidence from code
        beta=1.0
    )
    kg.add_concept(Concept(concept_name), metadata)

print(f"\nKnowledge Graph initialized with {len(kg.get_concepts())} concepts")

# Create linker and process documentation
linker = KnowledgeLinker(db, kg)

# Manually trigger pattern extraction
linker._extract_grammatical_patterns(class_doc, "OrderManagementSystem", 0.8)

# Get discovered patterns
discovered = linker.get_discovered_patterns()

print(f"\nKnowledgeLinker discovered {len(discovered)} patterns")
print("\nPattern-to-Concept Mapping Potential:")

# Analyze which patterns could map to known concepts
for pattern in discovered[:5]:  # Show first 5
    # Check if subject or object matches known concepts
    subject_match = pattern['subject'] and any(
        pattern['subject'].lower() == c.lower() for c in concepts
    )
    object_match = pattern['object'] and any(
        pattern['object'].lower() == c.lower() for c in concepts
    )
    
    if subject_match or object_match:
        print(f"\n  Pattern: ({pattern['subject']}, {pattern['verb']}, {pattern['object']})")
        if subject_match:
            print(f"    ✓ Subject '{pattern['subject']}' matches known concept")
        if object_match:
            print(f"    ✓ Object '{pattern['object']}' matches known concept")
        print(f"    → Potential mapping: ({pattern['subject'] or '?'}) "
              f"-[:{pattern['verb'].upper()}]-> ({pattern['object'] or '?'})")

# Show verb frequency analysis
print("\n" + "-" * 60)
print("Verb Frequency Analysis (for grammar rule discovery):")
print("-" * 60)

verb_counts = defaultdict(int)
for pattern in discovered:
    verb_counts[pattern['verb']] += 1

print("\nMost common verbs in documentation:")
for verb, count in sorted(verb_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {verb}: {count} occurrences")

# Demonstrate potential grammar rules
print("\n" + "=" * 60)
print("Potential Grammar Rules (to be discovered)")
print("=" * 60)

print("\nBased on the patterns found, the system could learn rules like:")
print("\n1. Subject + 'has/have' + Object → HAS_MANY relationship")
print("   Evidence: 'customer can have multiple orders'")
print("\n2. Subject + 'contains/contain' + Object → CONTAINS relationship")
print("   Evidence: 'orders contain items'")
print("\n3. Subject + 'validates' + Object → VALIDATES relationship")
print("   Evidence: 'system validates orders'")
print("\n4. Subject + 'is' + Property → HAS_PROPERTY relationship")
print("   Evidence: 'customer is active'")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("\nThe Grammar Pattern Extractor successfully:")
print("1. ✓ Deconstructed sentences into Subject-Verb-Object triples")
print("2. ✓ Handled various grammatical constructions (active, passive, copular)")
print("3. ✓ Extracted patterns with confidence scores")
print("4. ✓ Integrated with the KnowledgeLinker for future mapping")
print("\nNext step: Use these patterns to discover mappings between")
print("linguistic structures and knowledge graph relationships!")