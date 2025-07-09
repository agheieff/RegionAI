# RegionAI

Region-based embeddings for language models - representing concepts as bounded volumes instead of points

## Overview

RegionAI is an innovative framework that reimagines how we represent concepts in embedding spaces. Instead of representing concepts as single points, RegionAI uses bounded regions (boxes) where containment represents hierarchical relationships. This enables intuitive visualization and reasoning about concept hierarchies.

### Key Features

- **Region-based representations**: Concepts are volumes, not points
- **Interactive visualization**: Real-time selection and exploration of concept hierarchies
- **Pathfinding**: Find and visualize logical paths between concepts
- **Visual feedback**: Parent/child relationships shown with colors and line styles
- **GPU-ready**: Built on PyTorch for scalability

## Installation

```bash
# Clone the repository
git clone https://github.com/agheieff/RegionAI.git
cd RegionAI

# Install dependencies with Poetry
poetry install

# Run interactive demos
poetry run python scripts/demo_day10.py
```

## Architecture

The project follows a clean, modular architecture:

- **geometry/**: Core geometric primitives (Box2D with PyTorch tensors)
- **spaces/**: Concept space implementations for managing named regions
- **engine/**: Reasoning engines including pathfinding algorithms
- **visualization/**: Interactive plotting with matplotlib event handling

## Interactive Features

### Mouse Controls
- **Left-click**: Select a region (highlights in red, shows parents/children)
- **Right-click**: Initiate pathfinding
  - First click: Sets start point (purple)
  - Second click: Finds and displays path (orange)
- **C key**: Clear all selections

### Visual Feedback
- **Selected region**: Red with solid border
- **Parent regions**: Light blue with dashed border
- **Child regions**: Light green with dotted border
- **Pathfinding start**: Purple with dashed border
- **Found path**: Orange with thick borders

## Example Usage

```python
from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.visualization.interactive_plotter import InteractivePlotter

# Create a concept hierarchy
space = ConceptSpace2D()
space.add_region("ENTITY", Box2D(0, 0, 100, 100))
space.add_region("ANIMAL", Box2D(10, 10, 90, 90))
space.add_region("MAMMAL", Box2D(20, 20, 80, 80))
space.add_region("CAT", Box2D(30, 30, 50, 50))
space.add_region("SIAMESE", Box2D(35, 35, 45, 45))

# Launch interactive visualization
plotter = InteractivePlotter(space)
plotter.show()

# Try: Right-click SIAMESE, then right-click ENTITY to see the path!
```

## Pathfinding Algorithm

RegionAI uses a Breadth-First Search (BFS) algorithm to find the shortest hierarchical path between concepts. The pathfinding follows parent-child relationships where:
- A region can navigate to its parent (the smallest region that contains it)
- Paths represent "is-a" relationships in the concept hierarchy
- Example: SIAMESE → CAT → MAMMAL → ANIMAL → ENTITY

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run ruff format .

# Lint code
poetry run ruff check .

# Run specific demo
poetry run python scripts/test_interactive_pathfinding.py
```

## License

MIT