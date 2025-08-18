
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
            # If a non-keyboard event occurs, the shortcut attempt is over.
            # We check if it was a valid shortcut up to the previous event.
            if not pressed_keys:
                return None
            # Find the real end of the shortcut (last key up)
            final_end = j - 1
            text = f"Shortcut: {" + ".join(sorted(list(active_modifiers)))} + {" + ".join(sorted(list(pressed_keys)))}"
            return GroupedAction(display_text=text, type='shortcut', start_index=i, end_index=final_end), final_end + 1

        if not active_modifiers: # All modifiers have been released
            if not pressed_keys:
                return None # It was just a modifier tap, not a shortcut
            
            mods_at_time_of_press = sorted([k.capitalize() for k in active_modifiers.union({start_event.name.lower()})])
            keys_at_time_of_press = sorted([k.capitalize() for k in pressed_keys])

            text = f"Shortcut: {" + ".join(mods_at_time_of_press)} + {" + ".join(keys_at_time_of_press)}"
            return GroupedAction(display_text=text, type='shortcut', start_index=i, end_index=j), j + 1

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
            action_type = 'mouse_drag' if is_drag else 'mouse_click'
            text = f"Mouse Drag ({start_event.button})" if is_drag else f"Mouse Click ({start_event.button})"
            return GroupedAction(display_text=text, type=action_type, start_index=i, end_index=j), j + 1
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

    action_type = 'mouse_wheel' if event_type is mouse.WheelEvent else 'mouse_move'
    return GroupedAction(display_text=display_name, type=action_type, start_index=i, end_index=end_index), end_index + 1

def _find_typing_sequence(events, i):
    typed_string = ""
    end_index = i
    shift_pressed = False
    start_event_obj = _get_event_obj(events[i])

    # The sequence must start with a printable key press
    if not (isinstance(start_event_obj, keyboard.KeyboardEvent) and start_event_obj.event_type == 'down'):
        return None

    # A typing sequence should not be confused with a shortcut
    if _is_modifier(start_event_obj.name):
        return None

    temp_end_index = i
    for j in range(i, len(events)):
        current_event_time = _get_event_time(events[j])
        evt = _get_event_obj(events[j])

        # Check for pause between events
        if j > temp_end_index:
            prev_event_time = _get_event_time(events[temp_end_index])
            if (current_event_time - prev_event_time) > HUMAN_PAUSE_THRESHOLD:
                break

        if isinstance(evt, keyboard.KeyboardEvent):
            if not evt.name: continue
            key_name = evt.name.lower()

            if key_name == 'shift':
                shift_pressed = (evt.event_type == 'down')
                # This is part of the typing sequence, but doesn't advance the end_index itself
                continue

            # Break on non-printable keys (except space)
            if len(key_name) > 1 and key_name != 'space':
                break

            if evt.event_type == 'down':
                # Find the matching 'up' event to form a full key press
                found_up = False
                for k in range(j + 1, len(events)):
                    # Check for interruption before the 'up' event
                    interruption = False
                    for l in range(j + 1, k):
                        inter_evt = _get_event_obj(events[l])
                        if not isinstance(inter_evt, mouse.MoveEvent):
                            interruption = True
                            break
                    if interruption:
                        break

                    up_evt = _get_event_obj(events[k])
                    if isinstance(up_evt, keyboard.KeyboardEvent) and up_evt.name.lower() == key_name and up_evt.event_type == 'up':
                        char = key_name
                        if key_name == 'space':
                            char = ' '
                        
                        if shift_pressed:
                            if len(char) == 1 and 'a' <= char <= 'z':
                                char = char.upper()
                            # A more complete implementation would map all keys
                        
                        typed_string += char
                        temp_end_index = k # The action ends at the key up
                        found_up = True
                        break
                
                if found_up:
                    j = temp_end_index # Continue search from after the found 'up' event
                else:
                    break # If no matching up event, it's not a clean press, so sequence ends.
            else:
                # an 'up' event without a preceding 'down' in the sequence, break
                break
        else:
            # Break on any non-keyboard event (e.g., mouse)
            break
    
    # Only create a group if we have a meaningful string (more than 1 char)
    if len(typed_string) > 1:
        # The final end_index is the end of the last valid key press
        end_index = temp_end_index
        return GroupedAction(display_text=f'Typing: "{typed_string}"', type='typing', start_index=i, end_index=end_index), end_index + 1
    
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
            _find_typing_sequence(raw_events, i) or
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
                        text = f"Key Press: {evt_obj.name.capitalize() if evt_obj.name else 'None'}"
                        actions.append(GroupedAction(display_text=text, type='key_press', start_index=i, end_index=j))
                        i = j + 1
                        break
                else: # No matching up event found, treat as single down
                    text = f"Key Down: {evt_obj.name.capitalize() if evt_obj.name else 'None'}"
                    actions.append(GroupedAction(display_text=text, type='raw_key', start_index=i, end_index=i))
                    i += 1
            else:
                # If still no pattern matches, treat as a single raw event
                evt_obj = _get_event_obj(raw_events[i])
                if isinstance(evt_obj, mouse.ButtonEvent):
                    event_type_str = evt_obj.event_type.capitalize() if evt_obj.event_type else "Button"
                    text = f"Mouse {event_type_str} ({evt_obj.button})"
                    evt_type = 'raw_mouse'
                else:
                    evt_type = 'raw_mouse' if isinstance(evt_obj, (mouse.MoveEvent, mouse.WheelEvent)) else 'raw_key' if isinstance(evt_obj, keyboard.KeyboardEvent) else 'raw'
                    text = f"Event: {evt_obj}"
                actions.append(GroupedAction(display_text=text, type=evt_type, start_index=i, end_index=i))
                i += 1
    return actions
