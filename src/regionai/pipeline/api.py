"""
High-level API for RegionAI semantic analysis and search.

This module provides user-friendly functions for analyzing code and
discovering semantic relationships between functions.
"""
import ast
import os
from typing import List, Optional, Dict, Any

from ..analysis.interprocedural import InterproceduralAnalyzer, AnalysisResult
from ..semantic.db import SemanticDB
from ..semantic.fingerprint import SemanticFingerprint, Behavior
from ..language.trainer import LanguageBridgeTrainer
from ..knowledge.graph import KnowledgeGraph, Concept
from ..knowledge.discovery import ConceptDiscoverer
from ..knowledge.linker import KnowledgeLinker
from ..config import RegionAIConfig


def analyze_code(code: str, include_source: bool = True, 
                config: Optional[RegionAIConfig] = None) -> AnalysisResult:
    """
    Analyze a Python codebase and return comprehensive results.
    
    Args:
        code: Python source code to analyze
        include_source: Whether to include source code for enhanced documentation extraction
        config: Optional configuration for analysis (uses DEFAULT_CONFIG if not provided)
        
    Returns:
        AnalysisResult containing summaries, fingerprints, and semantic database
    """
    tree = ast.parse(code)
    analyzer = InterproceduralAnalyzer()
    source_code = code if include_source else None
    
    # Note: When interprocedural.py is updated to use config, pass it here
    # For now, the analyzer will create its own context with the default config
    return analyzer.analyze_program(tree, source_code)


def find_similar_functions(code: str, target_function_name: str,
                          similarity_threshold: float = 0.5,
                          config: Optional[RegionAIConfig] = None) -> SemanticDB:
    """
    Analyze a codebase and find functions semantically similar to the target.
    
    Args:
        code: Python source code to analyze
        target_function_name: Name of the function to find similar matches for
        similarity_threshold: Minimum similarity score (0-1) for matches
        config: Optional configuration for analysis
        
    Returns:
        SemanticDB containing only similar functions
    """
    # Run full analysis
    result = analyze_code(code, config=config)
    
    if not result.semantic_db:
        return SemanticDB()
    
    # Find the target function's fingerprint(s)
    target_entries = []
    for entry in result.semantic_db:
        if entry.function_name == target_function_name:
            target_entries.append(entry)
    
    if not target_entries:
        raise ValueError(f"Function '{target_function_name}' not found in code")
    
    # Create new DB for results
    similar_db = SemanticDB()
    
    # For each variant of the target function, find similar functions
    seen = set()
    for target_entry in target_entries:
        similar = result.semantic_db.find_similar(
            target_entry.fingerprint, 
            similarity_threshold
        )
        
        for entry, score in similar:
            # Avoid duplicates
            key = (entry.function_name, frozenset(entry.fingerprint.behaviors))
            if key not in seen:
                seen.add(key)
                similar_db.add(entry)
    
    return similar_db


def find_equivalent_functions(code: str, target_function_name: str,
                            config: Optional[RegionAIConfig] = None) -> SemanticDB:
    """
    Find all functions that are semantically equivalent to the target.
    
    Args:
        code: Python source code to analyze
        target_function_name: Name of the function to find equivalents for
        config: Optional configuration for analysis
        
    Returns:
        SemanticDB containing only equivalent functions
    """
    # Run full analysis
    result = analyze_code(code, config=config)
    
    if not result.semantic_db:
        return SemanticDB()
    
    # Find the target function's fingerprint(s)
    target_entries = []
    for entry in result.semantic_db:
        if entry.function_name == target_function_name:
            target_entries.append(entry)
    
    if not target_entries:
        raise ValueError(f"Function '{target_function_name}' not found in code")
    
    # Create new DB for results
    equivalent_db = SemanticDB()
    
    # Find exact matches for each variant
    seen = set()
    for target_entry in target_entries:
        equivalents = result.semantic_db.find_equivalent(target_entry.fingerprint)
        
        for entry in equivalents:
            # Avoid duplicates
            key = (entry.function_name, frozenset(entry.fingerprint.behaviors))
            if key not in seen:
                seen.add(key)
                equivalent_db.add(entry)
    
    return equivalent_db


