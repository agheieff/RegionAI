"""
Centralized component loading utilities for RegionAI.

This module provides standardized mechanisms for loading optional components
like spaCy models, ensuring consistent error handling and initialization
patterns across the codebase.
"""
import logging
from typing import Optional, TypeVar, Callable, Any, Dict
from functools import wraps, lru_cache
import warnings

# Type variable for generic component loading
T = TypeVar('T')

# Global cache for loaded components
_component_cache: Dict[str, Any] = {}


def load_optional_component(
    component_name: str,
    loader_func: Callable[[], T],
    error_types: tuple = (ImportError, OSError),
    warning_message: Optional[str] = None,
    fallback_value: Optional[T] = None,
    cache_key: Optional[str] = None
) -> Optional[T]:
    """
    Load an optional component with standardized error handling.
    
    This function provides a consistent way to load optional dependencies
    across the RegionAI codebase, handling import errors gracefully and
    providing clear logging.
    
    Args:
        component_name: Name of the component for logging
        loader_func: Function that loads and returns the component
        error_types: Tuple of exception types to catch
        warning_message: Custom warning message (if None, a default is used)
        fallback_value: Value to return if loading fails
        cache_key: If provided, cache the loaded component
        
    Returns:
        The loaded component or fallback_value if loading fails
        
    Example:
        >>> nlp = load_optional_component(
        ...     "spaCy English model",
        ...     lambda: spacy.load("en_core_web_sm"),
        ...     warning_message="spaCy model not found. NLP features will be limited."
        ... )
    """
    logger = logging.getLogger(__name__)
    
    # Check cache first
    if cache_key and cache_key in _component_cache:
        return _component_cache[cache_key]
    
    try:
        component = loader_func()
        
        # Cache if requested
        if cache_key:
            _component_cache[cache_key] = component
            
        logger.debug(f"Successfully loaded {component_name}")
        return component
        
    except error_types as e:
        if warning_message is None:
            warning_message = (
                f"Failed to load {component_name}: {str(e)}. "
                f"This feature will be disabled."
            )
        
        logger.warning(warning_message)
        
        # Also use warnings module for better visibility in some environments
        warnings.warn(warning_message, RuntimeWarning, stacklevel=2)
        
        return fallback_value


def requires_component(component_attr: str, error_message: Optional[str] = None):
    """
    Decorator that checks if a required component is available before executing a method.
    
    Args:
        component_attr: Name of the instance attribute containing the component
        error_message: Custom error message if component is not available
        
    Example:
        >>> class MyClass:
        ...     def __init__(self):
        ...         self.nlp = load_optional_component(...)
        ...     
        ...     @requires_component('nlp', "spaCy is required for this operation")
        ...     def process_text(self, text):
        ...         return self.nlp(text)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            component = getattr(self, component_attr, None)
            if component is None:
                if error_message is None:
                    msg = f"{component_attr} is required for {func.__name__} but was not loaded"
                else:
                    msg = error_message
                raise RuntimeError(msg)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


@lru_cache(maxsize=1)
def get_nlp_model(model_name: str = "en_core_web_sm"):
    """
    Get or create a cached spaCy NLP model instance.
    
    This function ensures that the spaCy model is loaded only once and
    reused across all components that need it.
    
    Args:
        model_name: Name of the spaCy model to load
        
    Returns:
        Loaded spaCy model or None if loading fails
        
    Note:
        The @lru_cache decorator ensures the model is loaded only once
        per model_name, providing singleton-like behavior within a process.
        For multi-process environments, consider using get_nlp_model_for_multiprocessing.
    """
    def loader():
        import spacy
        return spacy.load(model_name, disable=["ner", "textcat"])
    
    return load_optional_component(
        f"spaCy model '{model_name}'",
        loader,
        error_types=(ImportError, OSError),
        warning_message=(
            f"spaCy model '{model_name}' not found. "
            f"Please install it with: python -m spacy download {model_name}"
        )
    )


def get_nlp_model_for_multiprocessing(model_name: str = "en_core_web_sm", preloaded_model=None):
    """
    Get NLP model optimized for multiprocessing environments.
    
    In multiprocessing scenarios, the main process should load the model once
    and pass it to worker processes to avoid redundant loading.
    
    Args:
        model_name: Name of the spaCy model to load (if preloaded_model is None)
        preloaded_model: Pre-loaded model instance to use (for worker processes)
        
    Returns:
        The preloaded model if provided, otherwise loads and returns the model
        
    Example:
        # In main process:
        nlp_model = get_nlp_model_for_multiprocessing()
        
        # Pass to workers:
        with ProcessPoolExecutor() as executor:
            future = executor.submit(worker_func, nlp_model)
    """
    if preloaded_model is not None:
        return preloaded_model
    
    # If no preloaded model, load it (useful for main process)
    return get_nlp_model(model_name)


class OptionalComponentMixin:
    """
    Mixin class providing standardized initialization for optional components.
    
    Classes that use optional dependencies can inherit from this mixin
    to get consistent initialization and error handling patterns.
    """
    
    def _init_optional_component(
        self,
        component_name: str,
        loader_func: Callable[[], Any],
        attr_name: str,
        required: bool = False,
        **kwargs
    ):
        """
        Initialize an optional component with standardized error handling.
        
        Args:
            component_name: Name of the component for logging
            loader_func: Function that loads and returns the component
            attr_name: Name of the attribute to set on self
            required: If True, raise exception on failure instead of warning
            **kwargs: Additional arguments passed to load_optional_component
        """
        component = load_optional_component(
            component_name,
            loader_func,
            **kwargs
        )
        
        if required and component is None:
            raise RuntimeError(
                f"Required component '{component_name}' could not be loaded. "
                f"Please check your installation."
            )
        
        setattr(self, attr_name, component)


def clear_component_cache():
    """Clear the global component cache."""
    _component_cache.clear()
    get_nlp_model.cache_clear()


def preload_nlp_for_workers(model_name: str = "en_core_web_sm"):
    """
    Preload NLP model in the main process for distribution to workers.
    
    This function should be called in the main process before creating
    worker processes to ensure the model is loaded only once.
    
    Args:
        model_name: Name of the spaCy model to load
        
    Returns:
        The loaded model instance, ready to be passed to workers
        
    Example:
        # In analyze_codebase.py or similar:
        nlp_model = preload_nlp_for_workers()
        
        with ProcessPoolExecutor() as executor:
            # Pass nlp_model to worker functions that need it
            futures = []
            for data in work_items:
                future = executor.submit(process_with_nlp, data, nlp_model)
                futures.append(future)
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Preloading NLP model '{model_name}' for multiprocessing...")
    
    model = get_nlp_model(model_name)
    
    if model is not None:
        logger.info("NLP model preloaded successfully")
    else:
        logger.warning("Failed to preload NLP model")
    
    return model