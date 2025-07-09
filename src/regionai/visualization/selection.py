"""Selection management for interactive visualization."""

from typing import Set, List, Optional, Dict, Callable
from enum import Enum
from dataclasses import dataclass, field

from ..spaces.concept_space_2d import ConceptSpace2D
from ..geometry.box2d import Box2D
from .events import EventManager, EventType, SelectionEvent, Event


class SelectionMode(Enum):
    """Different selection modes."""
    
    SINGLE = "single"          # Only one region at a time
    MULTIPLE = "multiple"      # Multiple independent regions
    HIERARCHICAL = "hierarchical"  # Select with hierarchy
    CONNECTED = "connected"    # Select connected/overlapping regions


class HighlightStrategy(Enum):
    """Strategies for highlighting related regions."""
    
    NONE = "none"
    CONTAINED = "contained"    # Highlight contained regions
    OVERLAPPING = "overlapping"  # Highlight overlapping regions
    ANCESTORS = "ancestors"    # Highlight containing regions
    DESCENDANTS = "descendants"  # Highlight contained regions
    RELATED = "related"       # All related (ancestors + descendants)


@dataclass
class SelectionState:
    """Current selection state."""
    
    selected: Set[str] = field(default_factory=set)
    highlighted: Set[str] = field(default_factory=set)
    mode: SelectionMode = SelectionMode.SINGLE
    highlight_strategy: HighlightStrategy = HighlightStrategy.RELATED


