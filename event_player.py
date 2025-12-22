import time
import threading
import keyboard
import mouse
from collections import deque
from key_mapper_gui import SUGGESTED_TARGET_KEYS
import event_utils
import sounddevice as sd
import numpy as np

class Player:
    def __init__(self, on_finish_callback, log_callback=None, on_action_highlight_callback=None, mapper_manager=None):
        self.on_finish_callback = on_finish_callback
        self.log_callback = log_callback if log_callback else lambda msg: None
        self.on_action_highlight_callback = on_action_highlight_callback if on_action_highlight_callback else lambda idx: None
        # mapper_manager is no longer needed by the player
        self.playing = False
        self.thread = None
        self.esc_press_times = deque(maxlen=3)  # Track last 3 ESC presses
        self.esc_listener_hook = None

    def _esc_emergency_stop(self, event):
        """Callback for ESC key detection during playback"""
        if event.name == 'esc' and event.event_type == 'down':
            current_time = time.time()
            self.esc_press_times.append(current_time)
            
            # Check if we have 3 ESC presses within 0.5 seconds
            if len(self.esc_press_times) == 3:
                if (self.esc_press_times[-1] - self.esc_press_times[0]) < 0.5:
                    self.log_callback("EMERGENCY STOP: ESC pressed 3 times rapidly!")
                    self.playing = False

    def play_events(self, macro_data, repeat_count=1, speed_multiplier=1.0, stop_on_sound=False, prudent_mode=False):
        if self.playing:
            return
        
        self.thread = threading.Thread(target=self._play_events_task, args=(macro_data, repeat_count, speed_multiplier, stop_on_sound, prudent_mode))
        self.thread.start()

    def stop_playing(self):
        self.playing = False
        if self.esc_listener_hook:
            keyboard.unhook(self.esc_listener_hook)
            self.esc_listener_hook = None
        self.log_callback("Stopping playback...")

    def _play_events_task(self, macro_data, repeat_count, speed_multiplier, stop_on_sound, prudent_mode):
        self.playing = True
        self.esc_press_times.clear()
        events = macro_data.get('events', [])
        mode = macro_data.get('mode', 'absolute')
        origin = macro_data.get('origin', (0, 0))

        # Set up ESC emergency stop listener
        self.esc_listener_hook = keyboard.on_press(self._esc_emergency_stop)

        # Group events for playback highlighting
        grouped_actions = macro_data.get('grouped_actions')
        if not grouped_actions:
            import event_grouper # Import here to avoid circular dependency
            grouped_actions = event_grouper.group_events(events)
        
        # Stop on Sound Monitor
        if stop_on_sound:
            def sound_monitor():
                try:
                    # Using default input. Ensure 'Stereo Mix' is enabled in Windows Sound Settings for system audio.
                    with sd.InputStream(channels=1, blocksize=1024) as stream:
                        self.log_callback("Sound monitor active (Threshold: 0.02).")
                        while self.playing:
                            data, overflow = stream.read(1024)
                            if len(data) == 0: continue
                            volume = np.abs(data).mean()
                            
                            if volume > 0.02: # Sensitive threshold
                                self.log_callback(f"Sound detected (Vol: {volume:.4f})! Stopping.")
                                self.playing = False
                                break
                except Exception as e:
                    self.log_callback(f"Sound monitor error: {e}")
            threading.Thread(target=sound_monitor, daemon=True).start()

        learned_colors = {} # Key: action_idx, Value: hex_color

        try:
            for i in range(repeat_count):
                if not self.playing:
                    break
                
                # Log repeat progress if repeat_count > 1
                if repeat_count > 1:
                    self.log_callback(f"Playing: {i + 1}/{repeat_count}")

                current_pos_origin = mouse.get_position()
                start_time = time.time()
                
                # Use while loop for control flow
                idx = 0
                loop_stack = []
                self.time_offset = 0 # Initialize time offset for Wait actions
                while idx < len(grouped_actions):
                    if not self.playing: break
                    
                    action = grouped_actions[idx]
                    action_idx = idx # Use index as ID for learning colors
                    
                    # Highlight the current action in the UI
                    self.on_action_highlight_callback(action_idx)

                    # --- Universal Timing Logic ---
                    # Ensure EVERY action waits for its scheduled start time relative to the macro timeline.
                    # We skip this for 'loop_end' to allow immediate looping.
                    if action.type != 'loop_end':
                        # Current macro time = Real elapsed time - Pauses (time_offset)
                        current_macro_time = time.time() - start_time - self.time_offset
                        wait_time = action.start_time - current_macro_time
                        sleep_duration = wait_time / speed_multiplier
                        
                        if sleep_duration > 0:
                            time.sleep(sleep_duration)

                    # --- Logic Actions ---
                    if action.type == 'loop_start':
                        count = action.details.get('count', 0)
                        if not loop_stack or loop_stack[-1]['start_idx'] != idx:
                            loop_stack.append({'start_idx': idx, 'count': count, 'current': 0})
                            self.log_callback(f"Loop Start: {count if count > 0 else 'Infinite'}")
                        idx += 1
                        continue
                    elif action.type == 'loop_end':
                        if loop_stack:
                            ctx = loop_stack[-1]
                            ctx['current'] += 1
                            if ctx['count'] == 0 or ctx['current'] < ctx['count']:
                                idx = ctx['start_idx'] + 1
                                self.log_callback(f"Looping back... ({ctx['current']}/{ctx['count'] if ctx['count']>0 else 'Inf'})")
                                continue
                            else:
                                self.log_callback("Loop finished.")
                                loop_stack.pop()
                        idx += 1
                        continue
                    elif action.type == 'wait_color':
                        target_hex = action.details.get('target_hex')
                        x = action.details.get('x')
                        y = action.details.get('y')
                        timeout = action.details.get('timeout', 10)
                        
                        start_wait = time.time()
                        self.log_callback(f"Waiting for color {target_hex} at ({x}, {y})...")
                        
                        # Move mouse to target pixel
                        try:
                            mouse.move(x, y)
                        except Exception as e:
                            self.log_callback(f"Failed to move mouse: {e}")

                        while True:
                            if not self.playing: break
                            rgb = event_utils.get_pixel_color(x, y)
                            current_hex = event_utils.rgb_to_hex(rgb)
                            if current_hex.lower() == target_hex.lower():
                                self.log_callback("Color matched!")
                                break
                            if time.time() - start_wait > timeout:
                                self.log_callback("Wait Color Timeout! Stopping macro.")
                                self.playing = False
                                break
                            time.sleep(0.1)
                        
                        # Update time offset
                        elapsed = time.time() - start_wait
                        self.time_offset += elapsed
                        
                        # Post-Match Delay
                        post_delay = action.details.get('post_delay', 0)
                        if post_delay > 0:
                            self.log_callback(f"Post-match delay: {post_delay}s")
                            time.sleep(post_delay)
                            self.time_offset += post_delay

                        idx += 1
                        continue
                    elif action.type == 'wait_sound':
                        threshold = action.details.get('threshold', 0.1)
                        timeout = action.details.get('timeout', 10)
                        self.log_callback(f"Waiting for sound (Threshold: {threshold})...")
                        start_wait = time.time()
                        elapsed = time.time() - start_wait
                        self.time_offset += elapsed

                        # Post-Match Delay
                        post_delay = action.details.get('post_delay', 0)
                        if post_delay > 0:
                            self.log_callback(f"Post-match delay: {post_delay}s")
                            time.sleep(post_delay)
                            self.time_offset += post_delay

                        idx += 1
                        continue

                    # --- Action-Aware Playback Logic (High-Level) ---
                    # Prudent Mode Helper
                    def check_prudent(target_x, target_y):
                        if not prudent_mode: return True
                        
                        # Move first
                        # mouse.move(target_x, target_y)
                        time.sleep(0.05)
                        
                        rgb = event_utils.get_pixel_color(target_x, target_y)
                        current_hex = event_utils.rgb_to_hex(rgb)
                        
                        if i == 0: # Learning phase (First iteration of repeat loop)
                            learned_colors[action_idx] = current_hex
                            return True
                        else: # Verification phase
                            expected = learned_colors.get(action_idx)
                            if expected and current_hex != expected:
                                self.log_callback(f"Prudent Mode: Color mismatch! Expected {expected}, Got {current_hex}")
                                # Retry 3 times
                                for _ in range(3):
                                    time.sleep(0.5)
                                    rgb = event_utils.get_pixel_color(target_x, target_y)
                                    current_hex = event_utils.rgb_to_hex(rgb)
                                    if current_hex == expected:
                                        self.log_callback("Prudent Mode: Color matched after retry.")
                                        return True
                                
                                self.log_callback("Prudent Mode: Mismatch persists. Stopping.")
                                self.playing = False
                                return False
                        return True

                    # For special actions, perform a high-level command
                    if action.type in ('mouse_click', 'mouse_double_click', 'mouse_triple_click', 'mouse_drag'):
                        details = action.details
                        button = details.get('button', 'left')
                        pos = details.get('start_pos')
                        
                        if action.type == 'mouse_drag':
                            if pos:
                                mouse.move(pos[0], pos[1])
                                if not check_prudent(pos[0], pos[1]): break
                                end_pos = details.get('end_pos')
                                self.log_callback(f"Player: Executing high-level drag.")
                                mouse.drag(pos[0], pos[1], end_pos[0], end_pos[1], absolute=True, duration=0.2)
                        else:
                            if pos:
                                mouse.move(pos[0], pos[1])
                                if not check_prudent(pos[0], pos[1]): break
                            
                            if action.type == 'mouse_click':
                                mouse.click(button)
                            elif action.type == 'mouse_double_click':
                                self.log_callback(f"Player: Executing high-level double-click.")
                                mouse.double_click(button)
                            elif action.type == 'mouse_triple_click':
                                self.log_callback(f"Player: Executing high-level triple-click.")
                                mouse.double_click(button)
                                time.sleep(0.05)
                                mouse.click(button)
                        
                        idx += 1
                        continue # Skip the raw event loop for this action

                    # Fallback to playing raw events for other action types
                    for event_list_idx in action.indices:
                        if not self.playing: break
                        
                        event_time, event_data = events[event_list_idx]
                        event = event_data['obj']
                        recorded_pos = event_data.get('pos')

                        # Internal timing for raw events
                        # Must subtract time_offset!
                        current_delay = time.time() - start_time - self.time_offset
                        wait_time = event_time - current_delay
                        sleep_duration = wait_time / speed_multiplier

                        if sleep_duration > 0:
                            # Improve stability for very low delays (prevent OS timer resolution issues)
                            time.sleep(max(sleep_duration, 0.001))

                        # --- Raw Event Playback Logic ---
                        if isinstance(event, keyboard.KeyboardEvent):
                            # Fix for Numpad Decimal being recorded as 'decimal' but not playing back correctly
                            if event.name == 'decimal':
                                if event.event_type == 'down':
                                    keyboard.press('.')
                                elif event.event_type == 'up':
                                    keyboard.release('.')
                                continue

                            if event.name in SUGGESTED_TARGET_KEYS:
                                if event.event_type == 'down':
                                    keyboard.press_and_release(event.scan_code)
                                continue
                            if event.event_type == 'down':
                                if event.name in ('left windows', 'right windows', 'win') or (len(event.name) == 1 and event.name.isdigit()) or event.name.startswith('numpad'):
                                    keyboard.press(event.name)
                                elif hasattr(event, 'scan_code') and event.scan_code != -1:
                                    keyboard.press(event.scan_code)
                                else:
                                    keyboard.press(event.name)
                            elif event.event_type == 'up':
                                if event.name in ('left windows', 'right windows', 'win') or (len(event.name) == 1 and event.name.isdigit()) or event.name.startswith('numpad'):
                                    keyboard.release(event.name)
                                elif hasattr(event, 'scan_code') and event.scan_code != -1:
                                    keyboard.release(event.scan_code)
                                else:
                                    keyboard.release(event.name)
                                
                        elif isinstance(event, mouse.MoveEvent):
                            if mode == 'relative':
                                offset_x = event.x - origin[0]
                                offset_y = event.y - origin[1]
                                mouse.move(current_pos_origin[0] + offset_x, current_pos_origin[1] + offset_y)
                            else:
                                mouse.move(event.x, event.y)
                        elif isinstance(event, mouse.ButtonEvent):
                            if event.event_type == 'down':
                                mouse.press(event.button)
                            elif event.event_type == 'up':
                                mouse.release(event.button)
                        elif isinstance(event, mouse.WheelEvent):
                            mouse.wheel(event.delta)
                    
                    idx += 1

        except Exception as e:
            self.log_callback(f"Error during playback: {e}")
        finally:
            self.playing = False
            if self.esc_listener_hook:
                keyboard.unhook(self.esc_listener_hook)
                self.esc_listener_hook = None
            self.on_finish_callback()
