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

def _get_event_obj(event):
    """Helper to extract the event object from a macro data entry."""
    return event[1][0]

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
        self.root.title("Advanced Macro Editor v2.3")
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

        ttk.Label(options_frame, text="Speed:").pack(side="left", padx=(10, 0))
        self.speed_spinbox = ttk.Spinbox(options_frame, from_=0.1, to=5.0, increment=0.1, width=5)
        self.speed_spinbox.pack(side="left", padx=5)
        self.speed_spinbox.set(1.0)

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
        self.tree.bind("<Double-1>", self.open_action_editor)

        editor_button_frame = ttk.Frame(editor_frame)
        editor_button_frame.pack(fill='y', side='right', padx=5)
        self.delete_button = ttk.Button(editor_button_frame, text="Delete Selected", command=self.delete_selected_event)
        self.delete_button.pack(pady=5)

        log_frame = ttk.LabelFrame(main_pane, text="Logs")
        main_pane.add(log_frame, weight=0)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=5)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_file = "macro_log.txt"

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
            
            if self.macro_data and self.macro_data.get('events'):
                events = self.macro_data['events']
                start_idx_to_keep = 0
                if events:
                    start_filter_time = events[0][0]
                    for idx, (evt_time, (evt_obj, pos)) in enumerate(events):
                        if isinstance(evt_obj, keyboard.KeyboardEvent) and \
                           evt_obj.name in ['f5', 'f6', 'f7', 'ctrl', 'alt', 'shift'] and \
                           (evt_time - start_filter_time) < 0.5:
                            start_idx_to_keep = idx + 1
                        else:
                            break
                end_idx_to_keep = len(events)
                if events:
                    end_filter_time = events[-1][0]
                    for idx in range(len(events) - 1, -1, -1):
                        evt_time, (evt_obj, pos) = events[idx]
                        if isinstance(evt_obj, keyboard.KeyboardEvent) and \
                           evt_obj.name in ['f5', 'f6', 'f7', 'ctrl', 'alt', 'shift'] and \
                           (end_filter_time - evt_time) < 0.5:
                            end_idx_to_keep = idx
                        else:
                            break
                
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
            speed_multiplier = float(self.speed_spinbox.get())
        except ValueError:
            self.add_log_message("Invalid repeat count or speed.")
            return
        self.is_playing = True
        self.update_button_states()
        self.add_log_message(f"Playback started (repeating {repeat_count} times at {speed_multiplier}x speed)...")
        self.player.play_events(self.macro_data, repeat_count, speed_multiplier)

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
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{timestamp} {message}"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + "\n")
        except Exception as e:
            error_message = f"{timestamp} [ERROR] Could not write to log file: {e}"
            self.root.after(0, self._update_log_text, error_message)

        self.root.after(0, self._update_log_text, log_message)

    def _update_log_text(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def highlight_playing_action(self, action_index):
        self.root.after(0, self._update_highlight, action_index)

    def _update_highlight(self, action_index):
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        
        if action_index != -1:
            try:
                item_id = self.tree.get_children()[action_index]
                self.tree.selection_add(item_id)
                self.tree.see(item_id)
            except IndexError:
                pass

    def open_action_editor(self, event):
        if self.is_recording or self.is_playing:
            return

        selected_items = self.tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        action_index = self.tree.index(item_id)
        action = self.visible_actions[action_index]

        editor_window = tk.Toplevel(self.root)
        editor_window.title("Edit Action")
        editor_window.transient(self.root)
        editor_window.grab_set()

        time_frame = ttk.LabelFrame(editor_window, text="Time Edit")
        time_frame.pack(padx=10, pady=10, fill="x")

        if action_index == 0:
            label_text = "Start Delay (s):"
            current_delay = self.macro_data['events'][action.start_index][0]
        else:
            label_text = "Delay from previous (s):"
            prev_action = self.visible_actions[action_index - 1]
            current_delay = self.macro_data['events'][action.start_index][0] - self.macro_data['events'][prev_action.end_index][0]

        ttk.Label(time_frame, text=label_text).pack(side="left", padx=5, pady=5)
        delay_var = tk.StringVar(value=f"{current_delay:.4f}")
        time_entry = ttk.Entry(time_frame, textvariable=delay_var, width=15)
        time_entry.pack(side="left", padx=5, pady=5)

        action_frame = ttk.LabelFrame(editor_window, text="Action Specific Edit")
        action_frame.pack(padx=10, pady=5, fill="both", expand=True)

        edit_params = {}
        is_editable = False

        if action.type in ['mouse_click', 'mouse_drag', 'raw_mouse']:
            first_event_obj = None
            for i in range(action.start_index, action.end_index + 1):
                evt = _get_event_obj(self.macro_data['events'][i])
                if isinstance(evt, mouse.ButtonEvent):
                    first_event_obj = evt
                    break
            
            if first_event_obj:
                is_editable = True
                click_type_var = tk.StringVar()
                edit_params['click_type'] = click_type_var
                ttk.Label(action_frame, text="Click Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
                ttk.Radiobutton(action_frame, text="Single", variable=click_type_var, value="single").grid(row=0, column=1, sticky="w")
                ttk.Radiobutton(action_frame, text="Double", variable=click_type_var, value="double").grid(row=0, column=2, sticky="w")
                is_double = any(isinstance(_get_event_obj(e), mouse.ButtonEvent) and _get_event_obj(e).event_type == 'double' for e in self.macro_data['events'][action.start_index:action.end_index+1])
                click_type_var.set("double" if is_double else "single")

                button_type_var = tk.StringVar()
                edit_params['button_type'] = button_type_var
                ttk.Label(action_frame, text="Button:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
                ttk.Radiobutton(action_frame, text="Left", variable=button_type_var, value="left").grid(row=1, column=1, sticky="w")
                ttk.Radiobutton(action_frame, text="Right", variable=button_type_var, value="right").grid(row=1, column=2, sticky="w")
                ttk.Radiobutton(action_frame, text="Middle", variable=button_type_var, value="middle").grid(row=1, column=3, sticky="w")
                button_type_var.set(first_event_obj.button)

        elif action.type in ['key_press', 'raw_key']:
            is_editable = True
            first_event_obj = _get_event_obj(self.macro_data['events'][action.start_index])
            original_key = first_event_obj.name

            ttk.Label(action_frame, text="Key:").pack(side="left", padx=5, pady=5)
            key_var = tk.StringVar(value=original_key)
            edit_params['new_key'] = key_var
            key_entry = ttk.Entry(action_frame, textvariable=key_var, width=15)
            key_entry.pack(side="left", padx=5, pady=5)
            key_entry.focus_set()
            key_entry.select_range(0, 'end')

        if not is_editable:
            ttk.Label(action_frame, text="(No action-specific edits available for this type)").pack(pady=10)

        button_frame = ttk.Frame(editor_window)
        button_frame.pack(pady=10)

        def on_ok():
            self.apply_action_edit(action_index, delay_var.get(), current_delay, edit_params)
            editor_window.destroy()

        ok_button = ttk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side="left", padx=10)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=editor_window.destroy)
        cancel_button.pack(side="left", padx=10)
        editor_window.bind('<Return>', lambda e: on_ok())
        editor_window.bind('<Escape>', lambda e: editor_window.destroy())
        time_entry.focus_set()
        time_entry.select_range(0, 'end')

    def apply_action_edit(self, action_index, new_delay_str, old_delay, edit_params):
        action = self.visible_actions[action_index]
        
        try:
            new_delay = float(new_delay_str)
            if new_delay < 0: raise ValueError("Delay cannot be negative.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter a valid non-negative number for delay.\nError: {e}")
            return

        time_delta = new_delay - old_delay
        if abs(time_delta) > 0.0001:
            for i in range(action.start_index, len(self.macro_data['events'])):
                original_time, event_data = self.macro_data['events'][i]
                self.macro_data['events'][i] = (original_time + time_delta, event_data)
            self.add_log_message(f"Action {action_index} delay adjusted by {time_delta:.2f}s.")

        if action.type in ['mouse_click', 'mouse_drag', 'raw_mouse']:
            if edit_params:
                new_click_type = edit_params['click_type'].get()
                new_button_type = edit_params['button_type'].get()
                
                original_event_index = -1
                original_event_obj = None
                for i in range(action.start_index, action.end_index + 1):
                    evt = _get_event_obj(self.macro_data['events'][i])
                    if isinstance(evt, mouse.ButtonEvent):
                        original_event_index = i
                        original_event_obj = evt
                        break
                
                if original_event_obj is None: self._populate_treeview(); return

                original_click_type = "double" if original_event_obj.event_type == 'double' else "single"

                if original_event_obj.button != new_button_type:
                    for i in range(action.start_index, action.end_index + 1):
                        evt_time, (evt, pos) = self.macro_data['events'][i]
                        if isinstance(evt, mouse.ButtonEvent):
                            new_evt = mouse.ButtonEvent(evt.event_type, new_button_type, evt.time)
                            self.macro_data['events'][i] = (evt_time, (new_evt, pos))
                    self.add_log_message(f"Action {action_index}: Button changed to {new_button_type}")

                if original_click_type != new_click_type:
                    if new_click_type == 'double':
                        up_event_index = -1
                        for i in range(action.start_index, action.end_index + 1):
                            if _get_event_obj(self.macro_data['events'][i]).event_type == mouse.UP:
                                up_event_index = i
                                break
                        if up_event_index != -1: del self.macro_data['events'][up_event_index]
                        
                        evt_time, (evt, pos) = self.macro_data['events'][original_event_index]
                        new_evt = mouse.ButtonEvent(mouse.DOUBLE, new_button_type, evt.time)
                        self.macro_data['events'][original_event_index] = (evt_time, (new_evt, pos))
                        self.add_log_message(f"Action {action_index}: Changed to Double Click.")
                    else:
                        evt_time, (evt, pos) = self.macro_data['events'][original_event_index]
                        new_evt = mouse.ButtonEvent(mouse.DOWN, new_button_type, evt.time)
                        self.macro_data['events'][original_event_index] = (evt_time, (new_evt, pos))

                        down_time, (down_event, pos) = self.macro_data['events'][original_event_index]
                        up_event_time = down_time + 0.05
                        up_event = (up_event_time, (mouse.ButtonEvent(mouse.UP, new_button_type, time.time()), pos))
                        self.macro_data['events'].insert(original_event_index + 1, up_event)

                        for i in range(original_event_index + 2, len(self.macro_data['events'])):
                            original_time, event_data = self.macro_data['events'][i]
                            self.macro_data['events'][i] = (original_time + 0.05, event_data)
                        self.add_log_message(f"Action {action_index}: Changed to Single Click.")
        
        elif action.type in ['key_press', 'raw_key']:
            if edit_params:
                new_key = edit_params['new_key'].get()
                if not new_key:
                    messagebox.showwarning("Invalid Key", "Key cannot be empty.")
                    return
                
                self.add_log_message(f"--- Start Key Edit Debug ---")
                self.add_log_message(f"Editing action index: {action_index}, from raw index {action.start_index} to {action.end_index}")
                self.add_log_message(f"Attempting to change key to: '{new_key}'")

                try:
                    new_key_code = keyboard.key_to_scan_codes(new_key)[0]
                except IndexError:
                    messagebox.showerror("Invalid Key", f"Could not find a scan code for key: '{new_key}'")
                    self.add_log_message(f"--- End Key Edit Debug ---")
                    return

                new_key_name = new_key[0].lower()
                for i in range(action.start_index, action.end_index + 1):
                    evt_time, (evt, pos) = self.macro_data['events'][i]
                    if isinstance(evt, keyboard.KeyboardEvent):
                        self.add_log_message(f"Modifying raw index {i}: event_name={evt.name}, event_type={evt.event_type}")
                        new_evt = keyboard.KeyboardEvent(evt.event_type, scan_code=new_key_code, name=new_key_name)
                        self.macro_data['events'][i] = (evt_time, (new_evt, pos))
                self.add_log_message(f"Action {action_index}: Key changed to '{new_key_name}'")
                self.add_log_message(f"--- End Key Edit Debug ---")

        self._populate_treeview()
