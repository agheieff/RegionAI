#!/usr/bin/env python3
"""
Test suite for the Language Bridge components of RegionAI.

This module tests the vectorizers, projection models, training pipeline,
and high-level APIs that enable mapping from natural language to semantic fingerprints.
"""

import sys
import os
import ast
import tempfile
import shutil
import torch

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from regionai.language.vectorizer import (
    TextVectorizer, FingerprintVectorizer, DatasetVectorizer
)
from regionai.language.projection_model import (
    ProjectionModel, AttentionProjectionModel, EnsembleProjectionModel,
    create_projection_model, ModelCheckpoint
)
from regionai.language.trainer import LanguageBridgeTrainer
from regionai.semantic.fingerprint import (
    SemanticFingerprint, Behavior, NaturalLanguageContext, DocumentedFingerprint
)
from regionai.semantic.db import SemanticDB, SemanticEntry
from regionai.analysis.summary import CallContext
from regionai.pipeline.api import (
    analyze_code, train_language_model, predict_semantics_from_text,
    batch_predict_semantics, evaluate_language_model
)


def test_text_vectorizer():
    """Test text vectorization functionality."""
    print("\n=== Testing TextVectorizer ===")
    
    vectorizer = TextVectorizer()
    
    # Test single text
    text = "This function returns the identity of its input"
    embedding = vectorizer.vectorize_single(text)
    assert embedding.shape == (vectorizer.embedding_dim,), f"Expected shape ({vectorizer.embedding_dim},), got {embedding.shape}"
    print(f"✓ Single text vectorization: {embedding.shape}")
    
    # Test batch
    texts = [
        "Returns the sum of two numbers",
        "Checks if a value is None",
        "Pure function with no side effects"
    ]
    embeddings = vectorizer.vectorize(texts)
    assert embeddings.shape == (3, vectorizer.embedding_dim), f"Expected shape (3, {vectorizer.embedding_dim}), got {embeddings.shape}"
    print(f"✓ Batch text vectorization: {embeddings.shape}")
    
    # Test empty list
    empty_embeddings = vectorizer.vectorize([])
    assert empty_embeddings.shape == (0, vectorizer.embedding_dim)
    print(f"✓ Empty list handling: {empty_embeddings.shape}")


def test_fingerprint_vectorizer():
    """Test fingerprint vectorization functionality."""
    print("\n=== Testing FingerprintVectorizer ===")
    
    vectorizer = FingerprintVectorizer()
    
    # Create test fingerprints
    fp1 = SemanticFingerprint(behaviors={Behavior.PURE, Behavior.IDENTITY})
    fp2 = SemanticFingerprint(behaviors={Behavior.NULLABLE_RETURN, Behavior.MODIFIES_GLOBALS})
    fp3 = SemanticFingerprint(behaviors={Behavior.PURE})
    
    # Test single fingerprint
    vec1 = vectorizer.vectorize_single(fp1)
    assert vec1.shape == (vectorizer.num_behaviors,)
    assert vec1.sum() == 2  # Two behaviors active
    print(f"✓ Single fingerprint vectorization: {vec1.shape}, sum={vec1.sum()}")
    
    # Test batch
    vectors = vectorizer.vectorize([fp1, fp2, fp3])
    assert vectors.shape == (3, vectorizer.num_behaviors)
    print(f"✓ Batch fingerprint vectorization: {vectors.shape}")
    
    # Test decode
    decoded_fp = vectorizer.decode(vec1)
    assert decoded_fp.behaviors == fp1.behaviors
    print(f"✓ Fingerprint decode: {len(decoded_fp.behaviors)} behaviors recovered")
    
    # Test decode with threshold
    vec_soft = vec1.clone()
    vec_soft[vectorizer.behavior_to_idx[Behavior.PURE]] = 0.7
    vec_soft[vectorizer.behavior_to_idx[Behavior.IDENTITY]] = 0.3
    decoded_high = vectorizer.decode(vec_soft, threshold=0.6)
    assert Behavior.PURE in decoded_high.behaviors
    assert Behavior.IDENTITY not in decoded_high.behaviors
    print(f"✓ Threshold decode: {len(decoded_high.behaviors)} behaviors above threshold")


