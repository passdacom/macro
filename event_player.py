
import time
import threading
import keyboard
import mouse
from key_mapper_gui import SUGGESTED_TARGET_KEYS

class Player:
    def __init__(self, on_finish_callback, log_callback=None, on_action_highlight_callback=None, mapper_manager=None):
        self.on_finish_callback = on_finish_callback
        self.log_callback = log_callback if log_callback else lambda msg: None
        self.on_action_highlight_callback = on_action_highlight_callback if on_action_highlight_callback else lambda idx: None
        # mapper_manager is no longer needed by the player
        self.playing = False
        self.thread = None

    def _play_events_task(self, macro_data, repeat_count, speed_multiplier):
        self.playing = True
        events = macro_data.get('events', [])
        mode = macro_data.get('mode', 'absolute')
        origin = macro_data.get('origin', (0, 0))

        # Group events for playback highlighting
        import event_grouper # Import here to avoid circular dependency
        grouped_actions = event_grouper.group_events(events)

        for i in range(repeat_count):
            if not self.playing:
                break

            current_pos_origin = mouse.get_position()
            start_time = time.time()
            
            # Iterate through grouped actions for playback
            for action_idx, action in enumerate(grouped_actions):
                if not self.playing:
                    break

                # Highlight the current action in the UI
                self.on_action_highlight_callback(action_idx)

                # Play all raw events within this grouped action
                for event_list_idx in action.indices:
                    if not self.playing: break
                    
                    event_time, event_data = events[event_list_idx]
                    event = event_data['obj']
                    recorded_pos = event_data.get('pos')

                    current_delay = time.time() - start_time
                    wait_time = event_time - current_delay
                    sleep_duration = wait_time / speed_multiplier

                    if sleep_duration > 0:
                        time.sleep(sleep_duration)
                    else:
                        time.sleep(0)

                    # --- Correct Event Playback Logic ---
                    if isinstance(event, keyboard.KeyboardEvent):
                        # If the key is a special 'virtual' key, use its original scan code to play.
                        if event.name in SUGGESTED_TARGET_KEYS:
                            if event.event_type == 'down':
                                self.log_callback(f"Playing virtual key '{event.name}' using scan code {event.scan_code}")
                                keyboard.press_and_release(event.scan_code)
                            # Ignore 'up' event for virtual keys
                            continue

                        # For all other normal keys, play by name.
                        if event.event_type == 'down':
                            keyboard.press(event.name)
                        elif event.event_type == 'up':
                            keyboard.release(event.name)
                            
                    elif isinstance(event, mouse.MoveEvent):
                        if mode == 'relative':
                            offset_x = event.x - origin[0]
                            offset_y = event.y - origin[1]
                            mouse.move(current_pos_origin[0] + offset_x, current_pos_origin[1] + offset_y)
                        else:
                            mouse.move(event.x, event.y)
                    elif isinstance(event, mouse.ButtonEvent):
                        if recorded_pos:
                            if mode == 'relative':
                                offset_x = recorded_pos[0] - origin[0]
                                offset_y = recorded_pos[1] - origin[1]
                                target_x = current_pos_origin[0] + offset_x
                                target_y = current_pos_origin[1] + offset_y
                                mouse.move(target_x, target_y)
                            else: # Absolute mode
                                mouse.move(recorded_pos[0], recorded_pos[1])

                        if event.event_type == mouse.DOUBLE:
                            mouse.double_click(event.button)
                        elif event.event_type == mouse.DOWN:
                            mouse.press(event.button)
                        elif event.event_type == mouse.UP:
                            mouse.release(event.button)
                    elif isinstance(event, mouse.WheelEvent):
                        mouse.wheel(event.delta)

            if self.playing and i < repeat_count - 1:
                time.sleep(0.5)

        self.playing = False
        self.on_action_highlight_callback(-1) # Clear highlight when finished
        if self.on_finish_callback:
            self.on_finish_callback()

    def play_events(self, macro_data, repeat_count=1, speed_multiplier=1.0):
        if self.playing:
            return

        if not macro_data or not macro_data.get('events'):
            if self.on_finish_callback:
                self.on_finish_callback()
            return

        self.thread = threading.Thread(target=self._play_events_task, args=(macro_data, repeat_count, speed_multiplier), daemon=True)
        self.thread.start()

    def stop_playing(self):
        if not self.playing:
            return
        self.playing = False
