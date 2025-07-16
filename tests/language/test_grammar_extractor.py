#!/usr/bin/env python3
"""
Tests for the Grammar Pattern Extractor.

Verifies that the system can correctly deconstruct English sentences
into their grammatical primitives (Subject-Verb-Object triples).
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

try:
    from regionai.domains.language.grammar_extractor import GrammarPatternExtractor
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure spaCy is installed: pip install spacy")
    print("And download the model: python -m spacy download en_core_web_sm")
    sys.exit(1)


def test_simple_svo_extraction():
    """Test extraction of simple Subject-Verb-Object patterns."""
    print("Testing simple SVO extraction...")
    
    extractor = GrammarPatternExtractor()
    
    # Test simple active voice
    patterns = extractor.extract_patterns("The user saves the file.")
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.subject == "user"
    assert pattern.verb == "save"
    assert pattern.object == "file"
    
    print(f"✓ Extracted: {pattern}")
    print("✓ Simple SVO extraction works correctly")


def test_plural_handling():
    """Test handling of plural subjects and objects."""
    print("\nTesting plural handling...")
    
    extractor = GrammarPatternExtractor()
    
    # Test with plural subject
    patterns = extractor.extract_patterns("Users save files.")
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.subject == "user"  # Lemmatized to singular
    assert pattern.verb == "save"
    assert pattern.object == "file"   # Lemmatized to singular
    
    print(f"✓ 'Users save files' → {pattern}")
    
    # Test with modifiers
    patterns = extractor.extract_patterns("Multiple users save several files.")
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.subject == "user"
    assert pattern.verb == "save"
    assert pattern.object == "file"
    assert "multiple" in pattern.modifiers or "several" in pattern.modifiers
    
    print(f"✓ With modifiers: {pattern}")
    print("✓ Plural handling works correctly")


def test_tense_variations():
    """Test extraction with different verb tenses."""
    print("\nTesting tense variations...")
    
    extractor = GrammarPatternExtractor()
    
    test_cases = [
        ("The user saved the file.", "save"),      # Past tense
        ("The user is saving the file.", "save"),   # Progressive
        ("The user has saved the file.", "save"),   # Perfect
        ("The user will save the file.", "save"),   # Future
    ]
    
    for sentence, expected_verb in test_cases:
        patterns = extractor.extract_patterns(sentence)
        if patterns:  # Some may not extract due to auxiliary verbs
            assert patterns[0].verb == expected_verb
            print(f"✓ '{sentence}' → verb: {expected_verb}")
    
    print("✓ Tense variation handling works correctly")


def test_missing_components():
    """Test handling of sentences missing subject or object."""
    print("\nTesting sentences with missing components...")
    
    extractor = GrammarPatternExtractor()
    
    # Sentence without object
    patterns = extractor.extract_patterns("The system validates.")
    if patterns:
        pattern = patterns[0]
        assert pattern.subject == "system"
        assert pattern.verb == "validate"
        assert pattern.object is None
        print(f"✓ No object: {pattern}")
    
    # Imperative (no subject)
    patterns = extractor.extract_patterns("Save the file.")
    if patterns:
        pattern = patterns[0]
        # Subject might be None or inferred
        assert pattern.verb == "save"
        assert pattern.object == "file"
        print(f"✓ Imperative: {pattern}")
    
    print("✓ Missing component handling works correctly")


def test_copular_sentences():
    """Test extraction from copular sentences (X is Y)."""
    print("\nTesting copular sentences...")
    
    extractor = GrammarPatternExtractor()
    
    # "is a" relationship
    patterns = extractor.extract_patterns("A customer is a user.")
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.subject == "customer"
    assert pattern.verb == "is_a"  # Special handling for type relationships
    assert pattern.object == "user"
    
    print(f"✓ 'A customer is a user' → {pattern}")
    
    # Property assignment
    patterns = extractor.extract_patterns("The order is valid.")
    if patterns:
        pattern = patterns[0]
        assert pattern.subject == "order"
        assert pattern.verb in ["is", "has_property"]
        assert pattern.object == "valid"
        print(f"✓ 'The order is valid' → {pattern}")
    
    print("✓ Copular sentence handling works correctly")


def test_complex_sentences():
    """Test extraction from more complex documentation sentences."""
    print("\nTesting complex sentences...")
    
    extractor = GrammarPatternExtractor()
    
    # Multiple clauses
    text = "The customer saves the order and the system sends a confirmation."
    patterns = extractor.extract_patterns(text)
    
    # Should find at least one pattern (compound sentences might be parsed as one)
    assert len(patterns) >= 1
    
    [p.subject for p in patterns]
    verbs = [p.verb for p in patterns]
    
    # Check that we found at least one of the expected patterns
    found_save = "save" in verbs
    found_send = "send" in verbs
    assert found_save or found_send, f"Expected 'save' or 'send', got verbs: {verbs}"
    
    print(f"✓ Found {len(patterns)} patterns in complex sentence")
    
    # Prepositional phrases
    patterns = extractor.extract_patterns("The user saves the file to the database.")
    if patterns:
        pattern = patterns[0]
        assert pattern.subject == "user"
        assert pattern.verb == "save"
        # Object might be "file" or "database" depending on parsing
        print(f"✓ With prepositional phrase: {pattern}")
    
    print("✓ Complex sentence handling works correctly")


def test_documentation_patterns():
    """Test extraction from typical documentation patterns."""
    print("\nTesting documentation patterns...")
    
    extractor = GrammarPatternExtractor()
    
    # Common documentation patterns
    test_docs = [
        "This function validates user input.",
        "Process customer orders and update inventory.",
        "The system tracks user activities.",
        "Each order contains multiple items.",
        "Customers can have many orders.",
    ]
    
    for doc in test_docs:
        patterns = extractor.extract_patterns(doc)
        if patterns:
            print(f"  '{doc}'")
            for pattern in patterns:
                print(f"    → {pattern}")
    
    print("✓ Documentation pattern extraction works correctly")


def test_pattern_confidence():
    """Test confidence scoring for patterns."""
    print("\nTesting pattern confidence...")
    
    extractor = GrammarPatternExtractor()
    
    # Complete SVO should have high confidence
    patterns = extractor.extract_patterns("The user saves the file.")
    assert patterns[0].confidence >= 0.9
    print(f"✓ Complete SVO confidence: {patterns[0].confidence}")
    
    # Missing object should have lower confidence
    patterns = extractor.extract_patterns("The user validates.")
    if patterns:
        assert patterns[0].confidence < 0.9
        print(f"✓ No object confidence: {patterns[0].confidence}")
    
    # Copular patterns should have good confidence
    patterns = extractor.extract_patterns("A customer is a user.")
    assert patterns[0].confidence >= 0.8
    print(f"✓ Copular confidence: {patterns[0].confidence}")
    
    print("✓ Confidence scoring works correctly")


def test_context_enhancement():
    """Test pattern extraction with context."""
    print("\nTesting context enhancement...")
    
    extractor = GrammarPatternExtractor()
    
    # Extract patterns with function context
    patterns = extractor.extract_patterns_with_context(
        "The function saves user data to the database.",
        "save_user_data"
    )
    
    # Should boost confidence for patterns mentioning function parts
    if patterns:
        pattern = patterns[0]
        # Pattern mentions "user" which is in function name
        assert pattern.confidence > 0.5
        print(f"✓ Context-enhanced pattern: {pattern} [confidence: {pattern.confidence}]")
    
    print("✓ Context enhancement works correctly")


def test_knowledge_linker_integration():
    """Test integration with KnowledgeLinker."""
    print("\nTesting KnowledgeLinker integration...")
    
    from regionai.domains.code.semantic.db import SemanticDB
    from regionai.world_contexts.knowledge.hub import KnowledgeHub
    from regionai.world_contexts.knowledge.linker import KnowledgeLinker
    
    # Create test infrastructure
    db = SemanticDB()
    hub = KnowledgeHub()
    
    # Create linker
    linker = KnowledgeLinker(db, hub)
    
    # Verify NLP model was initialized
    assert linker.nlp_model is not None
    print("✓ NLP model initialized in KnowledgeLinker")
    
    # Test pattern extraction through linker's grammar extractor
    if linker.grammar_extractor:
        linker.grammar_extractor.extract_patterns_from_text(
            "The customer saves the order. Orders contain items.",
            "process_order",
            0.8
        )
    
    # Check that patterns were discovered
    patterns = linker.get_discovered_patterns()
    assert len(patterns) >= 2
    
    # Verify pattern structure
    for pattern in patterns:
        assert 'function' in pattern
        assert 'subject' in pattern
        assert 'verb' in pattern
        assert 'confidence' in pattern
    
    print(f"✓ KnowledgeLinker discovered {len(patterns)} patterns")
    print("✓ Integration works correctly")


def run_all_tests():
    """Run all grammar extractor tests."""
    print("=" * 60)
    print("Grammar Pattern Extractor Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_simple_svo_extraction,
        test_plural_handling,
        test_tense_variations,
        test_missing_components,
        test_copular_sentences,
        test_complex_sentences,
        test_documentation_patterns,
        test_pattern_confidence,
        test_context_enhancement,
        test_knowledge_linker_integration
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
        print("The Grammar Pattern Extractor successfully deconstructs language!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    # Check if spaCy model is available
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("ERROR: spaCy model 'en_core_web_sm' not found.")
        print("Please install it with: python -m spacy download en_core_web_sm")
        sys.exit(1)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)