def test_dataset_vectorizer():
    """Test dataset vectorization functionality."""
    print("\n=== Testing DatasetVectorizer ===")
    
    vectorizer = DatasetVectorizer()
    
    # Create test data
    training_pairs = [
        ("Returns the input unchanged", SemanticFingerprint(behaviors={Behavior.IDENTITY, Behavior.PURE})),
        ("Modifies global state", SemanticFingerprint(behaviors={Behavior.MODIFIES_GLOBALS, Behavior.MAY_NOT_RETURN})),
        ("Validates input and returns boolean", SemanticFingerprint(behaviors={Behavior.VALIDATOR, Behavior.PURE}))
    ]
    
    text_emb, fp_vec = vectorizer.prepare_training_data(training_pairs)
    
    assert text_emb.shape[0] == 3
    assert fp_vec.shape[0] == 3
    assert text_emb.shape[1] == vectorizer.text_vectorizer.embedding_dim
    assert fp_vec.shape[1] == vectorizer.fingerprint_vectorizer.num_behaviors
    
    print(f"✓ Dataset preparation: text={text_emb.shape}, fingerprints={fp_vec.shape}")
    
    # Test dimensions
    text_dim, fp_dim = vectorizer.get_dimensions()
    assert text_dim == text_emb.shape[1]
    assert fp_dim == fp_vec.shape[1]
    print(f"✓ Dimensions: text_dim={text_dim}, fingerprint_dim={fp_dim}")


def test_projection_models():
    """Test different projection model architectures."""
    print("\n=== Testing Projection Models ===")
    
    text_dim = 384  # Typical sentence transformer dimension
    fp_dim = 27     # Number of behaviors
    
    # Test standard model
    model = ProjectionModel(text_dim, fp_dim)
    input_tensor = torch.randn(5, text_dim)
    output = model(input_tensor)
    assert output.shape == (5, fp_dim)
    assert (output >= 0).all() and (output <= 1).all()  # Sigmoid output
    print(f"✓ Standard model: {output.shape}")
    
    # Test attention model
    attention_model = AttentionProjectionModel(text_dim, fp_dim)
    output_attn = attention_model(input_tensor)
    assert output_attn.shape == (5, fp_dim)
    print(f"✓ Attention model: {output_attn.shape}")
    
    # Test ensemble model
    ensemble_model = EnsembleProjectionModel(text_dim, fp_dim, num_models=3)
    output_ensemble = ensemble_model(input_tensor)
    assert output_ensemble.shape == (5, fp_dim)
    print(f"✓ Ensemble model: {output_ensemble.shape}")
    
    # Test factory function
    for model_type in ["standard", "attention", "ensemble"]:
        model = create_projection_model(text_dim, fp_dim, model_type=model_type)
        assert model is not None
        print(f"✓ Created {model_type} model via factory")


