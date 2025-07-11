#!/usr/bin/env python3
"""
Demonstration of RegionAI's Sequential Action Analysis.

This script shows how the system can discover and understand the
temporal ordering of actions in code, building causal models of behavior.
"""
from src.regionai.knowledge import (
    KnowledgeGraph, BayesianUpdater, ActionDiscoverer
)
from src.regionai.language import DocumentationGenerator
from src.regionai.pipeline.api import build_knowledge_graph

# Example code with rich sequential behavior
code = '''
class DataProcessor:
    """Handles data processing pipeline."""
    
    def process_dataset(self, dataset_path):
        """Process a dataset through the full pipeline."""
        # Step 1: Load and validate
        data = self.load_data(dataset_path)
        if not self.validate_data(data):
            self.log_error("Invalid data format")
            return None
        
        # Step 2: Preprocess
        data = self.clean_data(data)
        data = self.normalize_data(data)
        
        # Step 3: Feature extraction
        features = self.extract_features(data)
        features = self.select_best_features(features)
        
        # Step 4: Model training
        model = self.create_model()
        model.train(features)
        
        # Step 5: Evaluation and saving
        metrics = self.evaluate_model(model, features)
        if metrics.accuracy > 0.8:
            self.save_model(model)
            self.generate_report(metrics)
        else:
            self.log_warning("Model accuracy too low")
            self.retry_with_different_params()
        
        return model
    
    def batch_process(self, file_list):
        """Process multiple files in sequence."""
        results = []
        
        # Initialize batch processing
        self.prepare_batch()
        
        for file_path in file_list:
            # Load file
            data = self.load_file(file_path)
            
            # Validate before processing
            if self.validate_file(data):
                # Process the file
                result = self.process_file(data)
                result = self.optimize_result(result)
                
                # Save result
                self.save_result(result)
                results.append(result)
            else:
                # Handle invalid file
                self.skip_file(file_path)
                self.log_skip(file_path)
        
        # Finalize batch
        self.finalize_batch(results)
        self.generate_summary(results)
        
        return results
'''

print("RegionAI Sequential Action Analysis Demo")
print("=" * 60)

# Build knowledge graph with action discovery
print("\nBuilding knowledge graph with sequential analysis...")
kg = build_knowledge_graph(code, include_source=True, enrich_from_docs=True)

print(f"\nKnowledge graph contains:")
print(f"- {len(kg.get_concepts())} concepts")
print(f"- {len(kg.graph.edges())} relationships")

# Analyze sequences for specific functions
discoverer = ActionDiscoverer()

print("\n" + "=" * 60)
print("Analyzing Sequential Patterns in process_dataset()")
print("=" * 60)

# Extract the process_dataset function
func_start = code.find("def process_dataset")
func_end = code.find("def batch_process")
process_dataset_code = "def process_dataset" + code[func_start+len("def process_dataset"):func_end].strip()

# Discover actions and sequences
actions = discoverer.discover_actions(process_dataset_code, "process_dataset")
sequences = discoverer.discover_action_sequences(process_dataset_code, "process_dataset")

print(f"\nDiscovered {len(actions)} actions:")
for i, action in enumerate(actions[:10]):  # Show first 10
    print(f"  {i+1}. {action.concept}.{action.verb}() [confidence: {action.confidence:.2f}]")
if len(actions) > 10:
    print(f"  ... and {len(actions) - 10} more")

print(f"\nDiscovered {len(sequences)} sequential relationships:")
for i, (act1, act2) in enumerate(sequences[:8]):  # Show first 8
    print(f"  {i+1}. {act1.verb} → {act2.verb}")
if len(sequences) > 8:
    print(f"  ... and {len(sequences) - 8} more")

# Analyze causal chains
print("\n" + "-" * 40)
print("Causal Chains Discovered:")
print("-" * 40)

# Build a sequence map
from collections import defaultdict
sequence_map = defaultdict(list)
for act1, act2 in sequences:
    sequence_map[act1.verb].append(act2.verb)