def find_functions_by_behavior(code: str, behavior: Behavior,
                             config: Optional[RegionAIConfig] = None) -> SemanticDB:
    """
    Find all functions that exhibit a specific behavior.
    
    Args:
        code: Python source code to analyze
        behavior: The behavior to search for
        config: Optional configuration for analysis
        
    Returns:
        SemanticDB containing matching functions
    """
    result = analyze_code(code, config=config)
    
    if not result.semantic_db:
        return SemanticDB()
    
    # Create new DB for results
    behavior_db = SemanticDB()
    
    for entry in result.semantic_db.find_by_behavior(behavior):
        behavior_db.add(entry)
    
    return behavior_db


def find_pure_functions(code: str, config: Optional[RegionAIConfig] = None) -> SemanticDB:
    """Find all pure functions in the codebase."""
    return find_functions_by_behavior(code, Behavior.PURE, config=config)


def find_identity_functions(code: str, config: Optional[RegionAIConfig] = None) -> SemanticDB:
    """Find all identity functions in the codebase."""
    return find_functions_by_behavior(code, Behavior.IDENTITY, config=config)


def find_nullable_functions(code: str, config: Optional[RegionAIConfig] = None) -> SemanticDB:
    """Find all functions that may return None."""
    return find_functions_by_behavior(code, Behavior.NULLABLE_RETURN, config=config)


def compare_functions(code: str, func1_name: str, func2_name: str,
                     config: Optional[RegionAIConfig] = None) -> Dict[str, any]:
    """
    Compare two functions semantically.
    
    Args:
        code: Python source code containing both functions
        func1_name: Name of first function
        func2_name: Name of second function
        config: Optional configuration for analysis
        
    Returns:
        Dictionary with comparison results including:
        - equivalent: bool indicating if functions are semantically equivalent
        - similarity: float similarity score (0-1)
        - common_behaviors: list of shared behaviors
        - unique_to_first: behaviors only in first function
        - unique_to_second: behaviors only in second function
    """
    result = analyze_code(code, config=config)
    
    if not result.semantic_db:
        raise ValueError("Analysis failed")
    
    # Find entries for both functions
    func1_entries = [e for e in result.semantic_db if e.function_name == func1_name]
    func2_entries = [e for e in result.semantic_db if e.function_name == func2_name]
    
    if not func1_entries:
        raise ValueError(f"Function '{func1_name}' not found")
    if not func2_entries:
        raise ValueError(f"Function '{func2_name}' not found")
    
    # For simplicity, compare the first variant of each
    # In a more sophisticated implementation, we might compare all variants
    fp1 = func1_entries[0].fingerprint
    fp2 = func2_entries[0].fingerprint
    
    comparison = {
        'equivalent': fp1.behaviors == fp2.behaviors,
        'similarity': len(fp1.behaviors & fp2.behaviors) / max(len(fp1.behaviors | fp2.behaviors), 1),
        'common_behaviors': sorted([b.name for b in (fp1.behaviors & fp2.behaviors)]),
        'unique_to_first': sorted([b.name for b in (fp1.behaviors - fp2.behaviors)]),
        'unique_to_second': sorted([b.name for b in (fp2.behaviors - fp1.behaviors)])
    }
    
    return comparison


def discover_patterns(code: str, config: Optional[RegionAIConfig] = None) -> Dict[str, List[str]]:
    """
    Discover common patterns in the codebase.
    
    Returns a dictionary mapping pattern names to lists of functions
    that exhibit those patterns.
    """
    result = analyze_code(code, config=config)
    
    if not result.semantic_db:
        return {}
    
    patterns = {
        'Pure Functions': [],
        'Identity Functions': [],
        'Constant Functions': [],
        'Nullable Functions': [],
        'Safe Functions': [],
        'Validators': [],
        'Side-Effect Functions': [],
    }
    
    for entry in result.semantic_db:
        fp = entry.fingerprint
        func = entry.function_name
        
        if fp.is_pure():
            patterns['Pure Functions'].append(func)
        if Behavior.IDENTITY in fp.behaviors:
            patterns['Identity Functions'].append(func)
        if Behavior.CONSTANT_RETURN in fp.behaviors:
            patterns['Constant Functions'].append(func)
        if Behavior.NULLABLE_RETURN in fp.behaviors:
            patterns['Nullable Functions'].append(func)
        if fp.is_safe():
            patterns['Safe Functions'].append(func)
        if Behavior.VALIDATOR in fp.behaviors:
            patterns['Validators'].append(func)
        if (Behavior.MODIFIES_GLOBALS in fp.behaviors or 
            Behavior.MODIFIES_PARAMETERS in fp.behaviors or
            Behavior.PERFORMS_IO in fp.behaviors):
            patterns['Side-Effect Functions'].append(func)
    
    # Remove duplicates and sort
    for pattern in patterns:
        patterns[pattern] = sorted(list(set(patterns[pattern])))
    
    # Remove empty patterns
    return {k: v for k, v in patterns.items() if v}


