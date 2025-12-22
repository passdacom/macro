"""
Type definitions for the Macro Editor.
This module provides type hints and data structures used across the application.
"""
from typing import TypeAlias, Callable, Optional, Any
from dataclasses import dataclass, field

# Type Aliases for Event Data
EventTime: TypeAlias = float
EventData: TypeAlias = dict[str, Any]
RawEvent: TypeAlias = tuple[EventTime, EventData]
RawEventList: TypeAlias = list[RawEvent]

# Callback Types
LogCallback: TypeAlias = Optional[Callable[[str], None]]
FinishCallback: TypeAlias = Callable[[], None]
HighlightCallback: TypeAlias = Optional[Callable[[int], None]]


@dataclass(kw_only=True)
class GroupedAction:
    """
    Represents a grouped action (e.g., Click, Double Click, Shortcut).
    
    Attributes:
        type: Action type ('mouse_click', 'shortcut', 'loop_start', etc.)
        display_text: Human-readable description for UI
        start_time: Start timestamp (relative to macro start)
        end_time: End timestamp (relative to macro start)
        start_index: Index of first raw event in this action
        end_index: Index of last raw event in this action
        indices: List of all raw event indices belonging to this action
        details: Additional metadata (button, keys, coordinates, etc.)
    """
    type: str
    display_text: str
    start_time: float
    end_time: float
    start_index: int
    end_index: int
    indices: list[int] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Action({self.display_text} @ {self.start_time:.2f}s, {len(self.indices)} events)"


# Logic Action Types
LOGIC_TYPES = frozenset({
    'loop_start',
    'loop_end', 
    'wait_color',
    'wait_sound',
    'if_color_match',
    'if_color_else',
    'if_color_end',
    'call_macro'
})

# Modifier Keys Set
MODIFIER_KEYS = frozenset({
    'ctrl', 'alt', 'shift', 'cmd', 'win',
    'left ctrl', 'right ctrl',
    'left shift', 'right shift',
    'left alt', 'right alt',
    'left windows', 'right windows'
})

# Constants
DOUBLE_CLICK_TIME = 0.3  # seconds
DRAG_THRESHOLD_SQUARED = 100  # pixels squared (10^2)
HUMAN_PAUSE_THRESHOLD = 0.3  # seconds
