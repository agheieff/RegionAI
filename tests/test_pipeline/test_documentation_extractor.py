"""
Test suite for the Documentation Extractor.

Tests the extraction of natural language context from functions,
which forms the foundation for the Language Bridge.
"""
import ast
import pytest

from src.regionai.pipeline.documentation_extractor import (
    DocumentationExtractor, CommentExtractor, AdvancedDocumentationExtractor,
    DocumentationAnalyzer
)
from src.regionai.semantic.fingerprint import (
    NaturalLanguageContext, DocumentedFingerprint, DocumentationQuality
)
from src.regionai.pipeline.api import analyze_code


class TestDocumentationExtractor:
    """Test basic documentation extraction functionality."""
    
    def test_extract_simple_docstring(self):
        """Test extraction of a simple docstring."""
        code = '''
def add(a, b):
    """Add two numbers together."""
    return a + b
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        extractor = DocumentationExtractor()
        context = extractor.extract(func_node)
        
        assert context.function_name == "add"
        assert context.docstring == "Add two numbers together."
        assert context.parameter_names == ["a", "b"]
        assert context.return_description is None
    
    def test_extract_detailed_docstring(self):
        """Test extraction of a detailed docstring with return description."""
        code = '''
def calculate_interest(principal, rate, time):
    """
    Calculate compound interest.
    
    This function computes the compound interest based on the principal amount,
    interest rate, and time period.
    
    Args:
        principal: The initial amount of money
        rate: The annual interest rate (as a decimal)
        time: The time period in years
        
    Returns:
        The total amount after compound interest
    """
    return principal * (1 + rate) ** time
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        extractor = DocumentationExtractor()
        context = extractor.extract(func_node)
        
        assert context.function_name == "calculate_interest"
        assert "Calculate compound interest" in context.docstring
        assert context.parameter_names == ["principal", "rate", "time"]
        assert context.return_description is not None
        assert "total amount" in context.return_description.lower()
    
    def test_extract_no_docstring(self):
        """Test extraction from function without docstring."""
        code = '''
def multiply(x, y):
    return x * y
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        extractor = DocumentationExtractor()
        context = extractor.extract(func_node)
        
        assert context.function_name == "multiply"
        assert context.docstring is None
        assert context.parameter_names == ["x", "y"]
        assert not context.has_documentation()
    
    def test_extract_variable_names(self):
        """Test extraction of variable names from function body."""
        code = '''
def process_data(input_data):
    """Process the input data."""
    cleaned_data = clean(input_data)
    processed_result = transform(cleaned_data)
    return processed_result
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        extractor = DocumentationExtractor()
        context = extractor.extract(func_node)
        
        assert "cleaned_data" in context.variable_names
        assert "processed_result" in context.variable_names
    
    def test_extract_return_patterns(self):
        """Test extraction of different return description patterns."""
        test_cases = [
            ('def f(): """Returns: An integer value."""', "An integer value."),
            ('def f(): """Return the sum of inputs."""', "the sum of inputs."),
            ('def f(): """@return boolean value"""', "boolean value"),
        ]
        
        extractor = DocumentationExtractor()
        
        for code, expected in test_cases:
            tree = ast.parse(code)
            func_node = tree.body[0]
            context = extractor.extract(func_node)
            
            assert context.return_description is not None
            assert expected in context.return_description


class TestCommentExtractor:
    """Test comment extraction from source code."""
    
    def test_extract_function_comments(self):
        """Test extraction of comments within a function."""
        source_code = '''
def example_function(data):
    """Process some data."""
    # Validate input
    if not data:
        return None
    
    # Perform transformation
    result = data * 2  # Double the value
    
    # Return processed result
    return result
'''
        comments = CommentExtractor.extract_function_comments(source_code, "example_function")
        
        assert "Validate input" in comments
        assert "Perform transformation" in comments
        assert "Double the value" in comments
        assert "Return processed result" in comments
    
    def test_extract_no_comments(self):
        """Test extraction when function has no comments."""
        source_code = '''
def simple_function(x):
    return x + 1
'''
        comments = CommentExtractor.extract_function_comments(source_code, "simple_function")
        assert len(comments) == 0
    
    def test_extract_nonexistent_function(self):
        """Test extraction for function that doesn't exist."""
        source_code = '''
def real_function():
    pass
'''
        comments = CommentExtractor.extract_function_comments(source_code, "fake_function")
        assert len(comments) == 0


