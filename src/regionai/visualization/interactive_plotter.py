"""Interactive plotter with N-D to 2D projection capabilities."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from ..spaces.concept_space import ConceptSpaceND
from ..engine.pathfinder import Pathfinder


class InteractivePlotter:
    """Interactive plotter for N-dimensional concept spaces with 2D projection."""

    def __init__(self, space: ConceptSpaceND, dim_x: int = 0, dim_y: int = 1):
        """Initialize the plotter with an N-dimensional concept space.

        Args:
            space: The N-dimensional concept space to visualize
            dim_x: Which dimension to display on the X axis (default: 0)
            dim_y: Which dimension to display on the Y axis (default: 1)
        """
        self.space = space
        self.dim_x = dim_x
        self.dim_y = dim_y
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
        self.ax.set_xlabel(f"Dimension {self.dim_x}")
        self.ax.set_ylabel(f"Dimension {self.dim_y}")
        
        # Add dimension info to title
        dims_info = f" [Displaying dims: X={self.dim_x}, Y={self.dim_y}]"
        
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
            title = "Left-click: select, Right-click: path, C: clear, X/Y: cycle dims"

        self.ax.set_title(title + dims_info)

        # Sort regions by area (largest first) so smaller regions are drawn on top
        sorted_regions = sorted(
            self.space.items(), key=lambda item: item[1].volume(), reverse=True
        )

        # Draw each region according to current state
        for name, region in sorted_regions:
            # Get properties - extract only the dimensions we're displaying
            min_corner_full = region.min_corner.cpu().numpy()
            size_full = region.size().cpu().numpy()
            
            # Project to 2D by extracting only dim_x and dim_y
            min_x = min_corner_full[self.dim_x] if self.dim_x < len(min_corner_full) else 0
            min_y = min_corner_full[self.dim_y] if self.dim_y < len(min_corner_full) else 0
            width = size_full[self.dim_x] if self.dim_x < len(size_full) else 0
            height = size_full[self.dim_y] if self.dim_y < len(size_full) else 0

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

            # Create rectangle patch with projected coordinates
            rect = patches.Rectangle(
                (min_x, min_y),  # Use projected coordinates
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

            # Add label at center - project to 2D
            center_full = region.center().cpu().numpy()
            center_x = center_full[self.dim_x] if self.dim_x < len(center_full) else min_x + width/2
            center_y = center_full[self.dim_y] if self.dim_y < len(center_full) else min_y + height/2
            
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
                center_x,
                center_y,
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

            # Check if click is inside this region in the projected dimensions
            min_x = min_corner[self.dim_x] if self.dim_x < len(min_corner) else 0
            min_y = min_corner[self.dim_y] if self.dim_y < len(min_corner) else 0
            max_x = max_corner[self.dim_x] if self.dim_x < len(max_corner) else 0
            max_y = max_corner[self.dim_y] if self.dim_y < len(max_corner) else 0
            
            if (
                min_x <= x <= max_x
                and min_y <= y <= max_y
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

            # Check if click is inside this region in the projected dimensions
            min_x = min_corner[self.dim_x] if self.dim_x < len(min_corner) else 0
            min_y = min_corner[self.dim_y] if self.dim_y < len(min_corner) else 0
            max_x = max_corner[self.dim_x] if self.dim_x < len(max_corner) else 0
            max_y = max_corner[self.dim_y] if self.dim_y < len(max_corner) else 0
            
            if (
                min_x <= x <= max_x
                and min_y <= y <= max_y
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
            
        elif event.key == "x":
            # Cycle X dimension
            self._cycle_x_dimension()
            
        elif event.key == "y":
            # Cycle Y dimension
            self._cycle_y_dimension()
    
    def _get_max_dimension(self):
        """Get the maximum dimension from all regions in the space."""
        max_dim = 0
        for _, region in self.space.items():
            max_dim = max(max_dim, region.dims)
        return max_dim
    
    def _cycle_x_dimension(self):
        """Cycle the X dimension to the next available dimension."""
        max_dim = self._get_max_dimension()
        if max_dim <= 1:
            return  # Can't cycle in 1D or 0D space
            
        # Cycle to next dimension
        self.dim_x = (self.dim_x + 1) % max_dim
        
        # If it would equal dim_y, cycle once more
        if self.dim_x == self.dim_y:
            self.dim_x = (self.dim_x + 1) % max_dim
            
        print(f"X dimension changed to: {self.dim_x}")
        self._redraw_plot()
        self.fig.canvas.draw_idle()
    
    def _cycle_y_dimension(self):
        """Cycle the Y dimension to the next available dimension."""
        max_dim = self._get_max_dimension()
        if max_dim <= 1:
            return  # Can't cycle in 1D or 0D space
            
        # Cycle to next dimension
        self.dim_y = (self.dim_y + 1) % max_dim
        
        # If it would equal dim_x, cycle once more
        if self.dim_y == self.dim_x:
            self.dim_y = (self.dim_y + 1) % max_dim
            
        print(f"Y dimension changed to: {self.dim_y}")
        self._redraw_plot()
        self.fig.canvas.draw_idle()
