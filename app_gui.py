import tkinter as tk
from tkinter import ttk, scrolledtext, Menu, filedialog, messagebox
import json
import time
import keyboard
import mouse
from event_recorder import Recorder
from event_player import Player
from hotkey_manager import HotkeyManager
import event_grouper

# --- Event Serialization/Deserialization Helpers ---
def _serialize_event(event_data):
    event_time, (event, pos) = event_data
    event_dict = {'time': event_time}
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
        event_dict['pos'] = pos
    elif isinstance(event, mouse.WheelEvent):
        event_dict['type'] = 'mouse_wheel'
        event_dict['delta'] = event.delta
    else:
        return None
    return event_dict

def _deserialize_event(event_dict):
    event_type = event_dict.get('type')
    event_time = event_dict['time']
    pos = None
    event = None
    if event_type == 'keyboard':
        event = keyboard.KeyboardEvent(event_type=event_dict['event_type'], name=event_dict['name'], scan_code=event_dict['scan_code'])
    elif event_type == 'mouse_move':
        event = mouse.MoveEvent(event_dict['x'], event_dict['y'], event_dict['time'])
    elif event_type == 'mouse_button':
        event = mouse.ButtonEvent(event_type=event_dict['event_type'], button=event_dict['button'], time=event_dict['time'])
        pos = event_dict.get('pos')
    elif event_type == 'mouse_wheel':
        event = mouse.WheelEvent(event_dict['delta'])
    if event:
        return (event_time, (event, pos))
    return None

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Macro Editor v2.2")
        self.root.geometry("650x600")

        self.is_recording = False
        self.is_playing = False
        self.macro_data = {}
        self.visible_actions = []

        self.recorder = Recorder(log_callback=self.add_log_message)
        self.player = Player(on_finish_callback=self.on_playback_finished, log_callback=self.add_log_message, on_action_highlight_callback=self.highlight_playing_action)
        self.hotkey_manager = HotkeyManager(on_record_hotkey=self.toggle_recording, on_play_hotkey=self.start_playing, on_stop_hotkey=self.stop_playing)

        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Macro", command=self.save_events)
        file_menu.add_command(label="Load Macro", command=self.load_events)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)

        main_pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_frame = ttk.Frame(main_pane)
        main_pane.add(top_frame, weight=0)

        controls_frame = ttk.LabelFrame(top_frame, text="Controls")
        controls_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        self.record_button = ttk.Button(controls_frame, text="Record (Ctrl+Alt+F5)", command=self.toggle_recording)
        self.record_button.pack(side="left", padx=5, pady=5)
        self.play_button = ttk.Button(controls_frame, text="Play (Ctrl+Alt+F6)", command=self.start_playing)
        self.play_button.pack(side="left", padx=5, pady=5)
        self.stop_button = ttk.Button(controls_frame, text="Stop (Ctrl+Alt+F7)", command=self.stop_playing)
        self.stop_button.pack(side="left", padx=5, pady=5)

        options_frame = ttk.LabelFrame(top_frame, text="Options")
        options_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(options_frame, text="Repeat:").pack(side="left", padx=(5, 0))
        self.repeat_spinbox = ttk.Spinbox(options_frame, from_=1, to=100, width=5)
        self.repeat_spinbox.pack(side="left", padx=5)
        self.repeat_spinbox.set(1)
        ttk.Label(options_frame, text="Coordinates:").pack(side="left", padx=(10, 0))
        self.coord_var = tk.StringVar(value="absolute")
        ttk.Radiobutton(options_frame, text="Absolute", variable=self.coord_var, value="absolute").pack(side="left")
        ttk.Radiobutton(options_frame, text="Relative", variable=self.coord_var, value="relative").pack(side="left", padx=5)

        self.always_on_top_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top).pack(side="left", padx=(10,0))

        editor_frame = ttk.LabelFrame(main_pane, text="Macro Editor")
        main_pane.add(editor_frame, weight=1)

        self.tree = ttk.Treeview(editor_frame, columns=("Time", "Action", "Details"), show="headings")
        self.tree.heading("Time", text="Time (s)")
        self.tree.heading("Action", text="Action")
        self.tree.heading("Details", text="Details")
        self.tree.column("Time", width=80, anchor="center")
        self.tree.column("Action", width=150)
        self.tree.column("Details", width=270)
        tree_scrollbar = ttk.Scrollbar(editor_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_time_editor)

        editor_button_frame = ttk.Frame(editor_frame)
        editor_button_frame.pack(fill='y', side='right', padx=5)
        self.delete_button = ttk.Button(editor_button_frame, text="Delete Selected", command=self.delete_selected_event)
        self.delete_button.pack(pady=5)

        log_frame = ttk.LabelFrame(main_pane, text="Logs")
        main_pane.add(log_frame, weight=0)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=5)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.update_button_states()
        self.hotkey_manager.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _populate_treeview(self):
        self.visible_actions = event_grouper.group_events(self.macro_data.get('events', []))
        self.tree.delete(*self.tree.get_children())
        for i, action in enumerate(self.visible_actions):
            start_time = self.macro_data['events'][action.start_index][0]
            details = f"{action.end_index - action.start_index + 1} raw events"
            self.tree.insert("", "end", iid=i, values=(f"{start_time:.2f}", action.display_text, details))

    def delete_selected_event(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select an action to delete.")
            return

        selected_indices = sorted([int(item) for item in selected_items], reverse=True)
        raw_indices_to_delete = []
        for i in selected_indices:
            action = self.visible_actions[i]
            raw_indices_to_delete.extend(range(action.start_index, action.end_index + 1))
        
        final_delete_indices = sorted(list(set(raw_indices_to_delete)), reverse=True)
        for i in final_delete_indices:
            del self.macro_data['events'][i]

        self.add_log_message(f"Deleted {len(final_delete_indices)} raw event(s).")
        self._populate_treeview()
        self.update_button_states()

    def on_close(self):
        if self.is_recording:
            self.recorder.stop_recording()
        self.hotkey_manager.stop()
        self.root.destroy()

    def toggle_recording(self):
        if self.is_playing:
            return
        if not self.is_recording:
            self.is_recording = True
            self.record_button.config(text="Stop Record (Ctrl+Alt+F5)")
            self.recorder.start_recording(self.coord_var.get())
        else:
            self.is_recording = False
            self.record_button.config(text="Record (Ctrl+Alt+F5)")
            self.macro_data = self.recorder.stop_recording()
            
            # --- Post-process recorded macro data to filter out hotkey presses ---
            # --- Post-process recorded macro data to filter out hotkey presses ---
            if self.macro_data and self.macro_data.get('events'):
                events = self.macro_data['events']
                
                # Heuristic for filtering start hotkey (Ctrl+Alt+F5)
                # Remove any hotkey-related key events (F-keys and modifiers) 
                # that occur within a very short time window (e.g., 0.5 seconds) at the beginning.
                start_idx_to_keep = 0
                if events:
                    start_filter_time = events[0][0]
                    for idx, (evt_time, (evt_obj, pos)) in enumerate(events):
                        if isinstance(evt_obj, keyboard.KeyboardEvent) and \
                           evt_obj.name in ['f5', 'f6', 'f7', 'ctrl', 'alt', 'shift'] and \
                           (evt_time - start_filter_time) < 0.5: # Within 0.5 seconds of start
                            start_idx_to_keep = idx + 1
                        else:
                            break
                
                # Heuristic for filtering end hotkey (Ctrl+Alt+F7)
                # Remove any hotkey-related key events (F-keys and modifiers) 
                # that occur within a very short time window (e.g., 0.5 seconds) at the end.
                end_idx_to_keep = len(events)
                if events:
                    end_filter_time = events[-1][0]
                    for idx in range(len(events) - 1, -1, -1):
                        evt_time, (evt_obj, pos) = events[idx]
                        if isinstance(evt_obj, keyboard.KeyboardEvent) and \
                           evt_obj.name in ['f5', 'f6', 'f7', 'ctrl', 'alt', 'shift'] and \
                           (end_filter_time - evt_time) < 0.5: # Within 0.5 seconds of end
                            end_idx_to_keep = idx
                        else:
                            break
                
                # Apply filtering
                filtered_events = events[start_idx_to_keep:end_idx_to_keep]
                self.macro_data['events'] = filtered_events

            self.add_log_message(f"Recorded {len(self.macro_data.get('events', []))} events.")
            self._populate_treeview()
        self.update_button_states()

    def start_playing(self):
        if self.is_playing or self.is_recording:
            return
        if not self.macro_data.get('events'):
            self.add_log_message("No macro data to play.")
            return
        try:
            repeat_count = int(self.repeat_spinbox.get())
        except ValueError:
            self.add_log_message("Invalid repeat count.")
            return
        self.is_playing = True
        self.update_button_states()
        self.add_log_message(f"Playback started (repeating {repeat_count} times)...")
        self.player.play_events(self.macro_data, repeat_count)

    def stop_playing(self):
        if not self.is_playing:
            return
        self.player.stop_playing()

    def on_playback_finished(self):
        self.is_playing = False
        self.update_button_states()
        self.add_log_message("Playback finished.")

    def update_button_states(self):
        can_edit = not self.is_recording and not self.is_playing
        record_state = "disabled" if self.is_playing else "normal"
        play_state = "disabled" if self.is_recording or self.is_playing or not self.macro_data.get('events') else "normal"
        stop_state = "disabled" if not self.is_playing else "normal"
        self.record_button.config(state=record_state)
        self.play_button.config(state=play_state)
        self.stop_button.config(state=stop_state)
        self.delete_button.config(state="normal" if can_edit else "disabled")

    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top_var.get())

    def save_events(self):
        if not self.macro_data.get('events'):
            self.add_log_message("No macro data to save.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Macro Files", "*.json"), ("All Files", "*.*")] )
        if not file_path:
            return
        try:
            serializable_events = [_serialize_event(e) for e in self.macro_data['events']]
            serializable_macro_data = {'mode': self.macro_data['mode'], 'origin': self.macro_data['origin'], 'events': [e for e in serializable_events if e is not None]}
            with open(file_path, 'w') as f:
                json.dump(serializable_macro_data, f, indent=4)
            self.add_log_message(f"Macro successfully saved to {file_path}")
        except Exception as e:
            self.add_log_message(f"Error saving file: {e}")

    def load_events(self):
        if self.is_recording or self.is_playing:
            self.add_log_message("Cannot load macro while recording or playing.")
            return
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Macro Files", "*.json"), ("All Files", "*.*")] )
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                loaded_data = json.load(f)
            deserialized_events = [_deserialize_event(e) for e in loaded_data['events']]
            self.macro_data = {'mode': loaded_data['mode'], 'origin': loaded_data['origin'], 'events': [e for e in deserialized_events if e is not None]}
            self.add_log_message(f"Macro successfully loaded from {file_path}")
            self.add_log_message(f"Loaded {len(self.macro_data.get('events', []))} events.")
            self._populate_treeview()
            self.update_button_states()
        except FileNotFoundError:
            self.add_log_message(f"Error: File not found at {file_path}")
        except json.JSONDecodeError:
            self.add_log_message(f"Error: Could not decode JSON. The file may be corrupted.")
        except (KeyError, TypeError) as e:
            self.add_log_message(f"Error: The macro file is invalid or incompatible. Missing key: {e}")
        except Exception as e:
            self.add_log_message(f"An unexpected error occurred: {e}")

    def add_log_message(self, message):
        self.root.after(0, self._update_log_text, message)

    def _update_log_text(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def highlight_playing_action(self, action_index):
        self.root.after(0, self._update_highlight, action_index)

    def _update_highlight(self, action_index):
        # Clear previous selection
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        
        if action_index != -1:
            # Select the current item
            item_id = self.tree.get_children()[action_index] # Get the actual item ID from its position
            self.tree.selection_add(item_id)
            self.tree.see(item_id) # Scroll to the item if it's not visible

    def open_time_editor(self, event):
        if self.is_recording or self.is_playing:
            return

        selected_items = self.tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        action_index = self.tree.index(item_id)
        action = self.visible_actions[action_index]

        # Calculate delay
        if action_index == 0:
            label_text = "Start Delay (s):"
            current_delay = self.macro_data['events'][action.start_index][0]
        else:
            label_text = "Delay from previous (s):"
            prev_action = self.visible_actions[action_index - 1]
            current_delay = self.macro_data['events'][action.start_index][0] - self.macro_data['events'][prev_action.end_index][0]

        # --- Create Toplevel window ---
        editor_window = tk.Toplevel(self.root)
        editor_window.title("Edit Time")
        editor_window.geometry("300x120")
        editor_window.transient(self.root)
        editor_window.grab_set()

        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        popup_w = 300
        popup_h = 120
        x = root_x + (root_w // 2) - (popup_w // 2)
        y = root_y + (root_h // 2) - (popup_h // 2)
        editor_window.geometry(f'{popup_w}x{popup_h}+{x}+{y}')

        ttk.Label(editor_window, text=label_text).pack(pady=(10,0))
        
        delay_var = tk.StringVar(value=f"{current_delay:.4f}")
        entry = ttk.Entry(editor_window, textvariable=delay_var, width=20)
        entry.pack(pady=5)
        entry.focus_set()
        entry.select_range(0, 'end')

        button_frame = ttk.Frame(editor_window)
        button_frame.pack(pady=10)

        def on_ok():
            self.apply_time_edit(action_index, delay_var.get(), current_delay)
            editor_window.destroy()

        ok_button = ttk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side="left", padx=10)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=editor_window.destroy)
        cancel_button.pack(side="left", padx=10)
        
        editor_window.bind('<Return>', lambda e: on_ok())
        editor_window.bind('<Escape>', lambda e: editor_window.destroy())

    def apply_time_edit(self, action_index, new_delay_str, old_delay):
        # 1. Input validation
        try:
            new_delay = float(new_delay_str)
            if new_delay < 0:
                raise ValueError("Delay cannot be negative.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter a valid non-negative number.\nError: {e}")
            return

        # 2. Calculate time delta
        delta = new_delay - old_delay

        if abs(delta) < 0.0001: # No significant change
            return

        # 3. Apply the delta to all subsequent events
        action = self.visible_actions[action_index]
        start_event_index = action.start_index

        for i in range(start_event_index, len(self.macro_data['events'])):
            original_time, event_data = self.macro_data['events'][i]
            self.macro_data['events'][i] = (original_time + delta, event_data)

        # 4. Update UI
        self.add_log_message(f"Action {action_index} delay adjusted by {delta:.2f}s.")
        self._populate_treeview()