class TestAdvancedDocumentationExtractor:
    """Test the advanced documentation extractor."""
    
    def test_extract_with_source_code(self):
        """Test extraction with both AST and source code analysis."""
        source_code = '''
def well_documented_function(items):
    """
    Process a list of items.
    
    Returns: Processed items
    """
    # Initialize result list
    result = []
    
    # Process each item
    for item in items:
        # Apply transformation
        processed = item.upper()
        result.append(processed)
    
    return result
'''
        tree = ast.parse(source_code)
        func_node = tree.body[0]
        
        extractor = AdvancedDocumentationExtractor()
        context = extractor.extract_from_function(func_node, source_code)
        
        # Should have docstring
        assert "Process a list of items" in context.docstring
        
        # Should have return description
        assert context.return_description == "Processed items"
        
        # Should have comments
        assert "Initialize result list" in context.comments
        assert "Process each item" in context.comments
        assert "Apply transformation" in context.comments
        
        # Should have variables
        assert "result" in context.variable_names
        assert "processed" in context.variable_names
    
    def test_extract_from_module(self):
        """Test extraction from entire module."""
        source_code = '''
def function_one():
    """First function."""
    pass

def function_two(param):
    """
    Second function.
    
    Returns: Something useful
    """
    # Do something
    return param * 2

class SomeClass:
    def method(self):
        """A method."""
        pass
'''
        tree = ast.parse(source_code)
        extractor = AdvancedDocumentationExtractor()
        contexts = extractor.extract_from_module(tree, source_code)
        
        # Should find all functions (including methods)
        assert "function_one" in contexts
        assert "function_two" in contexts
        assert "method" in contexts
        
        # Check specific extractions
        assert contexts["function_one"].docstring == "First function."
        assert contexts["function_two"].return_description == "Something useful"
        assert "Do something" in contexts["function_two"].comments


class TestDocumentationAnalyzer:
    """Test documentation analysis utilities."""
    
    def test_analyze_vocabulary(self):
        """Test vocabulary analysis across multiple functions."""
        contexts = [
            NaturalLanguageContext(
                function_name="func1",
                docstring="Calculate the sum of numbers",
                parameter_names=["numbers"]
            ),
            NaturalLanguageContext(
                function_name="func2", 
                docstring="Calculate the average of values",
                parameter_names=["values"]
            ),
            NaturalLanguageContext(
                function_name="func3",
                docstring="Sort the list of items",
                parameter_names=["items"]
            )
        ]
        
        vocab = DocumentationAnalyzer.analyze_vocabulary(contexts)
        
        # "calculate" should appear twice
        assert vocab.get("calculate", 0) == 2
        # "the" should appear multiple times
        assert vocab.get("the", 0) >= 3
    
    def test_find_common_patterns(self):
        """Test finding common documentation patterns."""
        contexts = [
            NaturalLanguageContext(
                function_name="is_valid",
                docstring="Check if the input is valid. Returns true if valid.",
                parameter_names=["input"]
            ),
            NaturalLanguageContext(
                function_name="compute_total",
                docstring="Calculate the total sum of all values.",
                parameter_names=["values"]
            ),
            NaturalLanguageContext(
                function_name="update_record",
                docstring="Modify the database record with new data.",
                parameter_names=["record", "data"]
            ),
        ]
        
        patterns = DocumentationAnalyzer.find_common_patterns(contexts)
        
        assert "is_valid" in patterns["returns_boolean"]
        assert "compute_total" in patterns["performs_calculation"]
        assert "update_record" in patterns["modifies_state"]
    
    def test_get_training_candidates(self):
        """Test identification of good training candidates."""
        contexts = [
            NaturalLanguageContext(
                function_name="well_documented",
                docstring="This is a well-documented function that does something meaningful.",
                parameter_names=["meaningful_param"]
            ),
            NaturalLanguageContext(
                function_name="poorly_doc",
                docstring="Bad.",
                parameter_names=["x"]
            ),
            NaturalLanguageContext(
                function_name="no_doc",
                docstring=None,
                parameter_names=["param"]
            ),
        ]
        
        candidates = DocumentationAnalyzer.get_training_candidates(contexts)
        
        assert "well_documented" in candidates
        assert "poorly_doc" not in candidates
        assert "no_doc" not in candidates