def suggest_refactoring_opportunities(code: str, 
                                    config: Optional[RegionAIConfig] = None) -> List[Dict[str, any]]:
    """
    Analyze code and suggest refactoring opportunities based on semantic patterns.
    
    Args:
        code: Python source code to analyze
        config: Optional configuration for analysis
    
    Returns a list of suggestions, each containing:
    - type: The type of refactoring opportunity
    - functions: Functions involved
    - description: Explanation of the opportunity
    """
    result = analyze_code(code, config=config)
    suggestions = []
    
    if not result.semantic_db:
        return suggestions
    
    # Find duplicate implementations
    seen_fingerprints = {}
    for entry in result.semantic_db:
        fp_key = frozenset(entry.fingerprint.behaviors)
        if fp_key not in seen_fingerprints:
            seen_fingerprints[fp_key] = []
        seen_fingerprints[fp_key].append(entry.function_name)
    
    # Suggest consolidating duplicate implementations
    for fp_key, functions in seen_fingerprints.items():
        if len(functions) > 1:
            suggestions.append({
                'type': 'Duplicate Implementation',
                'functions': sorted(list(set(functions))),
                'description': f"These {len(set(functions))} functions have identical semantic behavior and could potentially be consolidated"
            })
    
    # Find functions that could use library replacements
    for entry in result.semantic_db:
        if (Behavior.IDENTITY in entry.fingerprint.behaviors and 
            entry.function_name not in ['identity', 'id']):
            suggestions.append({
                'type': 'Use Built-in',
                'functions': [entry.function_name],
                'description': "This identity function could potentially be replaced with direct parameter passing"
            })
    
    # Find impure functions that could be made pure
    for entry in result.semantic_db:
        fp = entry.fingerprint
        if (not fp.is_pure() and 
            Behavior.PERFORMS_IO not in fp.behaviors and
            Behavior.MODIFIES_GLOBALS not in fp.behaviors):
            suggestions.append({
                'type': 'Make Pure',
                'functions': [entry.function_name],
                'description': "This function modifies parameters but could potentially be refactored to be pure"
            })
    
    return suggestions


def train_language_model(semantic_db: SemanticDB, 
                        model_type: str = "standard",
                        epochs: int = 100,
                        checkpoint_dir: Optional[str] = None,
                        device: Optional[str] = None) -> Dict[str, Any]:
    """
    Train a language model to map natural language to semantic fingerprints.
    
    This function orchestrates the complete training process, from extracting
    training candidates from the semantic database to training the neural model.
    
    Args:
        semantic_db: SemanticDB containing documented fingerprints for training
        model_type: Type of model to train ("standard", "attention", or "ensemble")
        epochs: Number of training epochs
        checkpoint_dir: Directory to save model checkpoints (default: "./checkpoints")
        device: Device to train on ("cuda", "cpu", or None for auto-detect)
        
    Returns:
        Dictionary containing training results:
        - final_loss: Final validation loss
        - final_metrics: Final validation metrics (precision, recall, F1)
        - train_losses: List of training losses per epoch
        - val_losses: List of validation losses per epoch
        - epochs_trained: Number of epochs actually trained
        - model_path: Path to the saved best model
        
    Raises:
        ValueError: If no suitable training candidates are found in the database
    """
    # Set default checkpoint directory
    if checkpoint_dir is None:
        checkpoint_dir = os.path.join(os.getcwd(), "checkpoints")
    
    # Create trainer
    trainer = LanguageBridgeTrainer(model_type=model_type, device=device)
    
    # Train the model
    print(f"Training {model_type} projection model...")
    results = trainer.train_from_semantic_db(
        semantic_db,
        epochs=epochs,
        checkpoint_dir=checkpoint_dir
    )
    
    # Save the final model
    model_path = os.path.join(checkpoint_dir, f"language_bridge_{model_type}_final.pt")
    trainer.save_model(model_path)
    results['model_path'] = model_path
    
    # Print summary
    print(f"\nTraining completed:")
    print(f"  Final loss: {results['final_loss']:.4f}")
    print(f"  Final F1 score: {results['final_metrics']['f1']:.4f}")
    print(f"  Epochs trained: {results['epochs_trained']}")
    print(f"  Model saved to: {model_path}")
    
    return results


