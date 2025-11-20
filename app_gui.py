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
from event_grouper import GroupedAction
import event_utils
from action_editor import ActionEditorWindow
from key_mapper_manager import KeyMapperManager
from key_mapper_gui import KeyMapperWindow

def _get_event_obj(event):
    """Helper to extract the event object from a macro data entry."""
    return event[1]['obj']

def _is_modifier_or_hotkey(key_name):
    if not key_name: return False
    key_name = key_name.lower()
    return key_name in ['f5', 'f6', 'f7', 'ctrl', 'alt', 'shift']

# --- Event Serialization/Deserialization Helpers ---
def _serialize_event(event_data):
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

def _deserialize_event(event_dict):
    event_type = event_dict.get('type')
    event_time = event_dict['time']
    
    data_dict = {}
    event = None

    if event_type == 'keyboard':
        event = keyboard.KeyboardEvent(event_type=event_dict['event_type'], name=event_dict['name'], scan_code=event_dict['scan_code'])
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

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Macro Editor v3.1")
        self.root.geometry("580x550")

        self.is_recording = False
        self.is_playing = False
        self.macro_data = {}
        self.visible_actions = []

        self.key_mapper_manager = KeyMapperManager()
        self.recorder = Recorder(log_callback=self.add_log_message, mapper_manager=self.key_mapper_manager)
        self.player = Player(
            on_finish_callback=self.on_playback_finished, 
            log_callback=self.add_log_message, 
            on_action_highlight_callback=self.highlight_playing_action,
            mapper_manager=self.key_mapper_manager
        )
        self.hotkey_manager = HotkeyManager(on_record_hotkey=self.toggle_recording, on_play_hotkey=self.start_playing, on_stop_hotkey=self.stop_playing)
        self.coord_var = tk.StringVar(value="absolute")

        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Macro", command=self.save_events)
        file_menu.add_command(label="Load Macro", command=self.load_events)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)

        option_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Option", menu=option_menu)
        option_menu.add_radiobutton(label="Absolute Coordinates", variable=self.coord_var, value="absolute")
        option_menu.add_radiobutton(label="Relative Coordinates", variable=self.coord_var, value="relative")

        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Keyboard Mapping...", command=self.open_key_mapper)

        main_pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_frame = ttk.Frame(main_pane)
        main_pane.add(top_frame, weight=0)

        controls_frame = ttk.LabelFrame(top_frame, text="Controls")
        controls_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        self.record_button = ttk.Button(controls_frame, text="Record (Ctrl+Alt+F5)", command=self.toggle_recording)
        self.record_button.pack(side="left", padx=5, pady=5)
        self.continue_button = ttk.Button(controls_frame, text="Continue Record", command=self.start_continue_recording, state="disabled")
        self.continue_button.pack(side="left", padx=5, pady=5)
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

        self.always_on_top_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top).pack(side="left", padx=(10,0))

        # Partial playback controls
        partial_frame = ttk.LabelFrame(top_frame, text="Partial Playback")
        partial_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Label(partial_frame, text="From:").pack(side="left", padx=5)
        self.from_var = tk.StringVar(value="1")
        ttk.Entry(partial_frame, textvariable=self.from_var, width=8).pack(side="left")
        
        ttk.Label(partial_frame, text="To:").pack(side="left", padx=5)
        self.to_var = tk.StringVar(value="")
        ttk.Entry(partial_frame, textvariable=self.to_var, width=8).pack(side="left")
        
        self.partial_play_btn = ttk.Button(partial_frame, text="Play Range", command=self.play_partial)
        self.partial_play_btn.pack(side="left", padx=5)

        editor_frame = ttk.LabelFrame(main_pane, text="Macro Editor")
        main_pane.add(editor_frame, weight=1)

        self.tree = ttk.Treeview(editor_frame, columns=("No", "Time", "Action", "Details"), show="headings")
        self.tree.heading("No", text="No.")
        self.tree.heading("Time", text="Time (s)")
        self.tree.heading("Action", text="Action")
        self.tree.heading("Details", text="Details")
        self.tree.column("No", width=40, anchor="center")
        self.tree.column("Time", width=80, anchor="center")
        self.tree.column("Action", width=120)
        self.tree.column("Details", width=80)
        tree_scrollbar = ttk.Scrollbar(editor_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_action_editor)

        editor_button_frame = ttk.Frame(editor_frame)
        editor_button_frame.pack(fill='y', side='right', padx=5)
        self.delete_button = ttk.Button(editor_button_frame, text="Delete Selected", command=self.delete_selected_event)
        self.delete_button.pack(pady=5)
        self.bulk_delete_moves_button = ttk.Button(editor_button_frame, text="Delete All Moves", command=self.bulk_delete_mouse_moves)
        self.bulk_delete_moves_button.pack(pady=5)

        log_frame = ttk.LabelFrame(main_pane, text="Logs")
        main_pane.add(log_frame, weight=0)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=5)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_file = "macro_log.txt"

        self.update_button_states()
        self.hotkey_manager.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def open_key_mapper(self):
        KeyMapperWindow(self.root, self.key_mapper_manager)

    def _populate_treeview(self):
        self.tree.delete(*self.tree.get_children())
        
        try:
            # Use loaded grouped actions if available (perfect compatibility)
            # Otherwise re-group from raw events
            if self.macro_data.get('grouped_actions'):
                self.visible_actions = self.macro_data['grouped_actions']
                self.add_log_message("Using pre-grouped actions from file.")
            else:
                self.visible_actions = event_grouper.group_events(
                    self.macro_data.get('events', []),
                    log_callback=self.add_log_message
                )
            for i, action in enumerate(self.visible_actions):
                start_time = self.macro_data['events'][action.start_index][0]
                
                # Check for remarks in the first event of the action
                first_event_data = self.macro_data['events'][action.start_index][1]
                details = first_event_data.get('remarks', f"{len(action.indices)} raw events")

                self.tree.insert("", "end", iid=i, values=(i + 1, f"{start_time:.2f}", action.display_text, details))
        except Exception as e:
            self.add_log_message(f"Error populating editor: {e}")
            messagebox.showerror("Error", f"Failed to display macro actions. The data might be inconsistent.\n\nDetails: {e}")

    def bulk_delete_mouse_moves(self):
        if not self.macro_data.get('events'):
            messagebox.showwarning("No Macro", "There is no macro data to modify.")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete ALL mouse move actions?\nThis action cannot be undone."):
            return

        # We need to get a fresh grouping to ensure we have the right actions
        grouped_actions = event_grouper.group_events(
            self.macro_data.get('events', []),
            log_callback=self.add_log_message
        )
        
        indices_to_delete = set()
        for action in grouped_actions:
            if action.type == 'mouse_move':
                indices_to_delete.update(action.indices)
        
        if not indices_to_delete:
            messagebox.showinfo("No Moves", "No mouse move actions were found to delete.")
            return

        # Delete from the raw event list in reverse order to avoid index shifting issues
        for i in sorted(list(indices_to_delete), reverse=True):
            del self.macro_data['events'][i]

        self.add_log_message(f"Bulk deleted {len(indices_to_delete)} raw mouse move event(s).")
        self._populate_treeview()
        self.update_button_states()

    def delete_selected_event(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select an action to delete.")
            return
        
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected action(s)?"):
            return

        selected_indices = sorted([int(self.tree.item(item, "values")[0]) - 1 for item in selected_items], reverse=True)
        
        raw_indices_to_delete = set()
        for i in selected_indices:
            if i < len(self.visible_actions):
                action = self.visible_actions[i]
                raw_indices_to_delete.update(action.indices)
        
        # Delete from the raw event list in reverse order
        for i in sorted(list(raw_indices_to_delete), reverse=True):
            del self.macro_data['events'][i]

        self.add_log_message(f"Deleted {len(raw_indices_to_delete)} raw event(s).")
        self._populate_treeview()
        self.update_button_states()

    def on_close(self):
        if self.is_recording:
            self.recorder.stop_recording()
        self.hotkey_manager.stop()
        self.root.destroy()

    def toggle_recording(self, is_continuation=False):
        if self.is_playing:
            return
        if not self.is_recording:
            # Check if there's existing data and ask for confirmation
            if self.macro_data.get('events') and not is_continuation:
                response = messagebox.askyesnocancel(
                    "기존 녹화 확인",
                    "이미 녹화된 내용이 있습니다.\n\n"
                    "예: 기존 내용 삭제하고 새로 녹화\n"
                    "아니오: 저장 후 새로 녹화\n"
                    "취소: 녹화 취소"
                )
                
                if response is None:  # Cancel
                    return
                elif response is False:  # No - Save first
                    self.save_events()
            
            self.is_recording = True
            self.record_button.config(text="Stop Record (Ctrl+Alt+F5)")
            existing_events = self.macro_data.get('events', []) if is_continuation else None
            self.recorder.start_recording(self.coord_var.get(), existing_events=existing_events)
        else:
            self.is_recording = False
            self.record_button.config(text="Record (Ctrl+Alt+F5)")
            self.macro_data = self.recorder.stop_recording()
            
            if self.macro_data and self.macro_data.get('events'):
                events = self.macro_data['events']
                start_idx_to_keep = 0
                if events and not is_continuation:
                    start_filter_time = events[0][0]
                    for idx, (evt_time, evt_data) in enumerate(events):
                        evt_obj = evt_data['obj']
                        if isinstance(evt_obj, keyboard.KeyboardEvent) and \
                           _is_modifier_or_hotkey(evt_obj.name) and \
                           (evt_time - start_filter_time) < 0.5:
                            start_idx_to_keep = idx + 1
                        else:
                            break
                end_idx_to_keep = len(events)
                if events:
                    end_filter_time = events[-1][0]
                    for idx in range(len(events) - 1, -1, -1):
                        evt_time, evt_data = events[idx]
                        evt_obj = evt_data['obj']
                        if isinstance(evt_obj, keyboard.KeyboardEvent) and \
                           _is_modifier_or_hotkey(evt_obj.name) and \
                           (end_filter_time - evt_time) < 0.5:
                            end_idx_to_keep = idx
                        else:
                            break
                
                self.macro_data['events'] = events[start_idx_to_keep:end_idx_to_keep]

            # Remove redundant paste events (Win+V fix)
            if self.macro_data.get('events'):
                self.macro_data['events'] = event_utils.remove_redundant_paste_events(self.macro_data['events'])

            self.add_log_message(f"Recorded {len(self.macro_data.get('events', []))} events.")
            self._populate_treeview()
        self.update_button_states()

    def start_continue_recording(self):
        self.toggle_recording(is_continuation=True)

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


    def play_partial(self):
        if self.is_playing or self.is_recording:
            return
        if not self.visible_actions:
            self.add_log_message("No macro actions to play.")
            return
        
        try:
            from_idx = int(self.from_var.get()) - 1  # Convert to 0-indexed
            to_str = self.to_var.get().strip()
            to_idx = int(to_str) - 1 if to_str else len(self.visible_actions) - 1
            
            if from_idx < 0 or to_idx >= len(self.visible_actions) or from_idx > to_idx:
                messagebox.showerror("Invalid Range", "Please enter a valid range.")
                return
            
            # Create partial events from selected action range
            partial_events = []
            for i in range(from_idx, to_idx + 1):
                action = self.visible_actions[i]
                for idx in action.indices:
                    partial_events.append(self.macro_data['events'][idx])
            
            # Adjust timestamps to start from 0
            if partial_events:
                first_time = partial_events[0][0]
                partial_events = [(t - first_time, data) for t, data in partial_events]
            
            partial_macro = {
                'mode': self.macro_data['mode'],
                'origin': self.macro_data['origin'],
                'events': partial_events
            }
            
            repeat_count = int(self.repeat_spinbox.get())
            speed_multiplier = float(self.speed_spinbox.get())
            
            self.is_playing = True
            self.update_button_states()
            self.add_log_message(f"Partial playback started (actions {from_idx+1} to {to_idx+1})...")
            self.player.play_events(partial_macro, repeat_count, speed_multiplier)
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers.")

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
        has_macro = self.macro_data.get('events')

        record_state = "disabled" if self.is_playing else "normal"
        continue_state = "disabled" if self.is_recording or self.is_playing or not has_macro else "normal"
        play_state = "disabled" if self.is_recording or self.is_playing or not has_macro else "normal"
        stop_state = "disabled" if not self.is_playing else "normal"

        self.record_button.config(state=record_state)
        self.continue_button.config(state=continue_state)
        self.play_button.config(state=play_state)
        self.stop_button.config(state=stop_state)
        self.delete_button.config(state="normal" if can_edit and has_macro else "disabled")

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
            # Serialize grouped actions for perfect compatibility
            serializable_actions = []
            if self.visible_actions:
                for action in self.visible_actions:
                    action_dict = {
                        'type': action.type,
                        'display_text': action.display_text,
                        'start_time': action.start_time,
                        'end_time': action.end_time,
                        'start_index': action.start_index,
                        'end_index': action.end_index,
                        'indices': action.indices,
                        'details': action.details
                    }
                    serializable_actions.append(action_dict)
            
            serializable_macro_data = {
                'mode': self.macro_data['mode'],
                'origin': self.macro_data['origin'],
                'events': [e for e in serializable_events if e is not None],
                'grouped_actions': serializable_actions  # NEW: Store grouped actions
            }
            with open(file_path, 'w') as f:
                json.dump(serializable_macro_data, f, indent=4)
            self.add_log_message(f"Macro successfully saved to {file_path}")
        except Exception as e:
            self.add_log_message(f"Error saving file: {e}")

    def load_events(self):
        if self.is_recording or self.is_playing:
            self.add_log_message("Cannot load macro while recording or playing.")
            return

        load_mode = 'replace' # Default to replace
        if self.macro_data.get('events'):
            # In Korean: "기존 매크로가 있습니다. 불러온 매크로를 뒤에 추가하시겠습니까?\n\n(Yes=추가, No=새로 쓰기)"
            # Translation: "An existing macro is present. Would you like to append the new macro?\n\n(Yes=Append, No=Overwrite)"
            user_choice = messagebox.askyesnocancel(
                "Confirm Load", 
                "기존 매크로가 있습니다. 불러온 매크로를 뒤에 추가하시겠습니까?\n\n(Yes=추가, No=새로 쓰기)"
            )
            if user_choice is None: # Cancel
                self.add_log_message("Load operation cancelled.")
                return
            elif user_choice is True: # Yes -> Append
                load_mode = 'append'
            else: # No -> Replace
                load_mode = 'replace'

        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON Macro Files", "*.json"), ("All Files", "*.* אמיתי")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                loaded_data = json.load(f)
            
            new_events = [_deserialize_event(e) for e in loaded_data.get('events', [])]
            new_events = [e for e in new_events if e is not None]

            if not new_events:
                self.add_log_message("Loaded macro file contains no valid events.")
                return

            if load_mode == 'append':
                old_events = self.macro_data.get('events', [])
                if old_events:
                    last_timestamp = old_events[-1][0] if old_events else 0
                    # Add a 1-second delay between the end of the old macro and the start of the new one.
                    time_offset = last_timestamp + 1.0 
                    first_new_timestamp = new_events[0][0]
                    adjustment = time_offset - first_new_timestamp
                    
                    adjusted_new_events = [(t + adjustment, e) for t, e in new_events]
                    self.macro_data['events'].extend(adjusted_new_events)
                    self.add_log_message(f"Appended {len(adjusted_new_events)} events from {file_path}")
                else:
                    # If old_events is empty, 'append' is the same as 'replace'
                    self.macro_data = {
                        'mode': loaded_data.get('mode', 'absolute'),
                        'origin': loaded_data.get('origin', (0,0)),
                        'events': new_events
                    }
                    # Load grouped actions if available (for perfect compatibility)
                    loaded_groups = loaded_data.get('grouped_actions')
                    if loaded_groups:
                        self.macro_data['grouped_actions'] = []
                        for action_dict in loaded_groups:
                            action = GroupedAction(
                                type=action_dict['type'],
                                display_text=action_dict['display_text'],
                                start_time=action_dict['start_time'],
                                end_time=action_dict['end_time'],
                                start_index=action_dict['start_index'],
                                end_index=action_dict['end_index'],
                                indices=action_dict['indices'],
                                details=action_dict.get('details', {})
                            )
                            self.macro_data['grouped_actions'].append(action)
                    self.add_log_message(f"Macro successfully loaded from {file_path}")

            else: # 'replace'
                self.macro_data = {
                    'mode': loaded_data.get('mode', 'absolute'),
                    'origin': loaded_data.get('origin', (0,0)),
                    'events': new_events
                }
                self.add_log_message(f"Macro successfully loaded from {file_path}")

            self.add_log_message(f"Total events: {len(self.macro_data.get('events', []))}.")
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

        ActionEditorWindow(
            parent=self.root,
            action=action,
            action_index=action_index,
            visible_actions=self.visible_actions,
            macro_data=self.macro_data,
            on_complete_callback=self._populate_treeview
        )