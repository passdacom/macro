from dataclasses import dataclass, field
import time
from collections import deque
import keyboard
import mouse

# --- Configuration Constants ---
DOUBLE_CLICK_TIME = 0.4  # seconds
DRAG_THRESHOLD_SQUARED = 10**2  # pixels squared, cheaper than sqrt
HUMAN_PAUSE_THRESHOLD = 0.3 # Time in seconds to consider an action complete
MODIFIER_KEYS = {'ctrl', 'alt', 'shift', 'cmd', 'win', 'left ctrl', 'right ctrl', 'left shift', 'right shift', 'left alt', 'right alt'}

# --- Data Class for Actions ---
@dataclass(kw_only=True)
class GroupedAction:
    type: str
    display_text: str
    start_time: float
    end_time: float
    start_index: int
    end_index: int
    indices: list[int] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def __repr__(self):
        return f"Action({self.display_text} @ {self.start_time:.2f}s, {len(self.indices)} events)"

# --- Main Grouper Class ---
class EventGrouper:
    def __init__(self, raw_events, log_callback=None):
        self.raw_events = [(i, evt_time, evt_data) for i, (evt_time, evt_data) in enumerate(raw_events)]
        self.actions = []
        self.processed_indices = set()
        self.log_callback = log_callback if log_callback else lambda msg: None
        
        self.state = 'IDLE'
        self.buffer = deque()

    def _get_obj(self, event_tuple): return event_tuple[2]['obj']
    def _get_time(self, event_tuple): return event_tuple[1]
    def _get_pos(self, event_tuple):
        evt_obj = self._get_obj(event_tuple)
        if isinstance(evt_obj, mouse.MoveEvent): return (evt_obj.x, evt_obj.y)
        return event_tuple[2].get('pos')

    def _finalize_action(self, action: GroupedAction):
        self.log_callback(f"GROUPER: Finalized action -> {action.display_text}")
        self.actions.append(action)
        self.processed_indices.update(action.indices)
        self.buffer.clear()
        self.state = 'IDLE'

    def _flush_buffer(self):
        if not self.buffer:
            self.state = 'IDLE'
            return

        if self.state == 'KEY_DOWN':
            self._finalize_key_sequence()
        elif self.state == 'SEQUENCE':
            self._finalize_sequence()
        
        if self.buffer:
            for event_tuple in self.buffer:
                if event_tuple[0] in self.processed_indices: continue
                # Do not log raw flushes to keep the log clean as requested
                # self.log_callback(f"GROUPER: Flushed as raw -> {self._get_obj(event_tuple)}")
                action = GroupedAction(type='raw', display_text=f"Unprocessed: {self._get_obj(event_tuple)}", start_time=self._get_time(event_tuple), end_time=self._get_time(event_tuple), start_index=event_tuple[0], end_index=event_tuple[0], indices=[event_tuple[0]])
                self.actions.append(action)
                self.processed_indices.add(event_tuple[0])
            self.buffer.clear()
        
        self.state = 'IDLE'
        
    def _finalize_key_sequence(self):
        is_modifier = lambda name: name and name.lower() in MODIFIER_KEYS
        down_events_in_buffer = [e for e in self.buffer if isinstance(self._get_obj(e), keyboard.KeyboardEvent) and self._get_obj(e).event_type == 'down']
        
        final_mods = {self._get_obj(e).name.lower() for e in down_events_in_buffer if is_modifier(self._get_obj(e).name)}
        final_actions = {self._get_obj(e).name.lower() for e in down_events_in_buffer if not is_modifier(self._get_obj(e).name)}

        if final_mods and final_actions:
            mod_text = " + ".join(sorted([k.capitalize() for k in final_mods]))
            key_text = " + ".join(sorted([k.capitalize() for k in final_actions]))
            action = GroupedAction(type='shortcut', display_text=f"Shortcut: {mod_text} + {key_text}", start_time=self._get_time(self.buffer[0]), end_time=self._get_time(self.buffer[-1]), start_index=self.buffer[0][0], end_index=self.buffer[-1][0], indices=[e[0] for e in self.buffer], details={'keys': list(final_mods.union(final_actions))})
            self._finalize_action(action)
        elif len(final_actions) >= 1 and not final_mods:
            # Group multiple key presses into a single typing action
            typed_string = "".join([self._get_obj(e).name for e in down_events_in_buffer])
            action = GroupedAction(type='typing', display_text=f"Type: '{typed_string}'", start_time=self._get_time(self.buffer[0]), end_time=self._get_time(self.buffer[-1]), start_index=self.buffer[0][0], end_index=self.buffer[-1][0], indices=[e[0] for e in self.buffer], details={'text': typed_string})
            self._finalize_action(action)

    def _finalize_sequence(self):
        if not self.buffer: return
        first_event_obj = self._get_obj(self.buffer[0])
        action_type = 'mouse_wheel' if isinstance(first_event_obj, mouse.WheelEvent) else 'mouse_move'
        display_text = "Mouse Wheel" if action_type == 'mouse_wheel' else "Mouse Move"
        action = GroupedAction(type=action_type, display_text=display_text, start_time=self._get_time(self.buffer[0]), end_time=self._get_time(self.buffer[-1]), start_index=self.buffer[0][0], end_index=self.buffer[-1][0], indices=[e[0] for e in self.buffer], details={'count': len(self.buffer)})
        self._finalize_action(action)

    def _handle_idle(self, current_event):
        evt_obj = self._get_obj(current_event)
        # Double click is a special case that modifies a *previous* action
        if isinstance(evt_obj, mouse.ButtonEvent) and evt_obj.event_type == 'double':
            last_action = self.actions[-1] if self.actions else None
            if (last_action and last_action.type == 'mouse_click' and 
                last_action.details.get('button') == evt_obj.button and
                (self._get_time(current_event) - last_action.end_time) < DOUBLE_CLICK_TIME):
                
                self.log_callback(f"GROUPER: Mutating previous click to Double Click.")
                last_action.type = 'mouse_double_click'
                last_action.display_text = f"Mouse Double Click ({evt_obj.button})"
                
                final_up_index = -1
                for j in range(current_event[0] + 1, len(self.raw_events)):
                    up_cand_tuple = self.raw_events[j]
                    up_cand_obj = self._get_obj(up_cand_tuple)
                    if isinstance(up_cand_obj, mouse.ButtonEvent) and up_cand_obj.event_type == 'up' and up_cand_obj.button == evt_obj.button:
                        final_up_index = up_cand_tuple[0]
                        break
                
                end_index = final_up_index if final_up_index != -1 else current_event[0]
                last_action.end_time = self._get_time(self.raw_events[end_index])
                last_action.end_index = end_index
                
                new_indices = list(range(last_action.start_index, end_index + 1))
                self.processed_indices.update(new_indices)
                last_action.indices = new_indices
                return # Event consumed

        # If not a double click, start a new action
        self.buffer.append(current_event)
        if isinstance(evt_obj, mouse.ButtonEvent) and evt_obj.event_type == 'down': self.state = 'MOUSE_DOWN'
        elif isinstance(evt_obj, keyboard.KeyboardEvent) and evt_obj.event_type == 'down': self.state = 'KEY_DOWN'
        elif isinstance(evt_obj, (mouse.MoveEvent, mouse.WheelEvent)): self.state = 'SEQUENCE'
        else: self._flush_buffer()

    def _handle_mouse_down(self, current_event):
        self.buffer.append(current_event)
        evt_obj = self._get_obj(current_event)
        down_obj = self._get_obj(self.buffer[0])

        if isinstance(evt_obj, mouse.ButtonEvent) and evt_obj.event_type == 'up' and evt_obj.button == down_obj.button:
            max_dist_sq = 0
            start_pos = self._get_pos(self.buffer[0])
            for e in self.buffer:
                if isinstance(self._get_obj(e), mouse.MoveEvent):
                    dist_sq = (self._get_pos(e)[0] - start_pos[0])**2 + (self._get_pos(e)[1] - start_pos[1])**2
                    max_dist_sq = max(max_dist_sq, dist_sq)
            
            action_type = 'mouse_drag' if max_dist_sq > DRAG_THRESHOLD_SQUARED else 'mouse_click'
            display_text = f"Mouse Drag ({down_obj.button})" if action_type == 'mouse_drag' else f"Mouse Click ({down_obj.button})"
            action = GroupedAction(type=action_type, display_text=display_text, start_time=self._get_time(self.buffer[0]), end_time=self._get_time(current_event), start_index=self.buffer[0][0], end_index=current_event[0], indices=[e[0] for e in self.buffer], details={'button': down_obj.button, 'start_pos': start_pos, 'end_pos': self._get_pos(current_event)})
            self._finalize_action(action)
        elif not isinstance(evt_obj, mouse.MoveEvent):
            self._flush_buffer()
            self._handle_idle(current_event)

    def _handle_key_down(self, current_event):
        evt_obj = self._get_obj(current_event)
        if isinstance(evt_obj, keyboard.KeyboardEvent):
            self.buffer.append(current_event)
        else: # Interruption
            self._flush_buffer()
            self._handle_idle(current_event)

    def _handle_sequence(self, current_event):
        evt_obj = self._get_obj(current_event)
        if self.buffer and type(evt_obj) is type(self._get_obj(self.buffer[0])):
            self.buffer.append(current_event)
        else:
            self._flush_buffer()
            self._handle_idle(current_event)

    def group(self):
        if not self.raw_events: return []

        for i, evt_time, evt_data in self.raw_events:
            if i in self.processed_indices: continue
            current_event = (i, evt_time, evt_data)
            
            if self.buffer and (evt_time - self._get_time(self.buffer[-1])) > HUMAN_PAUSE_THRESHOLD:
                self._flush_buffer()
            
            # If buffer was flushed, it's now empty. current_event needs to start a new action.
            if not self.buffer:
                self.state = 'IDLE'

            if self.state == 'IDLE':
                self._handle_idle(current_event)
            elif self.state == 'MOUSE_DOWN':
                self._handle_mouse_down(current_event)
            elif self.state == 'KEY_DOWN':
                self._handle_key_down(current_event)
            elif self.state == 'SEQUENCE':
                self._handle_sequence(current_event)
        
        self._flush_buffer()
        self.actions.sort(key=lambda a: a.start_index)
        return self.actions

def group_events(raw_events: list, log_callback=None) -> list[GroupedAction]:
    if not raw_events: return []
    grouper = EventGrouper(raw_events, log_callback=log_callback)
    return grouper.group()