def predict_semantics_from_text(text: str, 
                               model_path: Optional[str] = None,
                               model_type: str = "standard",
                               threshold: float = 0.5) -> SemanticFingerprint:
    """
    Predict semantic fingerprint from natural language description.
    
    This function loads a trained language model and uses it to predict
    which code behaviors are described by the given text.
    
    Args:
        text: Natural language description of code functionality
        model_path: Path to saved model (if None, looks for default model)
        model_type: Type of model that was trained ("standard", "attention", "ensemble")
        threshold: Threshold for behavior activation (0-1)
        
    Returns:
        SemanticFingerprint with predicted behaviors
        
    Raises:
        ValueError: If no model is found or text is empty
        FileNotFoundError: If model_path doesn't exist
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Find model path if not provided
    if model_path is None:
        # Look for default model in common locations
        possible_paths = [
            f"./checkpoints/language_bridge_{model_type}_final.pt",
            f"./language_bridge_{model_type}_final.pt",
            f"./models/language_bridge_{model_type}_final.pt"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if model_path is None:
            raise FileNotFoundError(
                "No trained model found. Please train a model first using "
                "train_language_model() or provide an explicit model_path."
            )
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at: {model_path}")
    
    # Create trainer and load model
    trainer = LanguageBridgeTrainer(model_type=model_type)
    trainer.load_model(model_path)
    
    # Make prediction
    fingerprint = trainer.predict(text, threshold=threshold)
    
    return fingerprint


def batch_predict_semantics(texts: List[str],
                           model_path: Optional[str] = None,
                           model_type: str = "standard",
                           threshold: float = 0.5) -> List[SemanticFingerprint]:
    """
    Predict semantic fingerprints for multiple text descriptions.
    
    Args:
        texts: List of natural language descriptions
        model_path: Path to saved model
        model_type: Type of model that was trained
        threshold: Threshold for behavior activation
        
    Returns:
        List of SemanticFingerprints corresponding to input texts
    """
    # For efficiency, we could optimize this to batch process
    # For now, we'll use the single prediction function
    return [predict_semantics_from_text(text, model_path, model_type, threshold) 
            for text in texts]


def evaluate_language_model(semantic_db: SemanticDB,
                           model_path: str,
                           model_type: str = "standard") -> Dict[str, Any]:
    """
    Evaluate a trained language model on a semantic database.
    
    Args:
        semantic_db: SemanticDB with documented fingerprints for evaluation
        model_path: Path to the trained model
        model_type: Type of model that was trained
        
    Returns:
        Dictionary with evaluation metrics:
        - accuracy: Exact match accuracy
        - precision: Average precision across behaviors
        - recall: Average recall across behaviors
        - f1: Average F1 score
        - per_behavior_metrics: Detailed metrics for each behavior
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at: {model_path}")
    
    # Extract test candidates
    test_entries = semantic_db.find_training_candidates()
    if not test_entries:
        raise ValueError("No suitable test candidates found in SemanticDB")
    
    # Create trainer and load model
    trainer = LanguageBridgeTrainer(model_type=model_type)
    trainer.load_model(model_path)
    
    # Evaluate on each entry
    correct_exact = 0
    all_predictions = []
    all_targets = []
    
    for entry in test_entries:
        if entry.documented_fingerprint and entry.documented_fingerprint.nl_context.has_documentation():
            # Get text and true fingerprint
            text = entry.documented_fingerprint.nl_context.get_text_content()
            true_fp = entry.documented_fingerprint.fingerprint
            
            # Predict
            pred_fp = trainer.predict(text)
            
            # Check exact match
            if pred_fp.behaviors == true_fp.behaviors:
                correct_exact += 1
            
            # Store for detailed metrics
            all_predictions.append(pred_fp)
            all_targets.append(true_fp)
    
    # Calculate metrics
    n_samples = len(all_predictions)
    accuracy = correct_exact / n_samples if n_samples > 0 else 0
    
    # Calculate per-behavior metrics
    all_behaviors = list(Behavior)
    behavior_metrics = {}
    
    for behavior in all_behaviors:
        true_positives = sum(1 for pred, true in zip(all_predictions, all_targets)
                           if behavior in pred.behaviors and behavior in true.behaviors)
        false_positives = sum(1 for pred, true in zip(all_predictions, all_targets)
                            if behavior in pred.behaviors and behavior not in true.behaviors)
        false_negatives = sum(1 for pred, true in zip(all_predictions, all_targets)
                            if behavior not in pred.behaviors and behavior in true.behaviors)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        behavior_metrics[behavior.name] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'support': sum(1 for true in all_targets if behavior in true.behaviors)
        }
    
    # Calculate average metrics
    avg_precision = sum(m['precision'] for m in behavior_metrics.values()) / len(behavior_metrics)
    avg_recall = sum(m['recall'] for m in behavior_metrics.values()) / len(behavior_metrics)
    avg_f1 = sum(m['f1'] for m in behavior_metrics.values()) / len(behavior_metrics)
    
    return {
        'accuracy': accuracy,
        'precision': avg_precision,
        'recall': avg_recall,
        'f1': avg_f1,
        'n_samples': n_samples,
        'per_behavior_metrics': behavior_metrics
    }


