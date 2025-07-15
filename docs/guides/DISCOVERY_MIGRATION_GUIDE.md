# Discovery Module Migration Guide

## Overview
The discovery modules have been unified into a single, strategy-based discovery engine. This reduces code duplication and provides a cleaner, more extensible architecture.

## Changes

### Before (Multiple Files)
```python
# Using different discovery modules
from regionai.discovery.discover import discover_concept_from_failures
from regionai.discovery.discover_conditional import discover_conditional_concept
from regionai.discovery.discover_iterative import discover_iterative_concept

# Each with different interfaces
result1 = discover_concept_from_failures(problems)
result2 = discover_conditional_concept(problems, params)
result3 = discover_iterative_concept(problems, max_depth=5)
```

### After (Unified Engine)
```python
# Single unified interface
from regionai.discovery import UnifiedDiscoveryEngine

engine = UnifiedDiscoveryEngine()

# Try all strategies automatically
result = engine.discover(problems)

# Or use specific strategy
result = engine.discover(problems, strategy='conditional')
```

## Migration Steps

### 1. Basic Usage (Recommended)
```python
# Old
from regionai.discovery.discover import discover_concept_from_failures
concept = discover_concept_from_failures(failed_problems)

# New
from regionai.discovery import UnifiedDiscoveryEngine
engine = UnifiedDiscoveryEngine()
concept = engine.discover(failed_problems)
```

### 2. Strategy-Specific Discovery
```python
# Old - different modules
from regionai.discovery.discover_conditional import discover_conditional
result = discover_conditional(problems)

# New - unified with strategy parameter
engine = UnifiedDiscoveryEngine()
result = engine.discover(problems, strategy='conditional')
```

### 3. Custom Parameters
```python
# Old
result = discover_with_params(problems, max_depth=5, params=custom_params)

# New
engine = UnifiedDiscoveryEngine()
# Note: max_search_depth would need to be configured in strategies
result = engine.discover(problems)
```

### 4. Adding Custom Strategies
```python
from regionai.discovery.strategies.base import DiscoveryStrategy

class MyCustomStrategy(DiscoveryStrategy):
    def discover(self, problems):
        # Custom discovery logic
        pass

engine = UnifiedDiscoveryEngine()
engine.strategies['custom'] = MyCustomStrategy()
result = engine.discover(problems, strategy='custom')
```

## Benefits

1. **Unified Interface**: Single entry point for all discovery types
2. **Extensible**: Easy to add new discovery strategies
3. **Configurable**: Control strategy order and parameters
4. **Backward Compatible**: Legacy functions still work with deprecation warnings
5. **Less Code**: ~500 lines removed through consolidation

## Strategy Types

- **`sequential`**: Basic composition of primitive operations
- **`conditional`**: IF-THEN-ELSE patterns
- **`iterative`**: FOR-EACH loops with nested conditionals

## Advanced Usage

### Custom Strategy Order
```python
engine = DiscoveryEngine()
# Try conditional first, then iterative, then sequential
engine.set_strategy_order(['conditional', 'iterative', 'sequential'])
```

### Direct Strategy Access
```python
from regionai.discovery.discovery_engine import ConditionalDiscovery

strategy = ConditionalDiscovery(max_depth=5)
result = strategy.discover(problems)
```

## Deprecation Timeline

- Legacy functions will show deprecation warnings immediately
- Full removal planned for version 2.0
- Update your code to use the new DiscoveryEngine class