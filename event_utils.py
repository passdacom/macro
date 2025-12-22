import keyboard
import mouse

def get_event_obj(event):
    """Helper to extract the event object from a macro data entry."""
    return event[1]['obj']

def is_modifier_or_hotkey(key_name):
    if not key_name: return False
    key_name = key_name.lower()
    return key_name in ['f5', 'f6', 'f7', 'ctrl', 'alt', 'shift']

# --- Event Serialization/Deserialization Helpers ---
def serialize_event(event_data):
    event_time, data_dict = event_data
    event = data_dict['obj']
    pos = data_dict.get('pos')

    event_dict = {'time': event_time}
    # Add all other keys from the data_dict, like 'remarks' in the future
    for key, value in data_dict.items():
        if key not in ['obj', 'pos']:
            event_dict[key] = value

    if isinstance(event, keyboard.KeyboardEvent):
        event_dict['type'] = 'keyboard'
        event_dict['event_type'] = event.event_type
        event_dict['name'] = event.name
        event_dict['scan_code'] = event.scan_code
    elif isinstance(event, mouse.MoveEvent):
        event_dict['type'] = 'mouse_move'
        event_dict['x'] = event.x
        event_dict['y'] = event.y
    elif isinstance(event, mouse.ButtonEvent):
        event_dict['type'] = 'mouse_button'
        event_dict['event_type'] = event.event_type
        event_dict['button'] = event.button
        if pos: event_dict['pos'] = pos
    elif isinstance(event, mouse.WheelEvent):
        event_dict['type'] = 'mouse_wheel'
        event_dict['delta'] = event.delta
    else:
        return None
    return event_dict

def deserialize_event(event_dict):
    event_type = event_dict.get('type')
    event_time = event_dict['time']
    
    data_dict = {}
    event = None

    if event_type == 'keyboard':
        event = keyboard.KeyboardEvent(event_type=event_dict['event_type'], name=event_dict['name'], scan_code=event_dict.get('scan_code', -1))
    elif event_type == 'mouse_move':
        event = mouse.MoveEvent(event_dict['x'], event_dict['y'], event_dict['time'])
    elif event_type == 'mouse_button':
        event = mouse.ButtonEvent(event_type=event_dict['event_type'], button=event_dict['button'], time=event_dict['time'])
        if 'pos' in event_dict:
            data_dict['pos'] = event_dict['pos']
    elif event_type == 'mouse_wheel':
        event = mouse.WheelEvent(event_dict['delta'])
    
    if event:
        data_dict['obj'] = event
        # Restore any other metadata
        for key, value in event_dict.items():
            if key not in ['time', 'type', 'event_type', 'name', 'scan_code', 'x', 'y', 'button', 'pos', 'delta']:
                data_dict[key] = value
        return (event_time, data_dict)
    return None

def remove_redundant_paste_events(events):
    """
    Removes redundant Ctrl+V events that are automatically injected by Windows
    when using the Clipboard History (Win+V) menu.
    
    Logic:
    1. Detect 'Win+V' sequence.
    2. Look for a subsequent Mouse Click (Left Button Up) which selects the item.
    3. If a 'Ctrl+V' sequence follows immediately (e.g., < 0.2s) after the click, remove it.
    """
    if not events:
        return events

    cleaned_events = []
    skip_indices = set()
    
    win_v_detected_time = 0
    
    # Helper to check if event is Win key down
    def is_win_down(evt):
        return isinstance(evt, keyboard.KeyboardEvent) and \
               evt.event_type == 'down' and \
               evt.name in ('left windows', 'right windows', 'windows')

    # Helper to check if event is V key down
    def is_v_down(evt):
        return isinstance(evt, keyboard.KeyboardEvent) and \
               evt.event_type == 'down' and \
               evt.name == 'v'

    # Helper to check if event is Ctrl key down
    def is_ctrl_down(evt):
        return isinstance(evt, keyboard.KeyboardEvent) and \
               evt.event_type == 'down' and \
               evt.name in ('ctrl', 'left ctrl', 'right ctrl')

    # Helper to check if event is Mouse Left Click Up
    def is_mouse_click_up(evt):
        return isinstance(evt, mouse.ButtonEvent) and \
               evt.event_type == 'up' and \
               evt.button == 'left'

    for i in range(len(events)):
        if i in skip_indices:
            continue
            
        evt_time, evt_data = events[i]
        if 'obj' not in evt_data:
            cleaned_events.append(events[i])
            continue
            
        evt_obj = evt_data['obj']
        
        # 1. Detect Win+V
        # We look for Win down, then V down.
        if is_win_down(evt_obj):
            # Check next few events for 'v'
            for j in range(i + 1, min(i + 5, len(events))):
                next_obj = events[j][1]['obj']
                if is_v_down(next_obj):
                    win_v_detected_time = events[j][0]
                    break
        
        # 2. If Win+V was detected recently (e.g., within last 10 seconds), look for click
        if win_v_detected_time > 0 and (evt_time - win_v_detected_time) < 10.0:
            if is_mouse_click_up(evt_obj):
                # 3. Look for immediate Ctrl+V injection
                # Windows usually injects: Ctrl Down -> V Down -> V Up -> Ctrl Up
                # It happens very fast, usually within milliseconds of the click.
                
                potential_ctrl_idx = -1
                potential_v_idx = -1
                
                # Scan ahead a bit
                scan_limit = min(i + 10, len(events))
                for k in range(i + 1, scan_limit):
                    next_time, next_data = events[k]
                    next_obj = next_data['obj']
                    
                    # If too much time passed since click, abort search
                    if (next_time - evt_time) > 0.5: 
                        break
                        
                    if potential_ctrl_idx == -1 and is_ctrl_down(next_obj):
                        potential_ctrl_idx = k
                    elif potential_ctrl_idx != -1 and is_v_down(next_obj):
                        potential_v_idx = k
                        break # Found the pair
                
                if potential_ctrl_idx != -1 and potential_v_idx != -1:
                    # Found redundant paste! Mark the sequence for removal.
                    # We need to remove Ctrl Down, V Down, V Up, Ctrl Up
                    # Let's identify all 4 events.
                    
                    indices_to_remove = [potential_ctrl_idx, potential_v_idx]
                    
                    # Find V Up
                    for m in range(potential_v_idx + 1, scan_limit):
                        m_obj = events[m][1]['obj']
                        if isinstance(m_obj, keyboard.KeyboardEvent) and m_obj.event_type == 'up' and m_obj.name == 'v':
                            indices_to_remove.append(m)
                            break
                            
                    # Find Ctrl Up
                    for n in range(potential_ctrl_idx + 1, scan_limit):
                        n_obj = events[n][1]['obj']
                        if isinstance(n_obj, keyboard.KeyboardEvent) and n_obj.event_type == 'up' and n_obj.name in ('ctrl', 'left ctrl', 'right ctrl'):
                            indices_to_remove.append(n)
                            break
                            
                    skip_indices.update(indices_to_remove)
                    win_v_detected_time = 0 # Reset detection
                    
        cleaned_events.append(events[i])

    return cleaned_events

import ctypes

def get_pixel_color(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    # Color is BGR in Windows GDI
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    return (r, g, b)

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])