def build_knowledge_graph(code: str, include_source: bool = True, 
                         enrich_from_docs: bool = True,
                         config: Optional[RegionAIConfig] = None) -> KnowledgeGraph:
    """
    Build a knowledge graph of real-world concepts from code analysis.
    
    This function orchestrates the complete process of discovering concepts:
    1. Analyzes the code to build a SemanticDB
    2. Applies concept discovery heuristics
    3. Optionally enriches the graph with relationships from documentation
    4. Returns a populated KnowledgeGraph
    
    Args:
        code: Python source code to analyze
        include_source: Whether to include source for documentation extraction
        enrich_from_docs: Whether to enrich the graph using natural language documentation
        config: Optional configuration for analysis
        
    Returns:
        KnowledgeGraph containing discovered concepts and relationships
    """
    # First, perform semantic analysis
    print("Performing semantic analysis...")
    result = analyze_code(code, include_source, config=config)
    
    if not result.semantic_db:
        print("Warning: No semantic information found")
        return KnowledgeGraph()
    
    print(f"Analyzed {len(result.semantic_db._entries)} functions")
    
    # Discover concepts from the semantic database
    print("Discovering concepts...")
    discoverer = ConceptDiscoverer(result.semantic_db)
    knowledge_graph = discoverer.discover_concepts()
    
    # Print discovery statistics
    print(f"Discovered {len(knowledge_graph)} concepts")
    print(f"Found {len(knowledge_graph.graph.edges())} relationships from code patterns")
    
    # Enrich with relationships from documentation
    if enrich_from_docs and include_source:
        print("Enriching graph from documentation...")
        linker = KnowledgeLinker(result.semantic_db, knowledge_graph)
        knowledge_graph = linker.enrich_graph()
        
        # Print enrichment statistics
        discovered_rels = linker.get_discovered_relationships()
        if discovered_rels:
            print(f"Discovered {len(discovered_rels)} additional relationships from text")
    
    print(f"Final graph: {len(knowledge_graph)} concepts, {len(knowledge_graph.graph.edges())} relationships")
    
    return knowledge_graph


def build_knowledge_graph_from_semantic_db(semantic_db: SemanticDB) -> KnowledgeGraph:
    """
    Build a knowledge graph from an existing SemanticDB.
    
    Useful when you already have analyzed code and want to discover concepts.
    
    Args:
        semantic_db: Pre-analyzed semantic database
        
    Returns:
        KnowledgeGraph with discovered concepts
    """
    discoverer = ConceptDiscoverer(semantic_db)
    return discoverer.discover_concepts()


