import time
import threading
import keyboard
import mouse

NUMPAD_SCAN_CODES = {
    79: {'name': '1', 'scan_code': 2},
    80: {'name': '2', 'scan_code': 3},
    81: {'name': '3', 'scan_code': 4},
    75: {'name': '4', 'scan_code': 5},
    76: {'name': '5', 'scan_code': 6},
    77: {'name': '6', 'scan_code': 7},
    71: {'name': '7', 'scan_code': 8},
    72: {'name': '8', 'scan_code': 9},
    73: {'name': '9', 'scan_code': 10},
    82: {'name': '0', 'scan_code': 11},
    83: {'name': '.', 'scan_code': 52},
}

class Recorder:
    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.recording = False
        self.events = []
        self.start_time = 0
        self.origin_pos = (0, 0)
        self.coordinate_mode = 'absolute'
        self.keyboard_hook = None
        self.mouse_hook = None
        self.button_to_ignore_up = None

    def _record_event(self, event):
        if not self.recording:
            return

        if isinstance(event, keyboard.KeyboardEvent) and event.scan_code in NUMPAD_SCAN_CODES:
            mapping = NUMPAD_SCAN_CODES[event.scan_code]
            event = keyboard.KeyboardEvent(event.event_type, mapping['scan_code'], name=mapping['name'])
            self.log_callback(f"Normalized numpad key to '{mapping['name']}'.")

        if isinstance(event, mouse.ButtonEvent) and event.event_type == mouse.UP and event.button == self.button_to_ignore_up:
            self.button_to_ignore_up = None
            return

        event_time = time.time() - self.start_time

        if isinstance(event, mouse.ButtonEvent) and event.event_type == mouse.DOUBLE:
            last_button_up = None
            for i in range(len(self.events) - 1, -1, -1):
                _, (evt, _) = self.events[i]
                if isinstance(evt, mouse.ButtonEvent) and evt.event_type == mouse.UP:
                    last_button_up = evt.button
                    break
            
            if last_button_up and last_button_up != event.button:
                self.log_callback(f"Correcting spurious double-click event for '{event.button}' button.")
                event = mouse.ButtonEvent(event_type=mouse.DOWN, button=event.button, time=event.time)
            else:
                last_up_index = -1
                last_down_index = -1
                for i in range(len(self.events) - 1, -1, -1):
                    _, (evt, _) = self.events[i]
                    if isinstance(evt, mouse.ButtonEvent) and evt.button == event.button:
                        if evt.event_type == mouse.UP and last_up_index == -1:
                            last_up_index = i
                        elif evt.event_type == mouse.DOWN and last_down_index == -1:
                            last_down_index = i
                            break
                
                if last_down_index != -1 and last_up_index != -1:
                    self.log_callback(f"Double-click detected for '{event.button}' button. Cleaning up previous click event.")
                    del self.events[last_up_index]
                    del self.events[last_down_index]
                
                self.button_to_ignore_up = event.button

        pos = mouse.get_position() if isinstance(event, mouse.ButtonEvent) else None
        event_to_store = (event, pos)
        self.events.append((event_time, event_to_store))

        if not isinstance(event, mouse.MoveEvent):
            if isinstance(event, keyboard.KeyboardEvent):
                log_msg = f"KeyboardEvent(name='{event.name}', scan_code={event.scan_code}, event_type={event.event_type})"
                self.log_callback(log_msg)
            else:
                self.log_callback(f"Event: {event}")

    def _keyboard_handler(self, event):
        self._record_event(event)

    def _mouse_handler(self, event):
        self._record_event(event)

    def _start_listeners(self):
        self.keyboard_hook = keyboard.hook(self._keyboard_handler)
        self.mouse_hook = mouse.hook(self._mouse_handler)
        
        while self.recording:
            time.sleep(0.1)
        
        keyboard.unhook(self.keyboard_hook)
        mouse.unhook(self.mouse_hook)

    def start_recording(self, coordinate_mode='absolute'):
        if self.recording:
            self.log_callback("Already recording.")
            return

        self.recording = True
        self.events = []
        self.start_time = time.time()
        self.coordinate_mode = coordinate_mode
        self.button_to_ignore_up = None

        if self.coordinate_mode == 'relative':
            self.origin_pos = mouse.get_position()
            self.log_callback(f"Recording started in relative mode (Origin: {self.origin_pos})...")
        else:
            self.log_callback("Recording started in absolute mode...")

        self.thread = threading.Thread(target=self._start_listeners, daemon=True)
        self.thread.start()

    def stop_recording(self):
        if not self.recording:
            self.log_callback("Not recording.")
            return None

        self.recording = False
        if self.thread:
            self.thread.join()

        self.log_callback("Recording stopped.")
        return {
            'events': self.events,
            'mode': self.coordinate_mode,
            'origin': self.origin_pos
        }