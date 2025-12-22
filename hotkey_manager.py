
import keyboard
import threading
import time

class HotkeyManager:
    def __init__(self, on_record_hotkey, on_play_hotkey, on_stop_hotkey):
        self.on_record_hotkey = on_record_hotkey
        self.on_play_hotkey = on_play_hotkey
        self.on_stop_hotkey = on_stop_hotkey
        self.running = False

    def _listen(self):
        # Register hotkeys
        keyboard.add_hotkey('ctrl+alt+f5', self.on_record_hotkey)
        keyboard.add_hotkey('ctrl+alt+f6', self.on_play_hotkey)
        keyboard.add_hotkey('ctrl+alt+f7', self.on_stop_hotkey)

        # Keep the thread alive to listen for hotkeys
        while self.running:
            time.sleep(0.1)

        # Clean up hooks in the same thread that created them.
        keyboard.clear_all_hotkeys()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        # Wait for the listener thread to finish its cleanup.
        if self.thread:
            self.thread.join()
