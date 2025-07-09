# RegionAI

## Project Overview

RegionAI is a Python library for creating, managing, and visualizing N-dimensional hierarchical concept spaces. It provides a way to represent concepts as N-dimensional regions and to reason about their relationships, such as containment and overlap. The library also includes a powerful interactive visualization tool for exploring these concept spaces in 2D projections.

The core idea is to use geometric regions (hyperrectangles) to represent concepts, where the volume and position of a region correspond to its specificity and relationship to other concepts. For example, a small region for "cat" might be contained within a larger region for "mammal," which in turn is contained within "animal." This allows for a geometric interpretation of semantic hierarchies.

## Features

*   **N-Dimensional Concept Spaces**: Create concept spaces with any number of dimensions.
*   **Dimension-Agnostic Geometry**: All geometric operations (containment, overlap, union, intersection) work in any number of dimensions.
*   **Hierarchical Reasoning**: Automatically determines parent-child relationships between concepts based on geometric containment.
*   **Pathfinding**: Finds the shortest hierarchical path between any two concepts in the space.
*   **Interactive 2D Visualization**:
    *   Visualizes N-dimensional spaces by projecting them onto a 2D plane.
    *   Interactively select which dimensions to display.
    *   Click to select concepts and see their properties.
    *   Right-click to find and visualize the hierarchical path between two concepts.
    *   Dynamic UI provides feedback on the current state and actions.
    *   Accessible color schemes and line styles to distinguish relationships.
*   **Backward Compatibility**: The N-dimensional `RegionND` and `ConceptSpaceND` are backward compatible with the original 2D `Box2D` and `ConceptSpace2D` classes.

## Architecture

The project is structured into several key components:

*   **`regionai.geometry.region`**: Defines the `RegionND` class, which represents an N-dimensional hyperrectangle. It provides methods for geometric operations like `volume`, `contains`, `overlaps`, `intersection`, and `union`. The `Box2D` class is an alias for a 2D `RegionND`.
*   **`regionai.spaces.concept_space`**: Defines the `ConceptSpaceND` class, which manages a collection of named `RegionND` objects. It provides methods for adding regions, finding the parent of a region, and iterating over the concepts.
*   **`regionai.engine.pathfinder`**: Implements the `Pathfinder` class, which uses the parent relationships in a `ConceptSpaceND` to find the shortest hierarchical path between two concepts.
*   **`regionai.visualization.interactive_plotter`**: Contains the `InteractivePlotter` class, which uses `matplotlib` to create an interactive 2D plot of a `ConceptSpaceND`. It handles user input (mouse clicks, key presses) to enable selection, pathfinding, and dimension exploration.

## Getting Started

1.  **Install Dependencies**: The project uses `poetry` for dependency management. To install the required packages, run:
    ```bash
    poetry install
    ```

2.  **Run a Demo**: The `scripts` directory contains several demo scripts to showcase the project's functionality. For example, to run the main interactive demo, execute:
    ```bash
    poetry run python scripts/run_interactive_2d.py
    ```
    To run the N-dimensional visualization demo:
    ```bash
    poetry run python scripts/demo_day15_16_nd_visualization.py
    ```

## Usage

The interactive plotter provides a powerful way to explore concept spaces.

*   **Left-click**: Select a region to highlight it and see its properties.
*   **Right-click**:
    1.  Right-click on a region to set it as the starting point for pathfinding.
    2.  Right-click on another region to find and display the hierarchical path between them.
*   **'c' key**: Clear the current selection and path.
*   **'x' key**: Cycle through the dimensions to display on the x-axis (in N-D mode).
*   **'y' key**: Cycle through the dimensions to display on the y-axis (in N-D mode).

## Running Tests

The project uses `pytest` for testing. To run the test suite, execute:
```bash
poetry run pytest
```