class SelectionManager:
    """Manages selection state and logic."""
    
    def __init__(
        self, 
        space: ConceptSpace2D,
        event_manager: Optional[EventManager] = None,
        mode: SelectionMode = SelectionMode.SINGLE
    ):
        """Initialize the selection manager.
        
        Args:
            space: The concept space to work with
            event_manager: Event manager for notifications
            mode: Initial selection mode
        """
        self.space = space
        self.event_manager = event_manager or EventManager()
        self.state = SelectionState(mode=mode)
        
        # Selection callbacks
        self._selection_callbacks: List[Callable[[SelectionState], None]] = []
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register event handlers."""
        self.event_manager.register(EventType.REGION_SELECTED, self._on_region_selected)
        self.event_manager.register(EventType.REGION_DESELECTED, self._on_region_deselected)
        self.event_manager.register(EventType.SELECTION_CLEARED, self._on_selection_cleared)
    
    def select_region(self, region_name: str, add_to_selection: bool = False) -> bool:
        """Select a region.
        
        Args:
            region_name: Name of the region to select
            add_to_selection: Whether to add to existing selection
            
        Returns:
            True if selection changed
        """
        if region_name not in self.space:
            return False
        
        # Handle selection based on mode
        if self.state.mode == SelectionMode.SINGLE and not add_to_selection:
            # Clear existing selection
            if self.state.selected and region_name not in self.state.selected:
                self.clear_selection()
        
        # Add to selection
        if region_name not in self.state.selected:
            self.state.selected.add(region_name)
            
            # Update highlights
            self._update_highlights()
            
            # Emit event
            self.event_manager.emit(SelectionEvent(
                event_type=EventType.REGION_SELECTED,
                timestamp=0,  # Will be set by event system
                data={},
                region_name=region_name,
                is_selected=True
            ))
            
            # Notify callbacks
            self._notify_callbacks()
            return True
        
        return False
    
    def deselect_region(self, region_name: str) -> bool:
        """Deselect a region.
        
        Args:
            region_name: Name of the region to deselect
            
        Returns:
            True if selection changed
        """
        if region_name in self.state.selected:
            self.state.selected.remove(region_name)
            
            # Update highlights
            self._update_highlights()
            
            # Emit event
            self.event_manager.emit(SelectionEvent(
                event_type=EventType.REGION_DESELECTED,
                timestamp=0,
                data={},
                region_name=region_name,
                is_selected=False
            ))
            
            # Notify callbacks
            self._notify_callbacks()
            return True
        
        return False
    
    def toggle_region(self, region_name: str) -> bool:
        """Toggle selection of a region.
        
        Args:
            region_name: Name of the region to toggle
            
        Returns:
            True if region is now selected, False if deselected
        """
        if region_name in self.state.selected:
            self.deselect_region(region_name)
            return False
        else:
            self.select_region(region_name, add_to_selection=True)
            return True
    
    def clear_selection(self) -> None:
        """Clear all selections."""
        if self.state.selected:
            self.state.selected.clear()
            self.state.highlighted.clear()
            
            # Emit event
            self.event_manager.emit(Event(
                event_type=EventType.SELECTION_CLEARED,
                timestamp=0,
                data={}
            ))
            
            # Notify callbacks
            self._notify_callbacks()
    
    def select_hierarchy(self, region_name: str, include_ancestors: bool = True, 
                        include_descendants: bool = True) -> None:
        """Select a region and its hierarchy.
        
        Args:
            region_name: Starting region
            include_ancestors: Include containing regions
            include_descendants: Include contained regions
        """
        if region_name not in self.space:
            return
        
        # Clear existing selection if in single mode
        if self.state.mode == SelectionMode.SINGLE:
            self.clear_selection()
        
        # Add the region itself
        self.state.selected.add(region_name)
        region = self.space.get_region(region_name)
        
        # Add ancestors
        if include_ancestors:
            ancestors = self.space.find_containing_regions(region)
            self.state.selected.update(ancestors)
        
        # Add descendants
        if include_descendants:
            descendants = self.space.find_contained_regions(region)
            self.state.selected.update(descendants)
        
        # Update highlights
        self._update_highlights()
        
        # Notify
        self._notify_callbacks()
    
    def set_mode(self, mode: SelectionMode) -> None:
        """Set the selection mode."""
        self.state.mode = mode
        
        # Clear selection if switching to single mode with multiple selected
        if mode == SelectionMode.SINGLE and len(self.state.selected) > 1:
            self.clear_selection()
    
    def set_highlight_strategy(self, strategy: HighlightStrategy) -> None:
        """Set the highlight strategy."""
        self.state.highlight_strategy = strategy
        self._update_highlights()
        self._notify_callbacks()
    
    def _update_highlights(self) -> None:
        """Update highlighted regions based on selection and strategy."""
        self.state.highlighted.clear()
        
        if not self.state.selected or self.state.highlight_strategy == HighlightStrategy.NONE:
            return
        
        for selected_name in self.state.selected:
            region = self.space.get_region(selected_name)
            
            if self.state.highlight_strategy == HighlightStrategy.CONTAINED:
                self.state.highlighted.update(self.space.find_contained_regions(region))
            
            elif self.state.highlight_strategy == HighlightStrategy.OVERLAPPING:
                self.state.highlighted.update(self.space.find_overlapping_regions(region))
            
            elif self.state.highlight_strategy == HighlightStrategy.ANCESTORS:
                self.state.highlighted.update(self.space.find_containing_regions(region))
            
            elif self.state.highlight_strategy == HighlightStrategy.DESCENDANTS:
                self.state.highlighted.update(self.space.find_contained_regions(region))
            
            elif self.state.highlight_strategy == HighlightStrategy.RELATED:
                self.state.highlighted.update(self.space.find_containing_regions(region))
                self.state.highlighted.update(self.space.find_contained_regions(region))
        
        # Don't highlight selected regions
        self.state.highlighted -= self.state.selected
    
    def get_selection_info(self) -> Dict[str, List[str]]:
        """Get detailed information about current selection.
        
        Returns:
            Dictionary with selection details
        """
        info = {
            'selected': list(self.state.selected),
            'highlighted': list(self.state.highlighted),
            'mode': self.state.mode.value,
            'highlight_strategy': self.state.highlight_strategy.value
        }
        
        # Add relationships for selected regions
        if self.state.selected:
            info['relationships'] = {}
            for name in self.state.selected:
                region = self.space.get_region(name)
                info['relationships'][name] = {
                    'contains': self.space.find_contained_regions(region),
                    'contained_by': self.space.find_containing_regions(region),
                    'overlaps_with': self.space.find_overlapping_regions(region)
                }
        
        return info
    
    def add_selection_callback(self, callback: Callable[[SelectionState], None]) -> None:
        """Add a callback for selection changes."""
        self._selection_callbacks.append(callback)
    
    def remove_selection_callback(self, callback: Callable[[SelectionState], None]) -> None:
        """Remove a selection callback."""
        if callback in self._selection_callbacks:
            self._selection_callbacks.remove(callback)
    
    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._selection_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                print(f"Error in selection callback: {e}")
    
    def _on_region_selected(self, event: SelectionEvent) -> None:
        """Handle external region selection events."""
        # Don't process our own events
        if event.region_name not in self.state.selected:
            self.select_region(event.region_name, add_to_selection=True)
    
    def _on_region_deselected(self, event: SelectionEvent) -> None:
        """Handle external region deselection events."""
        # Don't process our own events
        if event.region_name in self.state.selected:
            self.deselect_region(event.region_name)
    
    def _on_selection_cleared(self, event: Event) -> None:
        """Handle external selection clear events."""
        if self.state.selected:
            self.clear_selection()