def test_model_checkpoint():
    """Test model saving and loading."""
    print("\n=== Testing Model Checkpoint ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and save model
        model = ProjectionModel(384, 27)
        filepath = os.path.join(tmpdir, "test_model.pt")
        metadata = {"test": "value", "epoch": 10}
        
        ModelCheckpoint.save(model, filepath, metadata)
        assert os.path.exists(filepath)
        print(f"✓ Model saved to {filepath}")
        
        # Load model
        loaded_model = ModelCheckpoint.load(ProjectionModel, filepath)
        assert isinstance(loaded_model, ProjectionModel)
        
        # Check weights are the same
        for p1, p2 in zip(model.parameters(), loaded_model.parameters()):
            assert torch.allclose(p1, p2)
        print("✓ Model loaded successfully with matching weights")


def test_language_bridge_trainer():
    """Test the high-level training interface."""
    print("\n=== Testing LanguageBridgeTrainer ===")
    
    # Create a small semantic DB with documented fingerprints
    db = SemanticDB()
    
    # Add some training examples
    examples = [
        ("identity", "Returns the input unchanged", {Behavior.IDENTITY, Behavior.PURE}),
        ("double", "Doubles the input value", {Behavior.PURE}),
        ("validate_email", "Validates email format", {Behavior.VALIDATOR, Behavior.PURE}),
        ("save_to_db", "Saves data to database", {Behavior.PERFORMS_IO, Behavior.MODIFIES_GLOBALS}),
        ("get_or_none", "Returns value or None", {Behavior.NULLABLE_RETURN}),
    ]
    
    for func_name, doc, behaviors in examples:
        # Create a context for each function
        context = CallContext(function_name=func_name, parameter_states=())
        nl_context = NaturalLanguageContext(
            function_name=func_name,
            docstring=doc
        )
        fingerprint = SemanticFingerprint(behaviors=behaviors)
        documented_fp = DocumentedFingerprint(fingerprint, nl_context)
        
        entry = SemanticEntry(
            function_name=func_name,
            context=context,
            fingerprint=fingerprint,
            documented_fingerprint=documented_fp
        )
        db.add(entry)
    
    print(f"✓ Created semantic DB with {len(db._entries)} entries")
    
    # Test trainer creation
    trainer = LanguageBridgeTrainer(model_type="standard")
    assert trainer is not None
    print("✓ Created trainer")
    
    # Test prediction before training (should fail)
    try:
        trainer.predict("Some text")
        assert False, "Should fail before training"
    except ValueError as e:
        print("✓ Correctly fails prediction before training")
    
    # We won't actually train here as it takes time, but verify the interface exists
    assert hasattr(trainer, 'train_from_semantic_db')
    assert hasattr(trainer, 'predict')
    assert hasattr(trainer, 'save_model')
    assert hasattr(trainer, 'load_model')
    print("✓ All trainer methods available")


def test_high_level_apis():
    """Test the high-level API functions."""
    print("\n=== Testing High-Level APIs ===")
    
    # Test code analysis with documentation
    code = '''
def identity(x):
    """Returns the input unchanged."""
    return x

def double(x):
    """Doubles the input value."""
    return x * 2

def validate_positive(x):
    """
    Validates that x is positive.
    
    Returns:
        True if x > 0, False otherwise
    """
    return x > 0
'''
    
    result = analyze_code(code, include_source=True)
    assert result.semantic_db is not None
    assert len(result.semantic_db._entries) > 0
    print(f"✓ Code analysis found {len(result.semantic_db._entries)} functions")
    
    # Verify documentation was extracted
    has_documented = any(
        entry.documented_fingerprint is not None 
        for entry in result.semantic_db._entries
    )
    assert has_documented
    print("✓ Documentation extraction working")
    
    # Test prediction API (without actual model)
    try:
        predict_semantics_from_text("Test function")
    except FileNotFoundError:
        print("✓ Prediction API correctly reports missing model")
    
    # Test batch prediction API structure
    assert callable(batch_predict_semantics)
    print("✓ Batch prediction API available")
    
    # Test evaluation API structure  
    assert callable(evaluate_language_model)
    print("✓ Evaluation API available")


def test_integration_example():
    """Test a complete integration example."""
    print("\n=== Testing Integration Example ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Analyze code
        code = '''
def add(a, b):
    """Adds two numbers together."""
    return a + b

def is_even(n):
    """Checks if a number is even."""
    return n % 2 == 0

def factorial(n):
    """Calculates factorial recursively."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def print_result(x):
    """Prints the result to console."""
    print(f"Result: {x}")
'''
        
        result = analyze_code(code, include_source=True)
        print(f"✓ Analyzed {len(result.semantic_db._entries)} functions")
        
        # Check we have training candidates
        candidates = result.semantic_db.find_training_candidates()
        assert len(candidates) > 0
        print(f"✓ Found {len(candidates)} training candidates")
        
        # Demonstrate the training API would work
        # (We don't actually train to keep tests fast)
        assert callable(train_language_model)
        print("✓ Training API ready")
        
        # Test model save/load with a dummy model
        model = ProjectionModel(384, 27)
        model_path = os.path.join(tmpdir, "test_model.pt")
        ModelCheckpoint.save(model, model_path)
        
        # Create trainer and load model manually for testing
        trainer = LanguageBridgeTrainer()
        trainer.model = ModelCheckpoint.load(ProjectionModel, model_path)
        
        # Test prediction
        test_text = "Adds two numbers"
        fingerprint = trainer.predict(test_text)
        assert isinstance(fingerprint, SemanticFingerprint)
        print(f"✓ Prediction returned fingerprint with {len(fingerprint.behaviors)} behaviors")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("RegionAI Language Bridge Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_text_vectorizer,
        test_fingerprint_vectorizer,
        test_dataset_vectorizer,
        test_projection_models,
        test_model_checkpoint,
        test_language_bridge_trainer,
        test_high_level_apis,
        test_integration_example
    ]
    
    failed = 0
    for test_func in test_functions:
        try:
            test_func()
        except Exception as e:
            print(f"\n✗ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)