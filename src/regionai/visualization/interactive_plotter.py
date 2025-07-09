"""Simple interactive plotter with mouse event handling."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from ..spaces.concept_space_2d import ConceptSpace2D


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
        
        # Hard-coded colors for simplicity
        self.default_color = 'blue'
        self.selected_color = 'red'
        self.alpha = 0.3
        self.selected_alpha = 0.6
        
    def show(self):
        """Create and display the interactive plot."""
        # Create figure and axis
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_title('Interactive Concept Space (Click to select regions)')
        
        # Draw all regions
        self._draw_regions()
        
        # Connect mouse event
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        
        # Show the plot
        plt.show()
    
    def _draw_regions(self):
        """Draw all regions in the concept space."""
        # Clear existing patches
        self.ax.clear()
        self.patches.clear()
        
        # Re-setup axes
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_title('Interactive Concept Space (Click to select regions)')
        
        # Sort regions by area (largest first) so smaller regions are drawn on top
        sorted_regions = sorted(
            self.space.items(),
            key=lambda item: item[1].volume(),
            reverse=True
        )
        
        # Draw each region
        for name, region in sorted_regions:
            # Get properties
            min_corner = region.min_corner.cpu().numpy()
            width = region.size().cpu().numpy()[0]
            height = region.size().cpu().numpy()[1]
            
            # Determine color and alpha based on selection
            if name == self.selected_region:
                color = self.selected_color
                alpha = self.selected_alpha
                linewidth = 3
            else:
                color = self.default_color
                alpha = self.alpha
                linewidth = 1
            
            # Create rectangle patch
            rect = patches.Rectangle(
                min_corner,
                width,
                height,
                linewidth=linewidth,
                edgecolor=color,
                facecolor=color,
                alpha=alpha
            )
            
            # Add to axes
            self.ax.add_patch(rect)
            self.patches[name] = rect
            
            # Add label at center
            center = region.center().cpu().numpy()
            self.ax.text(
                center[0], center[1], name,
                ha='center', va='center',
                fontsize=10, weight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
            )
        
        # Auto-scale to show all regions
        self.ax.autoscale_view()
        
        # Force redraw
        self.fig.canvas.draw_idle()
    
    def on_click(self, event):
        """Handle mouse click events.
        
        Args:
            event: Matplotlib mouse event
        """
        # Check if click was inside the axes
        if event.inaxes != self.ax:
            return
        
        # Get click coordinates
        x, y = event.xdata, event.ydata
        
        # Find which region was clicked (smallest containing region)
        clicked_region = None
        clicked_volume = float('inf')
        
        for name, region in self.space.items():
            min_corner = region.min_corner.cpu().numpy()
            max_corner = region.max_corner.cpu().numpy()
            
            # Check if click is inside this region
            if (min_corner[0] <= x <= max_corner[0] and 
                min_corner[1] <= y <= max_corner[1]):
                volume = region.volume()
                if volume < clicked_volume:
                    clicked_region = name
                    clicked_volume = volume
        
        # Update selection
        if clicked_region != self.selected_region:
            self.selected_region = clicked_region
            print(f"Selected: {clicked_region}")
            
            # Print some info about the selected region
            if clicked_region:
                region = self.space.get_region(clicked_region)
                print(f"  Volume: {region.volume():.2f}")
                print(f"  Center: {region.center().cpu().numpy()}")
                print(f"  Min corner: {region.min_corner.cpu().numpy()}")
                print(f"  Max corner: {region.max_corner.cpu().numpy()}")
            
            # Redraw with new selection
            self._draw_regions()