def discover_domain_model(code: str, output_file: Optional[str] = None,
                         enrich_from_docs: bool = True) -> Dict[str, Any]:
    """
    Discover the domain model (concepts and relationships) from code.
    
    This provides a comprehensive analysis including:
    - Discovered concepts with confidence scores
    - Relationships between concepts (from code patterns and documentation)
    - Discovery report explaining how concepts were found
    - Enrichment report showing relationships found in text
    
    Args:
        code: Python source code to analyze
        output_file: Optional file path to save the knowledge graph JSON
        enrich_from_docs: Whether to enrich with relationships from documentation
        
    Returns:
        Dictionary containing:
        - knowledge_graph: The KnowledgeGraph object
        - concepts: List of discovered concepts with metadata
        - relationships: List of discovered relationships
        - discovery_report: Human-readable discovery report
        - enrichment_report: Report of relationships found in documentation
        - visualization: Text visualization of the graph
    """
    # Build the knowledge graph with enrichment
    kg = build_knowledge_graph(code, include_source=True, enrich_from_docs=enrich_from_docs)
    
    # Extract information for the result
    concepts = []
    for concept in kg.get_concepts():
        metadata = kg.get_concept_metadata(concept)
        concepts.append({
            'name': concept,
            'discovery_method': metadata.discovery_method if metadata else 'unknown',
            'confidence': metadata.confidence if metadata else 0.0,
            'source_functions': metadata.source_functions if metadata else []
        })
    
    relationships = []
    for concept in kg.get_concepts():
        for source, target, relation in kg.get_relations(concept):
            if source == concept:  # Avoid duplicates
                relationships.append({
                    'source': source,
                    'target': target,
                    'relation': relation
                })
    
    # Generate discovery report
    result = analyze_code(code, include_source=True)
    discoverer = ConceptDiscoverer(result.semantic_db)
    discoverer.discover_concepts()  # Re-run to populate internal state
    discovery_report = discoverer.generate_discovery_report()
    
    # Generate enrichment report if applicable
    enrichment_report = ""
    if enrich_from_docs:
        linker = KnowledgeLinker(result.semantic_db, kg)
        linker.enrich_graph()  # Re-run to populate internal state
        enrichment_report = linker.generate_enrichment_report()
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write(kg.to_json())
        print(f"Knowledge graph saved to: {output_file}")
    
    return {
        'knowledge_graph': kg,
        'concepts': sorted(concepts, key=lambda c: c['confidence'], reverse=True),
        'relationships': relationships,
        'discovery_report': discovery_report,
        'enrichment_report': enrichment_report,
        'visualization': kg.visualize()
    }


def generate_docs_for_function(function_name: str, code: str = None, 
                             knowledge_graph: KnowledgeGraph = None) -> str:
    """
    Generate natural language documentation for a function using the Knowledge Graph.
    
    This function leverages RegionAI's semantic understanding to produce
    human-readable summaries of what a function does based on the concepts
    it involves and their relationships.
    
    Args:
        function_name: Name of the function to document
        code: Optional source code to analyze (if knowledge_graph not provided)
        knowledge_graph: Optional pre-built knowledge graph to use
        
    Returns:
        A human-readable summary of the function's purpose
        
    Example:
        >>> code = '''
        ... def get_customer_orders(customer_id):
        ...     return db.query(Order).filter(Order.customer_id == customer_id).all()
        ... '''
        >>> summary = generate_docs_for_function('get_customer_orders', code)
        >>> print(summary)
        This function appears to be primarily concerned with the concepts of 
        Customer, Orders, and Query.
    """
    # Import here to avoid circular dependencies
    from ..language import DocumentationGenerator
    
    # If no knowledge graph provided, build one from code
    if knowledge_graph is None:
        if code is None:
            return f"Error: Either code or knowledge_graph must be provided to generate documentation for '{function_name}'."
        
        # Build and enrich the knowledge graph
        kg = build_knowledge_graph(code, include_source=True, enrich_from_docs=True)
    else:
        kg = knowledge_graph
    
    # Create documentation generator
    doc_gen = DocumentationGenerator(kg)
    
    # Generate summary
    summary = doc_gen.generate_summary(function_name)
    
    return summary


