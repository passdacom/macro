from dataclasses import dataclass
import keyboard
import mouse

@dataclass(kw_only=True)
class GroupedAction:
    display_text: str
    start_index: int
    end_index: int
    type: str

# --- Constants and Helpers ---
HUMAN_PAUSE_THRESHOLD = 0.5
MODIFIER_KEYS = {'ctrl', 'alt', 'shift', 'cmd', 'win'}

def _get_event_time(event): return event[0]
def _get_event_obj(event): return event[1][0]
def _is_modifier(key_name): return key_name and key_name.lower() in MODIFIER_KEYS

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
            if not evt.name: continue
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
            if not pressed_keys:
                return None
            final_end = j - 1
            text = f"Shortcut: {" + ".join(sorted(list(active_modifiers)))} + {" + ".join(sorted(list(pressed_keys)))}"
            return GroupedAction(display_text=text, type='shortcut', start_index=i, end_index=final_end), final_end + 1

        if not active_modifiers:
            if not pressed_keys:
                return None
            
            mods_at_time_of_press = sorted([k.capitalize() for k in active_modifiers.union({start_event.name.lower()})])
            keys_at_time_of_press = sorted([k.capitalize() for k in pressed_keys])

            text = f"Shortcut: {" + ".join(mods_at_time_of_press)} + {" + ".join(keys_at_time_of_press)}"
            return GroupedAction(display_text=text, type='shortcut', start_index=i, end_index=j), j + 1

    return None

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
            action_type = 'mouse_drag' if is_drag else 'mouse_click'
            text = f"Mouse Drag ({start_event.button})" if is_drag else f"Mouse Click ({start_event.button})"
            return GroupedAction(display_text=text, type=action_type, start_index=i, end_index=j), j + 1
    return None

def _find_sequence(events, i, event_type, base_display_name):
    start_event = _get_event_obj(events[i])
    if not isinstance(start_event, event_type):
        return None

    end_index = i
    initial_delta_sign = 0
    if event_type is mouse.WheelEvent:
        initial_delta_sign = 1 if start_event.delta > 0 else -1

    for j in range(i + 1, len(events)):
        prev_time = _get_event_time(events[j-1])
        curr_time = _get_event_time(events[j])
        curr_event = _get_event_obj(events[j])

        if not isinstance(curr_event, event_type) or (curr_time - prev_time) > HUMAN_PAUSE_THRESHOLD:
            break
        
        if event_type is mouse.WheelEvent:
            current_delta_sign = 1 if curr_event.delta > 0 else -1
            if current_delta_sign != initial_delta_sign:
                break

        end_index = j
    
    display_name = base_display_name
    if event_type is mouse.WheelEvent:
        direction = "Up" if initial_delta_sign > 0 else "Down"
        display_name = f"{base_display_name} ({direction})"

    action_type = 'mouse_wheel' if event_type is mouse.WheelEvent else 'mouse_move'
    return GroupedAction(display_text=display_name, type=action_type, start_index=i, end_index=end_index), end_index + 1

def _find_key_press(events, i):
    evt_obj = _get_event_obj(events[i])
    if not (isinstance(evt_obj, keyboard.KeyboardEvent) and evt_obj.event_type == 'down'):
        return None

    # Look for the matching 'up' event, but don't allow other significant events to interrupt.
    matching_up_index = -1
    for j in range(i + 1, len(events)):
        next_evt = _get_event_obj(events[j])
        # If we find the matching up event, it's a candidate.
        if isinstance(next_evt, keyboard.KeyboardEvent) and next_evt.name == evt_obj.name and next_evt.event_type == 'up':
            matching_up_index = j
            break
        # If we find another keyboard event or a mouse button/wheel event first, this is not a clean key press.
        if isinstance(next_evt, keyboard.KeyboardEvent) or isinstance(next_evt, (mouse.ButtonEvent, mouse.WheelEvent)):
            break

    if matching_up_index != -1:
        text = f"Key Press: {evt_obj.name.capitalize() if evt_obj.name else ''}"
        return GroupedAction(display_text=text, type='key_press', start_index=i, end_index=matching_up_index), matching_up_index + 1
    
    return None

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
            _find_key_press(raw_events, i) or
            _find_sequence(raw_events, i, mouse.WheelEvent, "Mouse Wheel Scroll") or
            _find_sequence(raw_events, i, mouse.MoveEvent, "Mouse Move")
        )

        if result:
            action, next_i = result
            actions.append(action)
            i = next_i
        else:
            # Fallback for single raw events
            evt_obj = _get_event_obj(raw_events[i])
            if isinstance(evt_obj, mouse.ButtonEvent):
                event_type_str = evt_obj.event_type.capitalize() if evt_obj.event_type else "Button"
                text = f"Mouse {event_type_str} ({evt_obj.button})"
                evt_type = 'raw_mouse'
            elif isinstance(evt_obj, keyboard.KeyboardEvent):
                event_type_str = "Up" if evt_obj.event_type == 'up' else "Down"
                key_name = evt_obj.name.capitalize() if evt_obj.name else ""
                text = f"Key {event_type_str}: {key_name}"
                evt_type = 'raw_key'
            else:
                text = f"Event: {evt_obj}"
                evt_type = 'raw'
            actions.append(GroupedAction(display_text=text, type=evt_type, start_index=i, end_index=i))
            i += 1
    return actions
