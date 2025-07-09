"""Static visualization for concept spaces."""

from typing import Optional, Dict, List, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from ..spaces.concept_space_2d import ConceptSpace2D
from ..config.settings import Config, VisualizationConfig


class ConceptPlotter:
    """Static plotter for visualizing 2D concept spaces."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        """Initialize the plotter with configuration.
        
        Args:
            config: Visualization configuration (uses default if None)
        """
        self.config = config or Config().viz
        self._color_map: Dict[str, str] = {}
        self._default_colors = ['blue', 'red', 'green', 'orange', 'purple', 
                               'brown', 'pink', 'gray', 'olive', 'cyan']
        self._color_index = 0
    
    def plot(
        self, 
        space: ConceptSpace2D, 
        figsize: Optional[Tuple[int, int]] = None,
        title: Optional[str] = None,
        show_labels: bool = True,
        show_hierarchy: bool = False
    ) -> Figure:
        """Create a static plot of the concept space.
        
        Args:
            space: The concept space to visualize
            figsize: Figure size (width, height) in inches
            title: Plot title
            show_labels: Whether to show region names
            show_hierarchy: Whether to emphasize hierarchical relationships
            
        Returns:
            The matplotlib Figure object
        """
        figsize = figsize or self.config.figsize
        fig, ax = plt.subplots(figsize=figsize, dpi=self.config.dpi)
        
        if title:
            ax.set_title(title, fontsize=16)
        
        # Compute bounds for axis limits
        bounds = self._compute_bounds(space)
        if bounds:
            ax.set_xlim(bounds[0], bounds[2])
            ax.set_ylim(bounds[1], bounds[3])
        
        # Sort regions by area (largest first) for proper layering
        sorted_regions = self._sort_by_hierarchy(space) if show_hierarchy else self._sort_by_area(space)
        
        # Plot each region
        for name in sorted_regions:
            region = space.get_region(name)
            self._plot_region(ax, name, region, show_labels)
        
        # Configure plot
        ax.set_aspect('equal')
        if self.config.grid:
            ax.grid(True, alpha=0.3)
        ax.set_xlabel('X', fontsize=12)
        ax.set_ylabel('Y', fontsize=12)
        
        plt.tight_layout()
        return fig
    
    def _plot_region(
        self, 
        ax, 
        name: str, 
        region, 
        show_label: bool,
        alpha: Optional[float] = None,
        color: Optional[str] = None
    ):
        """Plot a single region on the axes.
        
        Args:
            ax: Matplotlib axes
            name: Region name
            region: The Box2D region
            show_label: Whether to show the label
            alpha: Override transparency
            color: Override color
        """
        # Get region properties
        min_corner = region.min_corner.cpu().numpy()
        size = region.size().cpu().numpy()
        center = region.center().cpu().numpy()
        
        # Determine color
        if color is None:
            color = self._get_color(name)
        
        # Determine alpha
        if alpha is None:
            alpha = self.config.default_alpha
        
        # Create rectangle patch
        rect = patches.Rectangle(
            min_corner, 
            size[0], 
            size[1],
            linewidth=2,
            edgecolor=color,
            facecolor=color,
            alpha=alpha,
            label=name
        )
        ax.add_patch(rect)
        
        # Add label
        if show_label:
            ax.text(
                center[0], 
                center[1], 
                name,
                ha='center',
                va='center',
                fontsize=10,
                weight='bold',
                color='black',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
            )
    
    def _get_color(self, name: str) -> str:
        """Get a consistent color for a region name."""
        if name not in self._color_map:
            self._color_map[name] = self._default_colors[self._color_index % len(self._default_colors)]
            self._color_index += 1
        return self._color_map[name]
    
    def _compute_bounds(self, space: ConceptSpace2D) -> Optional[Tuple[float, float, float, float]]:
        """Compute the bounding box of all regions.
        
        Returns:
            (min_x, min_y, max_x, max_y) or None if no regions
        """
        if len(space) == 0:
            return None
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for name in space:
            region = space.get_region(name)
            min_corner = region.min_corner.cpu().numpy()
            max_corner = region.max_corner.cpu().numpy()
            
            min_x = min(min_x, min_corner[0])
            min_y = min(min_y, min_corner[1])
            max_x = max(max_x, max_corner[0])
            max_y = max(max_y, max_corner[1])
        
        # Add padding
        padding_x = (max_x - min_x) * 0.1
        padding_y = (max_y - min_y) * 0.1
        
        return (min_x - padding_x, min_y - padding_y, 
                max_x + padding_x, max_y + padding_y)
    
    def _sort_by_area(self, space: ConceptSpace2D) -> List[str]:
        """Sort regions by area (largest first)."""
        return sorted(
            space.list_regions(),
            key=lambda name: space.get_region(name).volume(),
            reverse=True
        )
    
    def _sort_by_hierarchy(self, space: ConceptSpace2D) -> List[str]:
        """Sort regions for hierarchical visualization."""
        # Get containment relationships
        hierarchy = space.get_hierarchical_relationships()
        
        # Calculate depth for each region
        depths = {}
        for name in space:
            depths[name] = self._calculate_depth(name, hierarchy)
        
        # Sort by depth (deepest first) then by area
        return sorted(
            space.list_regions(),
            key=lambda name: (-depths[name], space.get_region(name).volume()),
            reverse=True
        )
    
    def _calculate_depth(self, name: str, hierarchy: Dict[str, List[str]]) -> int:
        """Calculate the depth of a region in the hierarchy."""
        # Find all regions that contain this one
        containers = []
        for parent, children in hierarchy.items():
            if name in children:
                containers.append(parent)
        
        if not containers:
            return 0
        
        # Recursively find maximum depth
        return 1 + max(self._calculate_depth(parent, hierarchy) for parent in containers)
    
    def show(self):
        """Display the current plot."""
        plt.show()
    
    def save(self, filename: str, dpi: Optional[int] = None):
        """Save the current plot to a file.
        
        Args:
            filename: Output filename
            dpi: Dots per inch (uses config default if None)
        """
        plt.savefig(filename, dpi=dpi or self.config.dpi, bbox_inches='tight')