def find_concept_functions(code: str, concept_name: str) -> Dict[str, List[str]]:
    """
    Find all functions related to a specific concept.
    
    Args:
        code: Python source code to analyze
        concept_name: Name of the concept to search for (e.g., "User", "Product")
        
    Returns:
        Dictionary mapping operation types to function names:
        - create: Functions that create the concept
        - read: Functions that read/retrieve the concept
        - update: Functions that update the concept
        - delete: Functions that delete the concept
        - other: Other related functions
    """
    # Analyze and discover concepts
    result = analyze_code(code)
    discoverer = ConceptDiscoverer(result.semantic_db)
    kg = discoverer.discover_concepts()
    
    # Check if concept exists
    concept = Concept(concept_name.title())
    if concept not in kg:
        # Try to find similar concepts
        similar = [c for c in kg.get_concepts() 
                  if concept_name.lower() in c.lower()]
        if similar:
            concept = similar[0]
        else:
            return {
                'create': [],
                'read': [],
                'update': [],
                'delete': [],
                'other': []
            }
    
    # Get metadata to find source functions
    metadata = kg.get_concept_metadata(concept)
    if not metadata:
        return {
            'create': [],
            'read': [],
            'update': [],
            'delete': [],
            'other': []
        }
    
    # Organize functions by operation type
    organized = {
        'create': [],
        'read': [],
        'update': [],
        'delete': [],
        'other': []
    }
    
    # Check if discovered through CRUD pattern
    for pattern in discoverer._discovered_patterns:
        if pattern.concept_name == concept:
            organized['create'] = pattern.create_functions
            organized['read'] = pattern.read_functions
            organized['update'] = pattern.update_functions
            organized['delete'] = pattern.delete_functions
            break
    
    # Add any other functions from metadata
    for func in metadata.source_functions:
        found = False
        for op_type in ['create', 'read', 'update', 'delete']:
            if func in organized[op_type]:
                found = True
                break
        if not found:
            organized['other'].append(func)
    
    return organized


def build_knowledge_graph_from_codebase(code: str) -> KnowledgeGraph:
    """
    Build a complete, enriched knowledge graph from a codebase.
    
    This is the main entry point for knowledge extraction. It orchestrates:
    1. Semantic analysis of the code
    2. Concept discovery using multiple heuristics
    3. Relationship enrichment from documentation
    
    Args:
        code: Python source code to analyze
        
    Returns:
        A fully populated and enriched KnowledgeGraph
    """
    return build_knowledge_graph(code, include_source=True, enrich_from_docs=True)


def explain_concept_discovery(code: str, concept_name: str) -> str:
    """
    Explain how and why a specific concept was discovered.
    
    Args:
        code: Python source code that was analyzed
        concept_name: Name of the concept to explain
        
    Returns:
        Human-readable explanation of the discovery process
    """
    # Analyze and discover
    result = analyze_code(code)
    discoverer = ConceptDiscoverer(result.semantic_db)
    kg = discoverer.discover_concepts()
    
    concept = Concept(concept_name.title())
    metadata = kg.get_concept_metadata(concept)
    
    if not metadata:
        return f"Concept '{concept_name}' was not discovered in the analyzed code."
    
    lines = [f"Discovery Explanation for '{concept}':", "=" * 50, ""]
    
    # Discovery method
    lines.append(f"Discovery Method: {metadata.discovery_method}")
    lines.append(f"Confidence Score: {metadata.confidence:.2f}")
    lines.append("")
    
    # Explain based on method
    if metadata.discovery_method == "CRUD_PATTERN":
        lines.append("This concept was discovered through CRUD pattern analysis.")
        lines.append("The following CRUD operations were found:")
        
        # Find the CRUD pattern
        for pattern in discoverer._discovered_patterns:
            if pattern.concept_name == concept:
                if pattern.create_functions:
                    lines.append(f"  Create: {', '.join(pattern.create_functions)}")
                if pattern.read_functions:
                    lines.append(f"  Read: {', '.join(pattern.read_functions)}")
                if pattern.update_functions:
                    lines.append(f"  Update: {', '.join(pattern.update_functions)}")
                if pattern.delete_functions:
                    lines.append(f"  Delete: {', '.join(pattern.delete_functions)}")
                break
                
    elif metadata.discovery_method == "NOUN_EXTRACTION":
        lines.append("This concept was discovered through noun extraction.")
        lines.append(f"The term '{concept}' appeared frequently in:")
        lines.append("  - Function names")
        lines.append("  - Documentation strings")
        
    elif "BEHAVIOR_ANALYSIS" in metadata.discovery_method:
        lines.append("This concept was discovered through semantic behavior analysis.")
        lines.append(f"Related behaviors: {', '.join(metadata.related_behaviors)}")
    
    lines.append("")
    lines.append("Source Functions:")
    for func in metadata.source_functions[:10]:  # Limit to 10
        lines.append(f"  - {func}")
    
    if len(metadata.source_functions) > 10:
        lines.append(f"  ... and {len(metadata.source_functions) - 10} more")
    
    return "\n".join(lines)