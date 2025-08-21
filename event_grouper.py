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

def _get_event_time(event): return event[0]
def _get_event_obj(event): return event[1][0]

# --- Main Grouper Function (Final Algorithm) ---
def group_events(raw_events: list) -> list[GroupedAction]:
    if not raw_events:
        return []

    actions = []
    processed_indices = set()
    
    # Pass 1: Group sequential mouse events first (Click, Drag, Move, Wheel)
    i = 0
    while i < len(raw_events):
        if i in processed_indices:
            i += 1
            continue

        current_event = _get_event_obj(raw_events[i])
        
        # Mouse Click/Drag
        if isinstance(current_event, mouse.ButtonEvent) and current_event.event_type == 'down':
            is_drag = False
            end_index = -1
            # Find the corresponding 'up' event
            for j in range(i + 1, len(raw_events)):
                evt = _get_event_obj(raw_events[j])
                if isinstance(evt, mouse.MoveEvent):
                    is_drag = True
                elif isinstance(evt, mouse.ButtonEvent) and evt.button == current_event.button and evt.event_type == 'up':
                    end_index = j
                    break
            
            if end_index != -1:
                action_type = 'mouse_drag' if is_drag else 'mouse_click'
                text = f"Mouse Drag ({current_event.button})" if is_drag else f"Mouse Click ({current_event.button})"
                indices = list(range(i, end_index + 1))
                actions.append(GroupedAction(display_text=text, type=action_type, start_index=i, indices=indices))
                processed_indices.update(indices)
                i = end_index + 1
                continue

        # Mouse Move/Wheel Sequence
        if isinstance(current_event, (mouse.MoveEvent, mouse.WheelEvent)):
            event_type = type(current_event)
            end_index = i
            for j in range(i + 1, len(raw_events)):
                if type(_get_event_obj(raw_events[j])) is not event_type or (_get_event_time(raw_events[j]) - _get_event_time(raw_events[j-1])) > HUMAN_PAUSE_THRESHOLD:
                    break
                end_index = j
            
            action_type = 'mouse_wheel' if event_type is mouse.WheelEvent else 'mouse_move'
            text = "Mouse Wheel" if event_type is mouse.WheelEvent else "Mouse Move"
            indices = list(range(i, end_index + 1))
            actions.append(GroupedAction(display_text=text, type=action_type, start_index=i, indices=indices))
            processed_indices.update(indices)
            i = end_index + 1
            continue
        
        i += 1

    # Pass 2: Group all remaining keyboard events statefully
    down_events = {}
    for i, (t, (evt, p)) in enumerate(raw_events):
        if i in processed_indices: continue

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
        i += 1

    # Final sort to ensure chronological order
    actions.sort(key=lambda x: x.start_index)
    return actions
