# Curriculum Migration Guide

## Overview
All curriculum generators have been unified into a single factory pattern, reducing ~800 lines of repetitive code while maintaining all functionality.

## Migration Examples

### Basic Usage

#### Old Way (Multiple Classes)
```python
from regionai.data.sign_curriculum import SignAnalysisCurriculumGenerator
from regionai.data.nullability_curriculum import NullabilityCurriculumGenerator

# Create generators
sign_gen = SignAnalysisCurriculumGenerator()
null_gen = NullabilityCurriculumGenerator()

# Generate problems
sign_problems = sign_gen.generate_basic_sign_curriculum()
null_problems = null_gen.generate_basic_nullability_curriculum()
```

#### New Way (Unified Factory)
```python
from regionai.data import create_curriculum

# Generate problems with factory
sign_problems = create_curriculum('sign_analysis', difficulty='basic')
null_problems = create_curriculum('nullability', difficulty='basic')
```

### Advanced Usage

#### Custom Configuration
```python
from regionai.data import CurriculumFactory, CurriculumConfig

factory = CurriculumFactory()

# With custom config
config = CurriculumConfig(
    difficulty='advanced',
    num_problems=10,
    seed=42,
    extra_params={'focus': 'loops'}
)

problems = factory.create('loop_analysis', config.__dict__)
```

#### Mixed Curricula
```python
from regionai.data import create_mixed_curriculum

# Create mixed curriculum
mixed_problems = create_mixed_curriculum([
    ('sign_analysis', {'difficulty': 'basic', 'num_problems': 5}),
    ('nullability', {'difficulty': 'intermediate', 'num_problems': 3}),
    ('loop_analysis', {'difficulty': 'basic', 'num_problems': 2})
])
```

#### Custom Curriculum Generator
```python
from regionai.data import CurriculumGenerator, CurriculumFactory

class MyCustomCurriculum(CurriculumGenerator):
    name = "custom"
    description = "My custom curriculum"
    
    def generate(self, config):
        # Custom generation logic
        return [Problem(...)]

# Register with factory
factory = CurriculumFactory()
factory.register_generator('custom', MyCustomCurriculum())

# Use it
problems = factory.create('custom')
```

## Available Curriculum Types

Use `list_curricula()` to see all available types:

```python
from regionai.data import list_curricula

curricula = list_curricula()
# {
#     'transformation': 'Basic transformation discovery (ADD, MULTIPLY, etc.)',
#     'sign_analysis': 'Abstract sign analysis and property proving',
#     'nullability': 'Null pointer detection and safety analysis',
#     'range_analysis': 'Array bounds checking and range analysis',
#     'loop_analysis': 'Loop termination and fixpoint analysis',
#     'conditional': 'IF-THEN-ELSE transformation patterns',
#     'iterative': 'FOR-EACH loops with transformations',
#     'ast_optimization': 'Code optimization through AST transformation',
#     'interprocedural': 'Whole-program analysis across functions'
# }
```

## Difficulty Levels

Most curricula support three difficulty levels:
- `'basic'`: Simple, foundational problems
- `'intermediate'`: More complex scenarios
- `'advanced'`: Challenging problems requiring sophisticated analysis

## Backward Compatibility

The old curriculum classes still work but show deprecation warnings:

```python
# This still works but shows a warning
from regionai.data import SignAnalysisCurriculumGenerator
gen = SignAnalysisCurriculumGenerator()
problems = gen.generate_basic_sign_curriculum()
```

## Benefits of New Approach

1. **Single Interface**: One factory for all curriculum types
2. **Consistent API**: Same method for all problem generation
3. **Easy Extension**: Add new curricula by implementing CurriculumGenerator
4. **Configuration**: Unified configuration system
5. **Less Code**: ~800 lines reduced through eliminating duplication

## Full Example

```python
from regionai.data import CurriculumFactory, create_curriculum, list_curricula

# List available curricula
print("Available curricula:")
for name, desc in list_curricula().items():
    print(f"  {name}: {desc}")

# Create problems
basic_sign = create_curriculum('sign_analysis', difficulty='basic')
advanced_null = create_curriculum('nullability', difficulty='advanced', num_problems=5)

# Or use factory directly
factory = CurriculumFactory()
loop_problems = factory.create('loop_analysis', {'difficulty': 'intermediate'})

# Mixed curriculum
mixed = factory.create_mixed([
    ('transformation', {'difficulty': 'basic'}),
    ('ast_optimization', {'difficulty': 'intermediate'})
])

print(f"\nGenerated {len(mixed)} problems from mixed curriculum")
```