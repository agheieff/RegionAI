#!/usr/bin/env python3
"""
Tests for the centralized component loader utilities.

Verifies that optional components are loaded consistently with proper
error handling across the RegionAI codebase.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from tier1.utils.component_loader import (
    load_optional_component,
    requires_component,
    get_nlp_model,
    OptionalComponentMixin,
    clear_component_cache
)


class TestComponentLoader(unittest.TestCase):
    """Test the component loader utilities."""
    
    def setUp(self):
        """Clear component cache before each test."""
        clear_component_cache()
    
    def test_successful_component_loading(self):
        """Test loading a component that exists."""
        mock_component = MagicMock()
        loader = lambda: mock_component
        
        result = load_optional_component(
            "Test Component",
            loader,
            cache_key="test"
        )
        
        self.assertEqual(result, mock_component)
    
    def test_failed_component_loading_with_fallback(self):
        """Test loading a component that fails with a fallback value."""
        def failing_loader():
            raise ImportError("Module not found")
        
        fallback = "fallback_value"
        
        with self.assertLogs(level='WARNING') as log:
            result = load_optional_component(
                "Missing Component",
                failing_loader,
                fallback_value=fallback
            )
        
        self.assertEqual(result, fallback)
        self.assertTrue(any("Failed to load Missing Component" in msg for msg in log.output))
    
    def test_component_caching(self):
        """Test that components are cached when cache_key is provided."""
        call_count = 0
        
        def counting_loader():
            nonlocal call_count
            call_count += 1
            return f"component_{call_count}"
        
        # First load
        result1 = load_optional_component(
            "Cached Component",
            counting_loader,
            cache_key="cached_test"
        )
        
        # Second load (should use cache)
        result2 = load_optional_component(
            "Cached Component",
            counting_loader,
            cache_key="cached_test"
        )
        
        self.assertEqual(result1, result2)
        self.assertEqual(call_count, 1)  # Loader called only once
    
    def test_custom_error_types(self):
        """Test handling of custom error types."""
        def custom_error_loader():
            raise OSError("Model file not found")
        
        with self.assertLogs(level='WARNING'):
            result = load_optional_component(
                "Custom Error Component",
                custom_error_loader,
                error_types=(OSError,)
            )
        
        self.assertIsNone(result)
    
    def test_requires_component_decorator_success(self):
        """Test the requires_component decorator when component exists."""
        class TestClass:
            def __init__(self):
                self.nlp = "mock_nlp_component"
            
            @requires_component('nlp')
            def process(self, text):
                return f"Processed: {text}"
        
        obj = TestClass()
        result = obj.process("test")
        self.assertEqual(result, "Processed: test")
    
    def test_requires_component_decorator_failure(self):
        """Test the requires_component decorator when component is missing."""
        class TestClass:
            def __init__(self):
                self.nlp = None
            
            @requires_component('nlp', "NLP is required")
            def process(self, text):
                return f"Processed: {text}"
        
        obj = TestClass()
        with self.assertRaises(RuntimeError) as context:
            obj.process("test")
        
        self.assertIn("NLP is required", str(context.exception))
    
    @patch('spacy.load')
    def test_get_nlp_model_success(self, mock_spacy_load):
        """Test successful NLP model loading."""
        mock_model = MagicMock()
        mock_spacy_load.return_value = mock_model
        
        result = get_nlp_model("en_core_web_sm")
        
        self.assertEqual(result, mock_model)
        mock_spacy_load.assert_called_once_with("en_core_web_sm", disable=["ner", "textcat"])
    
    @patch('spacy.load')
    def test_get_nlp_model_failure(self, mock_spacy_load):
        """Test NLP model loading failure."""
        mock_spacy_load.side_effect = OSError("Model not found")
        
        with self.assertLogs(level='WARNING') as log:
            result = get_nlp_model("missing_model")
        
        self.assertIsNone(result)
        self.assertTrue(any("spaCy model 'missing_model' not found" in msg for msg in log.output))
    
    @patch('spacy.load')
    def test_get_nlp_model_caching(self, mock_spacy_load):
        """Test that NLP models are cached."""
        mock_model = MagicMock()
        mock_spacy_load.return_value = mock_model
        
        # Load twice
        result1 = get_nlp_model("en_core_web_sm")
        result2 = get_nlp_model("en_core_web_sm")
        
        self.assertEqual(result1, result2)
        # Should only be called once due to caching
        mock_spacy_load.assert_called_once()
    
    @patch('spacy.load')
    def test_spacy_loads_with_disabled_components(self, mock_spacy_load):
        """Test that spaCy loads with NER and textcat disabled for optimization."""
        # Create a mock spaCy model with pipe_names attribute
        mock_model = MagicMock()
        # Simulate the pipeline after disabling ner and textcat
        # Standard en_core_web_sm has: tok2vec, tagger, parser, senter, ner, attribute_ruler, lemmatizer
        # With our disable list, it should have everything except ner and textcat
        mock_model.pipe_names = ['tok2vec', 'tagger', 'parser', 'senter', 'attribute_ruler', 'lemmatizer']
        mock_spacy_load.return_value = mock_model
        
        # Load the model
        nlp = get_nlp_model("en_core_web_sm")
        
        # Verify spacy.load was called with the correct disable parameter
        mock_spacy_load.assert_called_once_with("en_core_web_sm", disable=["ner", "textcat"])
        
        # Verify the loaded model has the expected pipeline
        self.assertIsNotNone(nlp)
        self.assertIn('parser', nlp.pipe_names)  # We need parser for dependency parsing
        self.assertNotIn('ner', nlp.pipe_names)  # NER should be disabled
        self.assertNotIn('textcat', nlp.pipe_names)  # Text categorization should be disabled
    
    def test_optional_component_mixin(self):
        """Test the OptionalComponentMixin class."""
        class TestComponent(OptionalComponentMixin):
            def __init__(self):
                self._init_optional_component(
                    "Test Component",
                    lambda: "loaded_component",
                    "test_attr"
                )
        
        obj = TestComponent()
        self.assertEqual(obj.test_attr, "loaded_component")
    
    def test_optional_component_mixin_required_failure(self):
        """Test OptionalComponentMixin with required component that fails."""
        class TestComponent(OptionalComponentMixin):
            def __init__(self):
                self._init_optional_component(
                    "Required Component",
                    lambda: None,  # Simulates failed loading
                    "required_attr",
                    required=True
                )
        
        with self.assertRaises(RuntimeError) as context:
            TestComponent()
        
        self.assertIn("Required component 'Required Component' could not be loaded", str(context.exception))


class TestIntegration(unittest.TestCase):
    """Test integration with actual RegionAI components."""
    
    def setUp(self):
        """Clear cache before tests."""
        clear_component_cache()
    
    def test_nlp_extractor_with_missing_model(self):
        """Test NLPExtractor handles missing spaCy model gracefully."""
        # Patch at the point of use in NLPExtractor
        with patch('regionai.language.nlp_extractor.get_nlp_model') as mock_get_nlp:
            mock_get_nlp.return_value = None
            
            from tier2.language.nlp_extractor import NLPExtractor
            
            with self.assertRaises(RuntimeError) as context:
                NLPExtractor()
            
            self.assertIn("Failed to load required spaCy model", str(context.exception))
    
    def test_action_discoverer_initialization(self):
        """Test ActionDiscoverer initializes with optional NLP component."""
        from tier3.world_contexts.knowledge.action_discoverer import ActionDiscoverer
        
        # Should not raise even if NLP is not available
        discoverer = ActionDiscoverer()
        self.assertIsNotNone(discoverer)
        self.assertTrue(hasattr(discoverer, 'nlp_model'))
    
    def test_grammar_extractor_with_missing_model(self):
        """Test GrammarPatternExtractor requires spaCy model."""
        # Patch at the module level where it's used
        with patch('regionai.domains.language.grammar_extractor.get_nlp_model') as mock_get_nlp:
            mock_get_nlp.return_value = None
            
            from tier2.domains.language.grammar_extractor import GrammarPatternExtractor
            
            with self.assertRaises(RuntimeError) as context:
                GrammarPatternExtractor()
            
            self.assertIn("Failed to load required spaCy model", str(context.exception))
    
    def test_knowledge_linker_initialization(self):
        """Test KnowledgeLinker initializes with all optional components."""
        from tier2.computer_science.semantic.db import SemanticDB
        from tier3.world_contexts.knowledge.hub import KnowledgeHub
        from tier3.world_contexts.knowledge.linker import KnowledgeLinker
        
        db = SemanticDB()
        hub = KnowledgeHub()
        
        # Should not raise even if optional components fail
        linker = KnowledgeLinker(db, hub)
        self.assertIsNotNone(linker)
        self.assertTrue(hasattr(linker, 'nlp_model'))


def run_all_tests():
    """Run all component loader tests."""
    print("=" * 60)
    print("Component Loader Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestComponentLoader))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ All tests passed!")
        print("Component loading is now standardized across RegionAI.")
    else:
        print(f"✗ {len(result.failures)} tests failed")
        print(f"✗ {len(result.errors)} tests had errors")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)