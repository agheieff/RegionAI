"""
High-level API for RegionAI semantic analysis and search.

This module provides user-friendly functions for analyzing code and
discovering semantic relationships between functions.
"""
import ast
import os
from typing import List, Optional, Dict, Tuple, Any

from ..analysis.interprocedural import InterproceduralAnalyzer, AnalysisResult
from ..semantic.db import SemanticDB, SemanticEntry, FunctionName
from ..semantic.fingerprint import SemanticFingerprint, Behavior
from ..language.trainer import LanguageBridgeTrainer
from ..language.projection_model import ModelCheckpoint


def analyze_code(code: str, include_source: bool = True) -> AnalysisResult:
    """
    Analyze a Python codebase and return comprehensive results.
    
    Args:
        code: Python source code to analyze
        include_source: Whether to include source code for enhanced documentation extraction
        
    Returns:
        AnalysisResult containing summaries, fingerprints, and semantic database
    """
    tree = ast.parse(code)
    analyzer = InterproceduralAnalyzer()
    source_code = code if include_source else None
    return analyzer.analyze_program(tree, source_code)


def find_similar_functions(code: str, target_function_name: str,
                          similarity_threshold: float = 0.5) -> SemanticDB:
    """
    Analyze a codebase and find functions semantically similar to the target.
    
    Args:
        code: Python source code to analyze
        target_function_name: Name of the function to find similar matches for
        similarity_threshold: Minimum similarity score (0-1) for matches
        
    Returns:
        SemanticDB containing only similar functions
    """
    # Run full analysis
    result = analyze_code(code)
    
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


def find_equivalent_functions(code: str, target_function_name: str) -> SemanticDB:
    """
    Find all functions that are semantically equivalent to the target.
    
    Args:
        code: Python source code to analyze
        target_function_name: Name of the function to find equivalents for
        
    Returns:
        SemanticDB containing only equivalent functions
    """
    # Run full analysis
    result = analyze_code(code)
    
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


def find_functions_by_behavior(code: str, behavior: Behavior) -> SemanticDB:
    """
    Find all functions that exhibit a specific behavior.
    
    Args:
        code: Python source code to analyze
        behavior: The behavior to search for
        
    Returns:
        SemanticDB containing matching functions
    """
    result = analyze_code(code)
    
    if not result.semantic_db:
        return SemanticDB()
    
    # Create new DB for results
    behavior_db = SemanticDB()
    
    for entry in result.semantic_db.find_by_behavior(behavior):
        behavior_db.add(entry)
    
    return behavior_db


def find_pure_functions(code: str) -> SemanticDB:
    """Find all pure functions in the codebase."""
    return find_functions_by_behavior(code, Behavior.PURE)


def find_identity_functions(code: str) -> SemanticDB:
    """Find all identity functions in the codebase."""
    return find_functions_by_behavior(code, Behavior.IDENTITY)


def find_nullable_functions(code: str) -> SemanticDB:
    """Find all functions that may return None."""
    return find_functions_by_behavior(code, Behavior.NULLABLE_RETURN)


def compare_functions(code: str, func1_name: str, func2_name: str) -> Dict[str, any]:
    """
    Compare two functions semantically.
    
    Args:
        code: Python source code containing both functions
        func1_name: Name of first function
        func2_name: Name of second function
        
    Returns:
        Dictionary with comparison results including:
        - equivalent: bool indicating if functions are semantically equivalent
        - similarity: float similarity score (0-1)
        - common_behaviors: list of shared behaviors
        - unique_to_first: behaviors only in first function
        - unique_to_second: behaviors only in second function
    """
    result = analyze_code(code)
    
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


def discover_patterns(code: str) -> Dict[str, List[str]]:
    """
    Discover common patterns in the codebase.
    
    Returns a dictionary mapping pattern names to lists of functions
    that exhibit those patterns.
    """
    result = analyze_code(code)
    
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


def suggest_refactoring_opportunities(code: str) -> List[Dict[str, any]]:
    """
    Analyze code and suggest refactoring opportunities based on semantic patterns.
    
    Returns a list of suggestions, each containing:
    - type: The type of refactoring opportunity
    - functions: Functions involved
    - description: Explanation of the opportunity
    """
    result = analyze_code(code)
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