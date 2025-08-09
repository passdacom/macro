
import time
import threading
import keyboard
import mouse

class Player:
    def __init__(self, on_finish_callback, log_callback=None, on_action_highlight_callback=None):
        self.on_finish_callback = on_finish_callback
        self.log_callback = log_callback if log_callback else lambda msg: None
        self.on_action_highlight_callback = on_action_highlight_callback if on_action_highlight_callback else lambda idx: None
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
                for event_list_idx in range(action.start_index, action.end_index + 1):
                    event_time, (event, recorded_pos) = events[event_list_idx]

                    current_delay = time.time() - start_time
                    wait_time = event_time - current_delay
                    sleep_duration = wait_time / speed_multiplier

                    if sleep_duration > 0:
                        time.sleep(sleep_duration)
                    else:
                        # 대기 시간이 없거나 이미 지났더라도, 다른 스레드(단축키 감지 등)가
                        # 실행될 수 있도록 CPU 제어권을 잠시 양보합니다.
                        time.sleep(0)

                    # --- Correct Event Playback Logic ---
                    if isinstance(event, keyboard.KeyboardEvent):
                        keyboard.play([event])
                    elif isinstance(event, mouse.MoveEvent):
                        if mode == 'relative':
                            offset_x = event.x - origin[0]
                            offset_y = event.y - origin[1]
                            mouse.move(current_pos_origin[0] + offset_x, current_pos_origin[1] + offset_y)
                        else:
                            mouse.move(event.x, event.y)
                    elif isinstance(event, mouse.ButtonEvent):
                        # If a position was recorded for this button event, move there first.
                        # This ensures that even if a preceding MoveEvent was deleted,
                        # the click happens at the correct recorded location.
                        if recorded_pos:
                            if mode == 'relative':
                                # In relative mode, calculate the target position based on
                                # the offset from the recording's origin, applied to the
                                # playback's starting position.
                                offset_x = recorded_pos[0] - origin[0]
                                offset_y = recorded_pos[1] - origin[1]
                                target_x = current_pos_origin[0] + offset_x
                                target_y = current_pos_origin[1] + offset_y
                                mouse.move(target_x, target_y)
                            else: # Absolute mode
                                mouse.move(recorded_pos[0], recorded_pos[1])

                        # Now perform the click/press/release action at the new cursor position
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
