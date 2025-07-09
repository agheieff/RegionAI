"""Simple interactive plotter with mouse event handling."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from ..spaces.concept_space_2d import ConceptSpace2D
from ..engine.pathfinder import Pathfinder


class InteractivePlotter:
    """Interactive plotter for 2D concept spaces with mouse event handling."""

    def __init__(self, space: ConceptSpace2D):
        """Initialize the plotter with a concept space.

        Args:
            space: The concept space to visualize
        """
        self.space = space
        self.fig = None
        self.ax = None
        self.patches = {}  # Map from region name to matplotlib patch
        self.selected_region = None

        # Pathfinding state
        self.pathfinding_start = None
        self.pathfinding_path = []

        # Hard-coded colors for simplicity
        self.default_color = "blue"
        self.selected_color = "red"
        self.alpha = 0.3
        self.selected_alpha = 0.6

    def _reset_state(self):
        """Reset all UI state."""
        self.pathfinding_start = None
        self.pathfinding_path = []
        self.selected_region = None

    def show(self):
        """Create and display the interactive plot."""
        # Create figure and axis
        self.fig, self.ax = plt.subplots(figsize=(10, 10))

        # Initial draw
        self._redraw_plot()

        # Connect mouse and keyboard events
        self.fig.canvas.mpl_connect("button_press_event", self._handle_click)
        self.fig.canvas.mpl_connect("key_press_event", self._handle_key_press)

        # Show the plot
        plt.show()

    def _redraw_plot(self):
        """Single source of truth for all drawing operations."""
        # Clear the current axes completely
        self.ax.clear()
        self.patches.clear()

        # Re-setup axes
        self.ax.set_aspect("equal")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        # Dynamic title based on current state
        if self.pathfinding_path:
            # Path found - show the path
            path_str = " → ".join(self.pathfinding_path)
            title = f"Path Found: {path_str}"
        elif self.pathfinding_start:
            # Waiting for end point
            title = f"Pathfinding: Select an end point. Start: {self.pathfinding_start}"
        elif self.selected_region:
            # Region selected
            title = f"Selected: {self.selected_region}"
        else:
            # Default instructions
            title = "Left-click to select. Right-click to find path. C to clear"

        self.ax.set_title(title)

        # Sort regions by area (largest first) so smaller regions are drawn on top
        sorted_regions = sorted(
            self.space.items(), key=lambda item: item[1].volume(), reverse=True
        )

        # Draw each region according to current state
        for name, region in sorted_regions:
            # Get properties
            min_corner = region.min_corner.cpu().numpy()
            width = region.size().cpu().numpy()[0]
            height = region.size().cpu().numpy()[1]

            # State-based styling with order of precedence
            if self.pathfinding_path and name in self.pathfinding_path:
                # Path Found: Vibrant success style
                facecolor = "orange"
                edgecolor = "black"
                alpha = 0.7
                linewidth = 4
                linestyle = "-"
            elif name == self.pathfinding_start:
                # Pathfinding Start: Waiting for input style
                facecolor = "purple"
                edgecolor = "purple"
                alpha = 0.6
                linewidth = 3
                linestyle = "--"
            elif name == self.selected_region:
                # Simple Selection: Selected style
                facecolor = self.selected_color
                edgecolor = self.selected_color
                alpha = self.selected_alpha
                linewidth = 3
                linestyle = "-"
            elif self.selected_region and name != self.selected_region:
                # Check parent/child relationships when something is selected
                selected_region = self.space.get_region(self.selected_region)
                current_region = region

                if selected_region and current_region.contains(selected_region):
                    # This is a parent of the selected region
                    facecolor = "lightblue"
                    edgecolor = "darkblue"
                    alpha = 0.5
                    linewidth = 2
                    linestyle = "--"  # Dashed for parents
                elif selected_region and selected_region.contains(current_region):
                    # This is a child of the selected region
                    facecolor = "lightgreen"
                    edgecolor = "darkgreen"
                    alpha = 0.5
                    linewidth = 2
                    linestyle = ":"  # Dotted for children
                else:
                    # Default: Neutral style
                    facecolor = self.default_color
                    edgecolor = self.default_color
                    alpha = self.alpha
                    linewidth = 1
                    linestyle = "-"
            else:
                # Default: Neutral style
                facecolor = self.default_color
                edgecolor = self.default_color
                alpha = self.alpha
                linewidth = 1
                linestyle = "-"

            # Create rectangle patch
            rect = patches.Rectangle(
                min_corner,
                width,
                height,
                linewidth=linewidth,
                edgecolor=edgecolor,
                facecolor=facecolor,
                alpha=alpha,
                linestyle=linestyle,
            )

            # Add to axes
            self.ax.add_patch(rect)
            self.patches[name] = rect

            # Add label at center
            center = region.center().cpu().numpy()
            # Make text more prominent for path regions
            fontweight = (
                "bold"
                if (self.pathfinding_path and name in self.pathfinding_path)
                else "normal"
            )
            fontsize = (
                12 if (self.pathfinding_path and name in self.pathfinding_path) else 10
            )

            self.ax.text(
                center[0],
                center[1],
                name,
                ha="center",
                va="center",
                fontsize=fontsize,
                weight=fontweight,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
            )

        # Auto-scale to show all regions
        self.ax.autoscale_view()

    def _handle_click(self, event):
        """General click handler that delegates to specific handlers.

        Args:
            event: Matplotlib mouse event
        """
        # Check if click was inside the axes
        if event.inaxes != self.ax:
            return

        if event.button == 1:  # Left click
            self._on_left_click(event)
        elif event.button == 3:  # Right click
            self._on_right_click(event)

    def _on_left_click(self, event):
        """Handle left mouse click events for selection.

        Args:
            event: Matplotlib mouse event
        """
        # Get click coordinates
        x, y = event.xdata, event.ydata

        # Find which region was clicked (smallest containing region)
        clicked_region = None
        clicked_volume = float("inf")

        for name, region in self.space.items():
            min_corner = region.min_corner.cpu().numpy()
            max_corner = region.max_corner.cpu().numpy()

            # Check if click is inside this region
            if (
                min_corner[0] <= x <= max_corner[0]
                and min_corner[1] <= y <= max_corner[1]
            ):
                volume = region.volume()
                if volume < clicked_volume:
                    clicked_region = name
                    clicked_volume = volume

        # Update selection
        if clicked_region != self.selected_region:
            self.selected_region = clicked_region
            # Clear pathfinding when selecting
            self.pathfinding_start = None
            self.pathfinding_path = []

            print(f"Selected: {clicked_region}")

            # Print some info about the selected region
            if clicked_region:
                region = self.space.get_region(clicked_region)
                print(f"  Volume: {region.volume():.2f}")
                print(f"  Center: {region.center().cpu().numpy()}")
                print(f"  Min corner: {region.min_corner.cpu().numpy()}")
                print(f"  Max corner: {region.max_corner.cpu().numpy()}")

            # Redraw with new state
            self._redraw_plot()
            self.fig.canvas.draw_idle()

    def _on_right_click(self, event):
        """Handle right mouse click events for pathfinding.

        Args:
            event: Matplotlib mouse event
        """
        # Get click coordinates
        x, y = event.xdata, event.ydata

        # Find which region was clicked (smallest containing region)
        clicked_region = None
        clicked_volume = float("inf")

        for name, region in self.space.items():
            min_corner = region.min_corner.cpu().numpy()
            max_corner = region.max_corner.cpu().numpy()

            # Check if click is inside this region
            if (
                min_corner[0] <= x <= max_corner[0]
                and min_corner[1] <= y <= max_corner[1]
            ):
                volume = region.volume()
                if volume < clicked_volume:
                    clicked_region = name
                    clicked_volume = volume

        # If no region clicked, do nothing
        if not clicked_region:
            return

        # Handle pathfinding logic
        if self.pathfinding_start is None:
            # Set start point
            self.pathfinding_start = clicked_region
            self.pathfinding_path = []
            self.selected_region = None  # Clear selection when pathfinding
            print(f"Pathfinding start set to: {clicked_region}")

            # Redraw with new state
            self._redraw_plot()
            self.fig.canvas.draw_idle()
        else:
            # This is the end point - find path
            start = self.pathfinding_start
            end = clicked_region

            path = Pathfinder.find_path(start, end, self.space)

            if path:
                print(f"Path found: {' → '.join(path)}")
                self.pathfinding_path = path
                # Keep the path visualization for a moment
                self._redraw_plot()
                self.fig.canvas.draw_idle()

                # Don't immediately reset - let user see the path
            else:
                print(f"No path found from {start} to {end}")
                # Reset state after failed pathfinding
                self._reset_state()
                self._redraw_plot()
                self.fig.canvas.draw_idle()

    def _handle_key_press(self, event):
        """Handle keyboard events.

        Args:
            event: Matplotlib keyboard event
        """
        if event.key == "c":
            # Clear all state
            print("Clearing selection and pathfinding state")
            self._reset_state()

            # Redraw with cleared state
            self._redraw_plot()
            self.fig.canvas.draw_idle()
