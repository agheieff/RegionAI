"""
Tests for custom domain exceptions.
"""

from regionai.knowledge.exceptions import (
    RegionAIException,
    ExponentialSearchException,
    ProofTimeoutException,
    InvalidProofStateException,
    HeuristicFailureException,
    ResourceExhaustionException,
    ConfigurationException,
    DiscoveryException,
    AbstractInterpretationException,
    LanguageParsingException
)


class TestRegionAIException:
    """Test the base RegionAI exception."""
    
    def test_base_exception(self):
        """Test creating base exception."""
        exc = RegionAIException("Test error")
        assert str(exc) == "Test error"
        assert isinstance(exc, Exception)


class TestExponentialSearchException:
    """Test the ExponentialSearchException."""
    
    def test_basic_creation(self):
        """Test creating exponential search exception."""
        exc = ExponentialSearchException("Search space exploded")
        assert str(exc) == "Search space exploded"
        assert exc.elapsed_time == 0.0
        assert exc.steps_taken == 0
        assert exc.context == {}
    
    def test_with_details(self):
        """Test exception with full details."""
        context = {"current_heuristic": "breadth_first", "depth": 100}
        exc = ExponentialSearchException(
            "Exponential growth detected",
            elapsed_time=125.5,
            steps_taken=50000,
            context=context
        )
        
        assert exc.elapsed_time == 125.5
        assert exc.steps_taken == 50000
        assert exc.context == context
        
        # Check string representation includes details
        exc_str = str(exc)
        assert "Exponential growth detected" in exc_str
        assert "Elapsed time: 125.50s" in exc_str
        assert "Steps taken: 50000" in exc_str
        assert "Context:" in exc_str
        assert "breadth_first" in exc_str
    
    def test_partial_details(self):
        """Test exception with partial details."""
        exc = ExponentialSearchException(
            "Partial failure",
            steps_taken=1000
        )
        
        exc_str = str(exc)
        assert "Steps taken: 1000" in exc_str
        assert "Elapsed time:" not in exc_str  # Not included when 0


class TestProofTimeoutException:
    """Test the ProofTimeoutException."""
    
    def test_creation(self):
        """Test creating proof timeout exception."""
        exc = ProofTimeoutException(
            "Proof attempt timed out",
            timeout_limit=600.0,
            actual_time=605.3
        )
        
        assert exc.timeout_limit == 600.0
        assert exc.actual_time == 605.3
        
        exc_str = str(exc)
        assert "Proof attempt timed out" in exc_str
        assert "(limit: 600.0s, actual: 605.30s)" in exc_str


class TestInvalidProofStateException:
    """Test the InvalidProofStateException."""
    
    def test_creation(self):
        """Test creating invalid proof state exception."""
        exc = InvalidProofStateException("Malformed goal: missing type")
        assert str(exc) == "Malformed goal: missing type"
        assert isinstance(exc, RegionAIException)


class TestHeuristicFailureException:
    """Test the HeuristicFailureException."""
    
    def test_creation(self):
        """Test creating heuristic failure exception."""
        exc = HeuristicFailureException(
            heuristic_name="depth_first_search",
            message="Stack overflow in recursive call"
        )
        
        assert exc.heuristic_name == "depth_first_search"
        
        exc_str = str(exc)
        assert "Heuristic 'depth_first_search' failed:" in exc_str
        assert "Stack overflow in recursive call" in exc_str


class TestResourceExhaustionException:
    """Test the ResourceExhaustionException."""
    
    def test_creation(self):
        """Test creating resource exhaustion exception."""
        exc = ResourceExhaustionException(
            resource_type="memory",
            message="Heap allocation failed"
        )
        
        assert exc.resource_type == "memory"
        
        exc_str = str(exc)
        assert "Resource exhaustion (memory):" in exc_str
        assert "Heap allocation failed" in exc_str


class TestOtherExceptions:
    """Test the remaining exception types."""
    
    def test_configuration_exception(self):
        """Test ConfigurationException."""
        exc = ConfigurationException("Invalid timeout value: -1")
        assert str(exc) == "Invalid timeout value: -1"
        assert isinstance(exc, RegionAIException)
    
    def test_discovery_exception(self):
        """Test DiscoveryException."""
        exc = DiscoveryException("No patterns found in dataset")
        assert str(exc) == "No patterns found in dataset"
        assert isinstance(exc, RegionAIException)
    
    def test_abstract_interpretation_exception(self):
        """Test AbstractInterpretationException."""
        exc = AbstractInterpretationException("Widening operator failed to converge")
        assert str(exc) == "Widening operator failed to converge"
        assert isinstance(exc, RegionAIException)
    
    def test_language_parsing_exception(self):
        """Test LanguageParsingException."""
        exc = LanguageParsingException("Ambiguous parse: 3 interpretations")
        assert str(exc) == "Ambiguous parse: 3 interpretations"
        assert isinstance(exc, RegionAIException)


class TestExceptionHierarchy:
    """Test that exception hierarchy is correct."""
    
    def test_all_inherit_from_base(self):
        """Test that all exceptions inherit from RegionAIException."""
        exceptions = [
            ExponentialSearchException("test"),
            ProofTimeoutException("test", 1.0, 2.0),
            InvalidProofStateException("test"),
            HeuristicFailureException("h", "test"),
            ResourceExhaustionException("r", "test"),
            ConfigurationException("test"),
            DiscoveryException("test"),
            AbstractInterpretationException("test"),
            LanguageParsingException("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, RegionAIException)
            assert isinstance(exc, Exception)