"""Event management system for decoupled visualization."""

from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
from enum import Enum


class EventType(Enum):
    """Standard event types for the visualization system."""
    
    # Mouse events
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_ENTER = "mouse_enter"
    MOUSE_LEAVE = "mouse_leave"
    
    # Selection events
    REGION_SELECTED = "region_selected"
    REGION_DESELECTED = "region_deselected"
    SELECTION_CLEARED = "selection_cleared"
    
    # Visualization events
    MODE_CHANGED = "mode_changed"
    VIEW_UPDATED = "view_updated"
    
    # Keyboard events
    KEY_PRESSED = "key_pressed"


@dataclass
class Event:
    """Base event class."""
    
    event_type: EventType
    timestamp: float
    data: Dict[str, Any]


@dataclass
class MouseEvent(Event):
    """Mouse-specific event data."""
    
    x: float
    y: float
    button: Optional[int] = None
    modifiers: Optional[List[str]] = None
    
    def __post_init__(self):
        """Add coordinates to event data."""
        self.data.update({
            'x': self.x,
            'y': self.y,
            'button': self.button,
            'modifiers': self.modifiers or []
        })


@dataclass
class SelectionEvent(Event):
    """Selection-specific event data."""
    
    region_name: str
    is_selected: bool
    
    def __post_init__(self):
        """Add selection info to event data."""
        self.data.update({
            'region_name': self.region_name,
            'is_selected': self.is_selected
        })


@dataclass
class KeyEvent(Event):
    """Keyboard event data."""
    
    key: str
    modifiers: Optional[List[str]] = None
    
    def __post_init__(self):
        """Add key info to event data."""
        self.data.update({
            'key': self.key,
            'modifiers': self.modifiers or []
        })


class EventManager:
    """Decoupled event handling for modularity."""
    
    def __init__(self):
        """Initialize the event manager."""
        self.handlers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self.event_history: List[Event] = []
        self.max_history = 1000
        self._enabled = True
    
    def register(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Register a handler for a specific event type.
        
        Args:
            event_type: The type of event to handle
            handler: Callable that accepts an Event parameter
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        if handler not in self.handlers[event_type]:
            self.handlers[event_type].append(handler)
    
    def unregister(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Unregister a handler for a specific event type.
        
        Args:
            event_type: The type of event
            handler: The handler to remove
        """
        if event_type in self.handlers and handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
    
    def emit(self, event: Event) -> None:
        """Emit an event to all registered handlers.
        
        Args:
            event: The event to emit
        """
        if not self._enabled:
            return
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Call all registered handlers
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler for {event.event_type}: {e}")
    
    def clear_handlers(self, event_type: Optional[EventType] = None) -> None:
        """Clear handlers for a specific event type or all handlers.
        
        Args:
            event_type: Specific event type to clear, or None for all
        """
        if event_type:
            self.handlers[event_type] = []
        else:
            self.handlers.clear()
    
    def enable(self) -> None:
        """Enable event processing."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable event processing."""
        self._enabled = False
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 10) -> List[Event]:
        """Get recent event history.
        
        Args:
            event_type: Filter by specific event type
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        history = self.event_history
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        return history[-limit:]


class EventBus:
    """Global event bus for application-wide event handling."""
    
    _instance: Optional['EventBus'] = None
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.manager = EventManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the event bus (only runs once)."""
        pass
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Register a handler on the global event bus."""
        self.manager.register(event_type, handler)
    
    def emit(self, event: Event) -> None:
        """Emit an event on the global event bus."""
        self.manager.emit(event)
    
    def unregister(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Unregister a handler from the global event bus."""
        self.manager.unregister(event_type, handler)