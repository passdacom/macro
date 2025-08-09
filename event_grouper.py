
from dataclasses import dataclass
import keyboard
import mouse

@dataclass
class GroupedAction:
    display_text: str
    start_index: int
    end_index: int

# --- Constants and Helpers ---
HUMAN_PAUSE_THRESHOLD = 0.5
MODIFIER_KEYS = {'ctrl', 'alt', 'shift', 'cmd', 'win'}

def _get_event_time(event): return event[0]
def _get_event_obj(event): return event[1][0]
def _is_modifier(key_name): return key_name.lower() in MODIFIER_KEYS

# --- Robust Pattern Finders ---

def _find_shortcut(events, i):
    start_event = _get_event_obj(events[i])
    if not (isinstance(start_event, keyboard.KeyboardEvent) and start_event.event_type == 'down' and _is_modifier(start_event.name)):
        return None

    active_modifiers = {start_event.name.lower()}
    pressed_keys = set()
    
    for j in range(i + 1, len(events)):
        evt = _get_event_obj(events[j])
        if isinstance(evt, keyboard.KeyboardEvent):
            key_name = evt.name.lower()
            if evt.event_type == 'down':
                if _is_modifier(key_name):
                    active_modifiers.add(key_name)
                else:
                    pressed_keys.add(key_name)
            elif evt.event_type == 'up':
                if _is_modifier(key_name):
                    active_modifiers.discard(key_name)
        else:
            # If a non-keyboard event occurs, the shortcut attempt is over.
            # We check if it was a valid shortcut up to the previous event.
            if not pressed_keys:
                return None
            # Find the real end of the shortcut (last key up)
            final_end = j - 1
            text = f"Shortcut: {" + ".join(sorted(list(active_modifiers)))} + {" + ".join(sorted(list(pressed_keys)))}"
            return GroupedAction(text, i, final_end), final_end + 1

        if not active_modifiers: # All modifiers have been released
            if not pressed_keys:
                return None # It was just a modifier tap, not a shortcut
            
            mods_at_time_of_press = sorted([k.capitalize() for k in active_modifiers.union({start_event.name.lower()})])
            keys_at_time_of_press = sorted([k.capitalize() for k in pressed_keys])

            text = f"Shortcut: {" + ".join(mods_at_time_of_press)} + {" + ".join(keys_at_time_of_press)}"
            return GroupedAction(text, i, j), j + 1

    return None # Reached end of events

def _find_drag_or_click(events, i):
    start_event = _get_event_obj(events[i])
    if not (isinstance(start_event, mouse.ButtonEvent) and start_event.event_type == 'down'):
        return None

    is_drag = False
    for j in range(i + 1, len(events)):
        evt = _get_event_obj(events[j])
        if isinstance(evt, mouse.MoveEvent):
            is_drag = True
        elif isinstance(evt, mouse.ButtonEvent) and evt.button == start_event.button and evt.event_type == 'up':
            text = f"Mouse Drag ({start_event.button})" if is_drag else f"Mouse Click ({start_event.button})"
            return GroupedAction(text, i, j), j + 1
    return None

def _find_sequence(events, i, event_type, base_display_name):
    start_event = _get_event_obj(events[i])
    if not isinstance(start_event, event_type):
        return None

    end_index = i
    # Special handling for wheel direction
    initial_delta_sign = 0
    if event_type is mouse.WheelEvent:
        initial_delta_sign = 1 if start_event.delta > 0 else -1

    for j in range(i + 1, len(events)):
        prev_time = _get_event_time(events[j-1])
        curr_time = _get_event_time(events[j])
        curr_event = _get_event_obj(events[j])

        if not isinstance(curr_event, event_type) or (curr_time - prev_time) > HUMAN_PAUSE_THRESHOLD:
            break
        
        # If it's a wheel event, check if the direction has changed
        if event_type is mouse.WheelEvent:
            current_delta_sign = 1 if curr_event.delta > 0 else -1
            if current_delta_sign != initial_delta_sign:
                break

        end_index = j
    
    display_name = base_display_name
    if event_type is mouse.WheelEvent:
        direction = "Up" if initial_delta_sign > 0 else "Down"
        display_name = f"{base_display_name} ({direction})"

    return GroupedAction(display_name, i, end_index), end_index + 1

# --- Main Grouper Function ---

def group_events(raw_events: list) -> list[GroupedAction]:
    if not raw_events:
        return []

    actions = []
    i = 0
    while i < len(raw_events):
        result = (
            _find_shortcut(raw_events, i) or
            _find_drag_or_click(raw_events, i) or
            _find_sequence(raw_events, i, mouse.WheelEvent, "Mouse Wheel Scroll") or
            _find_sequence(raw_events, i, mouse.MoveEvent, "Mouse Move")
        )

        if result:
            action, next_i = result
            actions.append(action)
            i = next_i
        else:
            # If no pattern matches, try to group single key presses (down + up)
            evt_obj = _get_event_obj(raw_events[i])
            if isinstance(evt_obj, keyboard.KeyboardEvent) and evt_obj.event_type == 'down':
                for j in range(i + 1, len(raw_events)):
                    next_evt = _get_event_obj(raw_events[j])
                    if isinstance(next_evt, keyboard.KeyboardEvent) and next_evt.name == evt_obj.name and next_evt.event_type == 'up':
                        text = f"Key Press: {evt_obj.name.capitalize()}"
                        actions.append(GroupedAction(text, i, j))
                        i = j + 1
                        break
                else: # No matching up event found, treat as single down
                    actions.append(GroupedAction(f"Key Down: {evt_obj.name.capitalize()}", i, i))
                    i += 1
            else:
                # If still no pattern matches, treat as a single raw event
                text = f"Event: {evt_obj}"
                actions.append(GroupedAction(text, i, i))
                i += 1
    return actions
