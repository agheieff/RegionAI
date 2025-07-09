"""Interactive plotter with event-driven architecture."""

from typing import Optional, Dict, List, Tuple, Set
from enum import Enum
import time
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from ..spaces.concept_space_2d import ConceptSpace2D
from ..geometry.box2d import Box2D
from ..config.settings import Config, VisualizationConfig
from .events import EventManager, EventType, MouseEvent, SelectionEvent, KeyEvent, Event
from .plotter import ConceptPlotter


class VisualizationMode(Enum):
    """Different visualization modes."""
    
    HIERARCHY = "hierarchy"
    OVERLAP = "overlap"
    SELECTION = "selection"
    DEBUG = "debug"


class InteractivePlotter(ConceptPlotter):
    """Interactive plotter with event-driven updates."""
    
    def __init__(
        self, 
        space: ConceptSpace2D,
        config: Optional[VisualizationConfig] = None,
        event_manager: Optional[EventManager] = None
    ):
        """Initialize the interactive plotter.
        
        Args:
            space: The concept space to visualize
            config: Visualization configuration
            event_manager: Event manager for decoupled handling
        """
        super().__init__(config)
        self.space = space
        self.event_manager = event_manager or EventManager()
        
        # State
        self.selected_regions: Set[str] = set()
        self.highlighted_regions: Set[str] = set()
        self.mode = VisualizationMode.HIERARCHY
        self.show_debug = False
        
        # Interactive elements
        self.fig: Optional[Figure] = None
        self.ax = None
        self._region_patches: Dict[str, patches.Rectangle] = {}
        self._region_texts: Dict[str, plt.Text] = {}
        
        # Register internal handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register internal event handlers."""
        self.event_manager.register(EventType.REGION_SELECTED, self._on_region_selected)
        self.event_manager.register(EventType.REGION_DESELECTED, self._on_region_deselected)
        self.event_manager.register(EventType.SELECTION_CLEARED, self._on_selection_cleared)
        self.event_manager.register(EventType.MODE_CHANGED, self._on_mode_changed)
    
    def create_interactive_plot(
        self, 
        figsize: Optional[Tuple[int, int]] = None,
        title: Optional[str] = None
    ) -> Figure:
        """Create an interactive plot with event handling.
        
        Args:
            figsize: Figure size
            title: Plot title
            
        Returns:
            The matplotlib Figure object
        """
        figsize = figsize or self.config.figsize
        self.fig, self.ax = plt.subplots(figsize=figsize, dpi=self.config.dpi)
        
        if title:
            self.ax.set_title(title, fontsize=16)
        
        # Set up plot
        self._setup_plot()
        
        # Connect matplotlib events
        self._connect_matplotlib_events()
        
        # Initial render
        self._render()
        
        return self.fig
    
    def _setup_plot(self):
        """Set up the plot axes and bounds."""
        bounds = self._compute_bounds(self.space)
        if bounds:
            self.ax.set_xlim(bounds[0], bounds[2])
            self.ax.set_ylim(bounds[1], bounds[3])
        
        self.ax.set_aspect('equal')
        if self.config.grid:
            self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X', fontsize=12)
        self.ax.set_ylabel('Y', fontsize=12)
    
    def _connect_matplotlib_events(self):
        """Connect matplotlib events to our event system."""
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
    
    def _render(self):
        """Render the current visualization state."""
        # Clear existing patches
        self.ax.clear()
        self._region_patches.clear()
        self._region_texts.clear()
        
        # Re-setup plot
        self._setup_plot()
        
        # Sort regions based on mode
        if self.mode == VisualizationMode.HIERARCHY:
            sorted_regions = self._sort_by_hierarchy(self.space)
        else:
            sorted_regions = self._sort_by_area(self.space)
        
        # Plot each region
        for name in sorted_regions:
            region = self.space.get_region(name)
            self._plot_interactive_region(name, region)
        
        # Add mode indicator
        self._add_mode_indicator()
        
        # Refresh canvas
        self.fig.canvas.draw_idle()
    
    def _plot_interactive_region(self, name: str, region: Box2D):
        """Plot a region with interactive properties."""
        # Determine visual properties based on state
        alpha = self.config.default_alpha
        color = self._get_color(name)
        linewidth = 2
        
        if name in self.selected_regions:
            color = self.config.selection_color
            alpha = self.config.highlight_alpha
            linewidth = self.config.highlight_linewidth
        elif name in self.highlighted_regions:
            alpha = self.config.highlight_alpha
            linewidth = self.config.highlight_linewidth
        
        # Create patch
        min_corner = region.min_corner.cpu().numpy()
        size = region.size().cpu().numpy()
        
        rect = patches.Rectangle(
            min_corner, 
            size[0], 
            size[1],
            linewidth=linewidth,
            edgecolor=color,
            facecolor=color,
            alpha=alpha,
            picker=True  # Enable picking
        )
        
        patch = self.ax.add_patch(rect)
        self._region_patches[name] = patch
        
        # Add label
        center = region.center().cpu().numpy()
        text = self.ax.text(
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
        self._region_texts[name] = text
        
        # Add debug info if enabled
        if self.show_debug or self.mode == VisualizationMode.DEBUG:
            self._add_debug_info(name, region)
    
    def _add_debug_info(self, name: str, region: Box2D):
        """Add debug information for a region."""
        min_corner = region.min_corner.cpu().numpy()
        max_corner = region.max_corner.cpu().numpy()
        
        # Corner coordinates
        self.ax.text(min_corner[0], min_corner[1], 
                    f"({min_corner[0]:.1f},{min_corner[1]:.1f})", 
                    fontsize=8, alpha=0.7)
        self.ax.text(max_corner[0], max_corner[1], 
                    f"({max_corner[0]:.1f},{max_corner[1]:.1f})", 
                    fontsize=8, alpha=0.7)
        
        # Volume
        center = region.center().cpu().numpy()
        self.ax.text(center[0], center[1] - 5, 
                    f"Area: {region.volume():.1f}", 
                    fontsize=8, alpha=0.7, ha='center')
    
    def _add_mode_indicator(self):
        """Add current mode indicator to the plot."""
        mode_text = f"Mode: {self.mode.value}"
        if self.selected_regions:
            mode_text += f" | Selected: {len(self.selected_regions)}"
        
        self.ax.text(0.02, 0.98, mode_text, 
                    transform=self.ax.transAxes,
                    fontsize=10,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    def _on_click(self, event):
        """Handle matplotlib click events."""
        if event.inaxes != self.ax:
            return
        
        # Create our event
        mouse_event = MouseEvent(
            event_type=EventType.MOUSE_CLICK,
            timestamp=time.time(),
            data={},
            x=event.xdata,
            y=event.ydata,
            button=event.button,
            modifiers=[]
        )
        
        # Check which region was clicked
        clicked_region = self._find_region_at_point(event.xdata, event.ydata)
        
        if clicked_region:
            # Toggle selection
            if clicked_region in self.selected_regions:
                self.event_manager.emit(SelectionEvent(
                    event_type=EventType.REGION_DESELECTED,
                    timestamp=time.time(),
                    data={},
                    region_name=clicked_region,
                    is_selected=False
                ))
            else:
                self.event_manager.emit(SelectionEvent(
                    event_type=EventType.REGION_SELECTED,
                    timestamp=time.time(),
                    data={},
                    region_name=clicked_region,
                    is_selected=True
                ))
        
        # Emit the mouse event too
        self.event_manager.emit(mouse_event)
    
    def _on_key_press(self, event):
        """Handle matplotlib keyboard events."""
        key_event = KeyEvent(
            event_type=EventType.KEY_PRESSED,
            timestamp=time.time(),
            data={},
            key=event.key,
            modifiers=[]
        )
        
        # Handle specific keys
        if event.key == 'escape':
            self.event_manager.emit(Event(
                event_type=EventType.SELECTION_CLEARED,
                timestamp=time.time(),
                data={}
            ))
        elif event.key == 'h':
            self.set_mode(VisualizationMode.HIERARCHY)
        elif event.key == 'o':
            self.set_mode(VisualizationMode.OVERLAP)
        elif event.key == 'd':
            self.set_mode(VisualizationMode.DEBUG)
        elif event.key == 'tab':
            self._cycle_selection()
        
        self.event_manager.emit(key_event)
    
    def _on_mouse_move(self, event):
        """Handle mouse move events."""
        if event.inaxes != self.ax:
            return
        
        # Find region under mouse
        hover_region = self._find_region_at_point(event.xdata, event.ydata)
        
        # Update highlights based on mode
        new_highlights = set()
        
        if hover_region:
            if self.mode == VisualizationMode.HIERARCHY:
                # Highlight containment hierarchy
                region = self.space.get_region(hover_region)
                new_highlights.add(hover_region)
                new_highlights.update(self.space.find_containing_regions(region))
                new_highlights.update(self.space.find_contained_regions(region))
            elif self.mode == VisualizationMode.OVERLAP:
                # Highlight overlapping regions
                region = self.space.get_region(hover_region)
                new_highlights.update(self.space.find_overlapping_regions(region))
        
        # Update if changed
        if new_highlights != self.highlighted_regions:
            self.highlighted_regions = new_highlights
            self._render()
    
    def _find_region_at_point(self, x: float, y: float) -> Optional[str]:
        """Find the smallest region containing a point."""
        containing_regions = []
        
        for name, region in self.space.items():
            min_corner = region.min_corner.cpu().numpy()
            max_corner = region.max_corner.cpu().numpy()
            
            if (min_corner[0] <= x <= max_corner[0] and 
                min_corner[1] <= y <= max_corner[1]):
                containing_regions.append((name, region.volume()))
        
        # Return smallest containing region
        if containing_regions:
            containing_regions.sort(key=lambda x: x[1])
            return containing_regions[0][0]
        
        return None
    
    def _cycle_selection(self):
        """Cycle through regions for selection."""
        all_regions = list(self.space.list_regions())
        if not all_regions:
            return
        
        if not self.selected_regions:
            # Select first
            first = all_regions[0]
            self.event_manager.emit(SelectionEvent(
                event_type=EventType.REGION_SELECTED,
                timestamp=time.time(),
                data={},
                region_name=first,
                is_selected=True
            ))
        else:
            # Find next
            current = list(self.selected_regions)[0]
            if current in all_regions:
                idx = all_regions.index(current)
                next_idx = (idx + 1) % len(all_regions)
                
                # Clear and select next
                self.event_manager.emit(Event(
                    event_type=EventType.SELECTION_CLEARED,
                    timestamp=time.time(),
                    data={}
                ))
                self.event_manager.emit(SelectionEvent(
                    event_type=EventType.REGION_SELECTED,
                    timestamp=time.time(),
                    data={},
                    region_name=all_regions[next_idx],
                    is_selected=True
                ))
    
    def _on_region_selected(self, event: SelectionEvent):
        """Handle region selection events."""
        self.selected_regions.add(event.region_name)
        self._render()
    
    def _on_region_deselected(self, event: SelectionEvent):
        """Handle region deselection events."""
        self.selected_regions.discard(event.region_name)
        self._render()
    
    def _on_selection_cleared(self, event: Event):
        """Handle selection clear events."""
        self.selected_regions.clear()
        self._render()
    
    def _on_mode_changed(self, event: Event):
        """Handle mode change events."""
        if 'mode' in event.data:
            self.mode = event.data['mode']
            self._render()
    
    def set_mode(self, mode: VisualizationMode):
        """Set the visualization mode."""
        self.event_manager.emit(Event(
            event_type=EventType.MODE_CHANGED,
            timestamp=time.time(),
            data={'mode': mode}
        ))
    
    def show(self):
        """Display the interactive plot."""
        plt.show()