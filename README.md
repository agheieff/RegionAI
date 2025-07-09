# RegionAI

Region-based embeddings for language models

## Overview

RegionAI is an interactive 2D/3D application that visually represents concept boxes and tests their geometric relationships in real-time. It provides a framework for understanding hierarchical relationships between concepts using spatial representations.

## Installation

```bash
# Clone the repository
git clone https://github.com/agheieff/RegionAI.git
cd RegionAI

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

## Architecture

The project follows a modular architecture with clear separation of concerns:

- **core/**: Core interfaces and base classes (Region, ConceptSpace protocols)
- **geometry/**: Geometric operations (Box2D, Box3D, BoxND implementations)
- **spaces/**: Concept space implementations for managing collections of regions
- **visualization/**: All plotting and UI code, including event management
- **config/**: Configuration management and settings

## Example Usage

```python
from regionai.geometry import Box2D
from regionai.spaces import ConceptSpace2D
from regionai.visualization import InteractivePlotter

# Create a concept space
space = ConceptSpace2D()

# Define hierarchical concepts
space.add_region("thing", Box2D(0, 0, 10, 10))
space.add_region("animal", Box2D(1, 1, 8, 8))
space.add_region("mammal", Box2D(2, 2, 6, 6))
space.add_region("cat", Box2D(3, 3, 4, 4))

# Visualize interactively
plotter = InteractivePlotter(space)
plotter.show()
```

## Development Guidelines

1. **Dependency Injection**: Pass dependencies explicitly, don't hardcode
2. **Protocol-Based Design**: Use Python protocols for interfaces
3. **Event-Driven Updates**: Changes propagate through events, not direct calls
4. **Configurable Everything**: Colors, sizes, behaviors in config files

## Testing

```bash
pytest tests/
```

## License

MIT