class TestDocumentationQuality:
    """Test documentation quality assessment."""
    
    def test_score_high_quality_documentation(self):
        """Test scoring of high-quality documentation."""
        context = NaturalLanguageContext(
            function_name="well_documented_function",
            docstring="This function processes user input data and validates it according to business rules. Returns the processed data.",
            parameter_names=["user_input", "validation_rules"],
            comments=["Validate format", "Apply business logic"]
        )
        
        score = DocumentationQuality.score_documentation(context)
        assert score > 0.7  # Should be high quality
    
    def test_score_poor_quality_documentation(self):
        """Test scoring of poor-quality documentation."""
        context = NaturalLanguageContext(
            function_name="f",
            docstring="Does stuff.",
            parameter_names=["x", "y"]
        )
        
        score = DocumentationQuality.score_documentation(context)
        assert score < 0.5  # Should be low quality
    
    def test_is_suitable_for_training(self):
        """Test training suitability assessment."""
        from src.regionai.semantic.fingerprint import SemanticFingerprint, Behavior
        
        # Good training candidate
        good_context = NaturalLanguageContext(
            function_name="calculate_tax",
            docstring="Calculate tax amount based on income and rate. Returns the tax owed.",
            parameter_names=["income", "tax_rate"]
        )
        good_fp = SemanticFingerprint(behaviors={Behavior.PURE, Behavior.VALIDATOR})
        good_doc_fp = DocumentedFingerprint(fingerprint=good_fp, nl_context=good_context)
        
        assert DocumentationQuality.is_suitable_for_training(good_doc_fp)
        
        # Poor candidate - no behaviors
        poor_fp = SemanticFingerprint(behaviors=set())
        poor_doc_fp = DocumentedFingerprint(fingerprint=poor_fp, nl_context=good_context)
        
        assert not DocumentationQuality.is_suitable_for_training(poor_doc_fp)


class TestIntegrationWithAnalysisPipeline:
    """Test integration of documentation extraction with the analysis pipeline."""
    
    def test_documented_fingerprints_generated(self):
        """Test that documented fingerprints are generated during analysis."""
        code = '''
def identity_function(value):
    """
    Return the input value unchanged.
    
    Args:
        value: The input value to return
        
    Returns:
        The same value that was passed in
    """
    return value

def add_numbers(a, b):
    """Add two numbers together."""
    return a + b

def undocumented_function(x):
    return x * 2
'''
        result = analyze_code(code, include_source=True)
        
        # Should have documented fingerprints
        assert result.documented_fingerprints is not None
        assert len(result.documented_fingerprints) >= 2
        
        # Check specific functions
        documented_funcs = [
            df.nl_context.function_name 
            for df in result.documented_fingerprints.values()
        ]
        
        assert "identity_function" in documented_funcs
        assert "add_numbers" in documented_funcs
        assert "undocumented_function" in documented_funcs  # Should still be extracted
    
    def test_semantic_db_with_documentation(self):
        """Test that SemanticDB includes documentation information."""
        code = '''
def pure_function(x, y):
    """
    A pure function that adds two numbers.
    
    Returns: The sum of x and y
    """
    return x + y

def impure_function(data):
    """Print and return data."""
    print(data)  # Side effect
    return data
'''
        result = analyze_code(code, include_source=True)
        db = result.semantic_db
        
        # Find documented functions
        documented = db.find_documented_functions()
        assert len(documented) >= 2
        
        # Check documentation statistics
        stats = db.get_documentation_statistics()
        assert stats['documented_functions'] >= 2
        assert stats['total_functions'] >= 2
        
        # Find by documentation pattern
        pure_funcs = db.find_by_documentation_pattern("pure function")
        assert len(pure_funcs) >= 1
        
        # Create training dataset
        dataset = db.create_language_training_dataset()
        assert len(dataset) >= 0  # May be empty if quality is too low
        
        for doc, semantic in dataset:
            assert isinstance(doc, str)
            assert isinstance(semantic, str)
            assert len(doc) > 0
            assert len(semantic) > 0
    
    def test_documentation_without_source_code(self):
        """Test that analysis works without source code (AST-only)."""
        code = '''
def documented_function(param):
    """A function with documentation."""
    return param
'''
        result = analyze_code(code, include_source=False)
        
        # Should still extract docstrings
        assert result.documented_fingerprints is not None
        assert len(result.documented_fingerprints) >= 1
        
        # But comments should be empty since no source code was provided
        for doc_fp in result.documented_fingerprints.values():
            assert len(doc_fp.nl_context.comments) == 0