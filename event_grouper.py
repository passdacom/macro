from dataclasses import dataclass
import keyboard
import mouse

@dataclass(kw_only=True)
class GroupedAction:
    display_text: str
    start_index: int
    indices: list[int]
    type: str

# --- Constants and Helpers ---
HUMAN_PAUSE_THRESHOLD = 0.7
MODIFIER_KEYS = {'ctrl', 'alt', 'shift', 'cmd', 'win'}

def _get_event_time(event): return event[0]
def _get_event_obj(event): return event[1]['obj']
def _is_modifier(key_name): return key_name and key_name.lower() in MODIFIER_KEYS

# --- Pattern Finder Functions ---

def _find_shortcut(events, i, processed_indices):
    if i in processed_indices: return None
    start_event = _get_event_obj(events[i])
    if not (isinstance(start_event, keyboard.KeyboardEvent) and start_event.event_type == 'down' and _is_modifier(start_event.name)):
        return None

    active_modifiers = {start_event.name.lower()}
    pressed_action_keys = set()
    end_index = i
    temp_indices = {i}

    for j in range(i + 1, len(events)):
        if j in processed_indices: continue
        evt = _get_event_obj(events[j])
        is_mouse_interruption = isinstance(evt, mouse.ButtonEvent)
        if is_mouse_interruption: break

        if isinstance(evt, keyboard.KeyboardEvent):
            if not evt.name: continue
            key_name = evt.name.lower()
            temp_indices.add(j)

            if evt.event_type == 'down':
                if _is_modifier(key_name): active_modifiers.add(key_name)
                else: pressed_action_keys.add(key_name)
            elif evt.event_type == 'up':
                if _is_modifier(key_name): active_modifiers.discard(key_name)
        
        end_index = j
        if not active_modifiers:
            break
    
    if not pressed_action_keys:
        return None

    mod_text = " + ".join(sorted([k.capitalize() for k in active_modifiers.union({start_event.name.lower()})]))
    key_text = " + ".join(sorted([k.capitalize() for k in pressed_action_keys]))
    text = f"Shortcut: {mod_text} + {key_text}"
    
    indices = sorted(list(temp_indices))
    return GroupedAction(display_text=text, type='shortcut', start_index=i, indices=indices), indices

def _find_mouse_action(events, i, processed_indices):
    if i in processed_indices: return None
    start_event = _get_event_obj(events[i])
    if not isinstance(start_event, mouse.ButtonEvent) or start_event.event_type != 'down':
        return None

    is_drag = False
    end_index = -1
    temp_indices = {i}
    for j in range(i + 1, len(events)):
        if j in processed_indices: continue
        evt = _get_event_obj(events[j])
        temp_indices.add(j)
        if isinstance(evt, mouse.MoveEvent):
            is_drag = True
        elif isinstance(evt, mouse.ButtonEvent) and evt.button == start_event.button and evt.event_type == 'up':
            end_index = j
            break
    
    if end_index != -1:
        action_type = 'mouse_drag' if is_drag else 'mouse_click'
        text = f"Mouse Drag ({start_event.button})" if is_drag else f"Mouse Click ({start_event.button})"
        indices = sorted(list(temp_indices))
        return GroupedAction(display_text=text, type=action_type, start_index=i, indices=indices), indices
    return None

def _find_mouse_sequence(events, i, processed_indices):
    if i in processed_indices: return None
    start_event = _get_event_obj(events[i])
    if not isinstance(start_event, (mouse.MoveEvent, mouse.WheelEvent)):
        return None
    
    event_type = type(start_event)
    end_index = i
    for j in range(i + 1, len(events)):
        if j in processed_indices or type(_get_event_obj(events[j])) is not event_type or (_get_event_time(events[j]) - _get_event_time(events[j-1])) > HUMAN_PAUSE_THRESHOLD:
            break
        end_index = j

    action_type = 'mouse_wheel' if event_type is mouse.WheelEvent else 'mouse_move'
    text = "Mouse Wheel" if event_type is mouse.WheelEvent else "Mouse Move"
    indices = list(range(i, end_index + 1))
    return GroupedAction(display_text=text, type=action_type, start_index=i, indices=indices), indices

# --- Main Grouper Function ---
def group_events(raw_events: list) -> list[GroupedAction]:
    if not raw_events:
        return []

    actions = []
    processed_indices = set()
    
    # Pass 1: Find complex and sequential patterns first
    i = 0
    while i < len(raw_events):
        if i in processed_indices: 
            i += 1
            continue
        
        result = (
            _find_shortcut(raw_events, i, processed_indices) or 
            _find_mouse_action(raw_events, i, processed_indices) or
            _find_mouse_sequence(raw_events, i, processed_indices)
        )
        
        if result:
            action, indices = result
            actions.append(action)
            processed_indices.update(indices)
            i = indices[-1] + 1
        else:
            i += 1

    # Pass 2: Group remaining keyboard events statefully (handles interleaving)
    down_events = {}
    for i, event_tuple in enumerate(raw_events):
        if i in processed_indices: continue

        evt = _get_event_obj(event_tuple)
        if isinstance(evt, keyboard.KeyboardEvent):
            if evt.event_type == 'down' and evt.scan_code is not None:
                down_events[evt.scan_code] = i
            elif evt.event_type == 'up' and evt.scan_code in down_events:
                start_idx = down_events.pop(evt.scan_code)
                end_idx = i
                down_evt_obj = _get_event_obj(raw_events[start_idx])
                text = f"Key Press: {down_evt_obj.name.capitalize() if down_evt_obj.name else ''}"
                actions.append(GroupedAction(display_text=text, type='key_press', start_index=start_idx, indices=[start_idx, end_idx]))
                processed_indices.add(start_idx)
                processed_indices.add(end_idx)

    # Pass 3: Handle any remaining raw events
    i = 0
    while i < len(raw_events):
        if i in processed_indices: 
            i += 1
            continue
        evt_obj = _get_event_obj(raw_events[i])
        text = f"Event: {evt_obj}"
        actions.append(GroupedAction(display_text=text, type='raw', start_index=i, indices=[i]))
        processed_indices.add(i) # Mark as processed
        i += 1

    # Final sort to ensure chronological order
    actions.sort(key=lambda x: x.start_index)
    return actions