# Find chains starting from common entry points
def find_chains(start_verb, sequence_map, max_depth=5, current_chain=None):
    """Find all chains starting from a verb."""
    if current_chain is None:
        current_chain = [start_verb]
    
    if len(current_chain) >= max_depth:
        return [current_chain]
    
    chains = []
    next_verbs = sequence_map.get(start_verb, [])
    
    if not next_verbs:
        return [current_chain]
    
    for next_verb in next_verbs:
        if next_verb not in current_chain:  # Avoid cycles
            new_chain = current_chain + [next_verb]
            chains.extend(find_chains(next_verb, sequence_map, max_depth, new_chain))
    
    return chains if chains else [current_chain]

# Find chains from key starting points
start_points = ["load", "validate", "clean", "extract"]
all_chains = []

for start in start_points:
    if start in sequence_map:
        chains = find_chains(start, sequence_map)
        for chain in chains:
            if len(chain) >= 3:  # Only show chains with 3+ steps
                all_chains.append(chain)

# Show unique chains
seen_chains = set()
for chain in all_chains:
    chain_str = " → ".join(chain)
    if chain_str not in seen_chains and len(chain) >= 3:
        seen_chains.add(chain_str)
        print(f"  • {chain_str}")

# Analyze PRECEDES relationships in the knowledge graph
print("\n" + "=" * 60)
print("PRECEDES Relationships in Knowledge Graph")
print("=" * 60)

# Find all PRECEDES relationships
precedes_relationships = []
for concept in kg.get_concepts():
    relations = kg.get_relations_with_confidence(concept)
    for rel in relations:
        if str(rel['relation']) == "PRECEDES":
            precedes_relationships.append({
                'from': str(concept),
                'to': str(rel['target']),
                'confidence': rel['confidence']
            })

# Sort by confidence
precedes_relationships.sort(key=lambda x: x['confidence'], reverse=True)

print(f"\nTop temporal relationships (by confidence):")
for i, rel in enumerate(precedes_relationships[:10]):
    print(f"  {i+1}. {rel['from']} → {rel['to']} [confidence: {rel['confidence']:.3f}]")

# Demonstrate behavioral understanding
print("\n" + "=" * 60)
print("Behavioral Understanding")
print("=" * 60)

# Find concepts with the most sequential behaviors
action_concepts = []
for concept in kg.get_concepts():
    metadata = kg.get_concept_metadata(concept)
    if metadata and metadata.properties.get('is_action'):
        # Count incoming and outgoing PRECEDES relationships
        incoming = sum(1 for rel in kg.get_relations_with_confidence(concept) 
                      if str(rel['relation']) == "PRECEDES")
        
        # Count where this concept precedes others
        outgoing = 0
        for other_concept in kg.get_concepts():
            for rel in kg.get_relations_with_confidence(other_concept):
                if str(rel['relation']) == "PRECEDES" and str(rel['target']) == str(concept):
                    incoming += 1
                elif str(rel['source']) == str(concept) and str(rel['relation']) == "PRECEDES":
                    outgoing += 1
        
        action_concepts.append({
            'concept': str(concept),
            'incoming': incoming,
            'outgoing': outgoing,
            'total': incoming + outgoing
        })

# Sort by total connections
action_concepts.sort(key=lambda x: x['total'], reverse=True)

print("\nMost connected actions in the temporal flow:")
for i, action in enumerate(action_concepts[:5]):
    if action['total'] > 0:
        print(f"  {i+1}. {action['concept']}: {action['incoming']} incoming, {action['outgoing']} outgoing")

# Generate a process summary
print("\n" + "=" * 60)
print("Process Summary Generation")
print("=" * 60)

doc_gen = DocumentationGenerator(kg)

# Generate summaries for both functions
for func_name in ["process_dataset", "batch_process"]:
    print(f"\n{func_name}():")
    print("-" * len(func_name) + "---")
    
    # Traditional summary
    trad_summary = doc_gen.generate_summary(func_name)
    print(f"Concept Summary: {trad_summary}")
    
    # Behavioral summary  
    behav_summary = doc_gen.generate_behavioral_summary(func_name)
    print(f"Behavioral Summary: {behav_summary}")

print("\n" + "=" * 60)
print("Sequential Analysis Complete!")
print("=" * 60)
print("\nKey Achievements:")
print("1. ✓ Discovered action sequences preserving execution order")
print("2. ✓ Built PRECEDES relationships showing temporal flow")
print("3. ✓ Identified causal chains of behavior")
print("4. ✓ Understanding of process workflows")
print("\nRegionAI now understands not just WHAT code does,")
print("but HOW it does it - the sequential flow of execution!")