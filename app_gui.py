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
from import_dialog import ImportDialog
from help_gui import HelpWindow

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
    
    # Handle Logic Events (Loop, Wait, etc.)
    if 'logic_type' in data_dict:
        event_dict = {'time': event_time}
        event_dict.update(data_dict)
        return event_dict

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
    event_time = event_dict['time']
    data_dict = {}
    
    # Handle Logic Events
    if 'logic_type' in event_dict:
        data_dict = event_dict.copy()
        del data_dict['time']
        return (event_time, data_dict)

    event_type = event_dict.get('type')
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
        self.root.title("Advanced Macro Editor v6.2.1")
        self.root.geometry("700x750")

        self.is_recording = False
        self.is_playing = False
        self.macro_data = {}
        self.visible_actions = []

        self.quick_slots = {}
        self.load_quick_slots_config()
        self.register_quick_slot_hotkeys()
        self.key_mapper_manager = KeyMapperManager()
        self.playback_idx_offset = 0
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
        self.root.bind('<Control-o>', lambda e: self.load_events(mode='replace'))
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Macro", command=self.save_events)
        file_menu.add_command(label="Open (Replace)", command=lambda: self.load_events(mode='replace'), accelerator="Ctrl+O")
        import_menu = Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Import", menu=import_menu)
        import_menu.add_command(label="Append to End", command=lambda: self.load_events(mode='append'))
        import_menu.add_command(label="Prepend to Start", command=lambda: self.load_events(mode='prepend'))
        import_menu.add_command(label="Insert at Selection", command=self.import_at_selection)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)

        option_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Option", menu=option_menu)
        option_menu.add_radiobutton(label="Absolute Coordinates", variable=self.coord_var, value="absolute")
        option_menu.add_radiobutton(label="Relative Coordinates", variable=self.coord_var, value="relative")
        option_menu.add_separator()
        self.dark_mode_var = tk.BooleanVar(value=False)
        option_menu.add_checkbutton(label="Dark Mode / 다크 모드", variable=self.dark_mode_var, command=self.toggle_dark_mode)

        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Usage Guide", command=self.open_help)
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
        self.stop_on_sound_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Stop on Sound", variable=self.stop_on_sound_var).pack(side="left", padx=(10,0))
        
        self.prudent_mode_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Prudent Mode", variable=self.prudent_mode_var).pack(side="left", padx=(10,0))



        # Bottom Controls (Partial + Import)
        bottom_controls_frame = ttk.Frame(top_frame)
        bottom_controls_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        # Partial Playback (Left)
        partial_frame = ttk.LabelFrame(bottom_controls_frame, text="Partial Playback")
        partial_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ttk.Label(partial_frame, text="From:").pack(side="left", padx=2)
        self.from_var = tk.StringVar(value="1")
        ttk.Entry(partial_frame, textvariable=self.from_var, width=4).pack(side="left")
        
        ttk.Label(partial_frame, text="To:").pack(side="left", padx=2)
        self.to_var = tk.StringVar(value="")
        ttk.Entry(partial_frame, textvariable=self.to_var, width=4).pack(side="left")
        
        self.partial_play_btn = ttk.Button(partial_frame, text="Play", command=self.play_partial, width=6)
        self.partial_play_btn.pack(side="left", padx=5)

        # Import Macros (Middle)
        import_frame = ttk.LabelFrame(bottom_controls_frame, text="Import Macros")
        import_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ttk.Button(import_frame, text="Append", command=lambda: self.load_events(mode='append'), width=8).pack(side="left", padx=2, pady=5)
        ttk.Button(import_frame, text="Prepend", command=lambda: self.load_events(mode='prepend'), width=8).pack(side="left", padx=2, pady=5)
        ttk.Button(import_frame, text="Insert", command=self.import_at_selection, width=8).pack(side="left", padx=2, pady=5)

        # Auto Wait Color (Right)
        auto_wait_frame = ttk.LabelFrame(bottom_controls_frame, text="Auto Wait Color")
        auto_wait_frame.pack(side="left", fill="both", expand=True)

        self.auto_wait_var = tk.BooleanVar()
        self.auto_wait_chk = ttk.Checkbutton(auto_wait_frame, text="Enable", variable=self.auto_wait_var, command=self.toggle_auto_wait_timeout)
        self.auto_wait_chk.pack(side="left", padx=5, pady=5)
        
        ttk.Label(auto_wait_frame, text="Timeout:").pack(side="left", padx=2)
        self.auto_wait_timeout_var = tk.StringVar(value="5.0")
        self.auto_wait_timeout_entry = ttk.Entry(auto_wait_frame, textvariable=self.auto_wait_timeout_var, width=4, state="disabled")
        self.auto_wait_timeout_entry.pack(side="left", padx=2)

        self.notebook = ttk.Notebook(main_pane)
        main_pane.add(self.notebook, weight=1)
        
        editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(editor_frame, text="Editor")
        
        self.quick_slots_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.quick_slots_frame, text="Quick Slots")
        self._setup_quick_slots_tab()

        self.tree = ttk.Treeview(editor_frame, columns=("No", "Time", "Action", "Remarks"), show="headings")
        self.tree.heading("No", text="No.")
        self.tree.heading("Time", text="Time (s)")
        self.tree.heading("Action", text="Action")
        self.tree.heading("Remarks", text="Remarks")
        self.tree.column("No", width=30, anchor="center")
        self.tree.column("Time", width=60, anchor="center")
        self.tree.column("Action", width=120)
        self.tree.column("Remarks", width=150)
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
        self.bulk_edit_btn = ttk.Button(editor_button_frame, text="Bulk Edit Interval", command=self.bulk_edit_interval)
        self.bulk_edit_btn.pack(pady=5)
        self.insert_loop_btn = ttk.Button(editor_button_frame, text="Insert Loop", command=self.insert_loop)
        self.insert_loop_btn.pack(pady=5)
        self.insert_color_btn = ttk.Button(editor_button_frame, text="Insert Color Wait", command=self.insert_color_wait)
        self.insert_color_btn.pack(pady=5)
        self.insert_sound_btn = ttk.Button(editor_button_frame, text="Insert Sound Wait", command=self.insert_sound_wait)
        self.insert_sound_btn.pack(pady=5)
        
        # IF Color with submenu
        self.if_color_menubutton = ttk.Menubutton(editor_button_frame, text="Insert IF Color ▼")
        self.if_color_menu = Menu(self.if_color_menubutton, tearoff=0)
        self.if_color_menubutton["menu"] = self.if_color_menu
        self.if_color_menu.add_command(label="IF Block (전체)", command=self.insert_if_color_block)
        self.if_color_menu.add_separator()
        self.if_color_menu.add_command(label="IF Color Only", command=self.insert_if_color_only)
        self.if_color_menu.add_command(label="ELSE Only", command=self.insert_else_only)
        self.if_color_menu.add_command(label="END IF Only", command=self.insert_end_if_only)
        self.if_color_menubutton.pack(pady=5, fill='x')
        
        self.insert_call_btn = ttk.Button(editor_button_frame, text="Insert Call Macro", command=self.insert_call_macro)
        self.insert_call_btn.pack(pady=5)

        log_frame = ttk.LabelFrame(main_pane, text="Logs")
        main_pane.add(log_frame, weight=0)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=5)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_file = "macro_log.txt"

        # Status Bar
        self.status_var = tk.StringVar(value="Ready / 준비")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                    relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.update_button_states()
        self.hotkey_manager.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def open_key_mapper(self):
        KeyMapperWindow(self.root, self.key_mapper_manager)

    def toggle_auto_wait_timeout(self):
        if self.auto_wait_var.get():
            self.auto_wait_timeout_entry.config(state="normal")
        else:
            self.auto_wait_timeout_entry.config(state="disabled")

    def _invalidate_grouped_actions(self):
        if 'grouped_actions' in self.macro_data:
            del self.macro_data['grouped_actions']

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
                details = first_event_data.get('remarks', "")

                self.tree.insert("", "end", iid=i, values=(i + 1, f"{start_time:.2f}", action.display_text, details))
        except Exception as e:
            self.add_log_message(f"Error populating editor: {e}")
            messagebox.showerror("Error", f"Failed to display macro actions. The data might be inconsistent.\n\nDetails: {e}")


    def bulk_edit_interval(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select actions to edit.")
            return
        
        indices = sorted([self.tree.index(item) for item in selected_items])
        start_idx = indices[0]
        end_idx = indices[-1]
        
        import tkinter.simpledialog as simpledialog
        new_interval_str = simpledialog.askstring("Bulk Edit Interval", 
            f"Enter new delay (seconds) for actions {start_idx+1} to {end_idx+1}:")
        
        if new_interval_str is None: return
        
        try:
            new_interval = float(new_interval_str)
            if new_interval < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid non-negative number.")
            return
            
        self._invalidate_grouped_actions()
        self._apply_bulk_interval(start_idx, end_idx, new_interval)
        self._populate_treeview()
        self.add_log_message(f"Bulk edited interval for actions {start_idx+1}-{end_idx+1} to {new_interval}s")

    def _apply_bulk_interval(self, start_idx, end_idx, new_interval):
        self._invalidate_grouped_actions()
        events = self.macro_data['events']
        if not self.visible_actions: return
    
        # Reconstruct timeline based on Start-to-Start intervals
        new_start_times = []
        
        for i, action in enumerate(self.visible_actions):
            original_start = action.start_time
            
            if i < start_idx:
                new_start = original_start
            elif i <= end_idx:
                # In range: Start = PrevStart + Interval
                if i == 0:
                    new_start = new_interval
                else:
                    new_start = new_start_times[i-1] + new_interval
            else:
                # After range: Maintain original interval from previous
                prev_original_start = self.visible_actions[i-1].start_time
                original_interval = original_start - prev_original_start
                new_start = new_start_times[i-1] + original_interval
            
            new_start_times.append(new_start)
                
        rebuilt_events = []
        for i, action in enumerate(self.visible_actions):
            new_start = new_start_times[i]
            original_start = action.start_time
            shift = new_start - original_start
            
            action.start_time = new_start
            action.end_time += shift

            if action.indices:
                for idx in action.indices:
                    t, data = events[idx]
                    import copy
                    new_data = copy.deepcopy(data)
                    new_t = t + shift
                    
                    if 'time' in new_data:
                        new_data['time'] = new_t
                    
                    if 'obj' in new_data:
                        try:
                            new_data['obj'].time = new_t
                        except:
                            pass
                        
                    rebuilt_events.append((new_t, new_data))
                
        self.macro_data['events'] = rebuilt_events

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
        self._invalidate_grouped_actions()
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
        self._invalidate_grouped_actions()
        self._populate_treeview()
        self.update_button_states()

    def open_help(self):
        HelpWindow(self.root)

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
            
            auto_wait = self.auto_wait_var.get()
            try:
                auto_wait_timeout = float(self.auto_wait_timeout_var.get())
            except ValueError:
                auto_wait_timeout = 5.0

            self.recorder.start_recording(self.coord_var.get(), existing_events=existing_events, auto_wait=auto_wait, auto_wait_timeout=auto_wait_timeout)
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
                        if 'obj' not in evt_data: continue
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
                        if 'obj' not in evt_data: continue
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
        if not messagebox.askyesno("Continue Recording", "Do you want to continue recording from the end of the current macro?"):
            return
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
        self.playback_idx_offset = 0
        self.update_button_states()
        self.add_log_message(f"Playback started (repeating {repeat_count} times at {speed_multiplier}x speed)...")
        self.player.play_events(self.macro_data, repeat_count, speed_multiplier, stop_on_sound=self.stop_on_sound_var.get(), prudent_mode=self.prudent_mode_var.get())


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
            self.playback_idx_offset = from_idx
            self.update_button_states()
            self.add_log_message(f"Partial playback started (actions {from_idx+1} to {to_idx+1})...")
            self.player.play_events(partial_macro, repeat_count, speed_multiplier, stop_on_sound=self.stop_on_sound_var.get(), prudent_mode=self.prudent_mode_var.get())
            
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
        
        # Update Status Bar
        if self.is_recording:
            self.status_var.set("🔴 Recording... / 녹화 중...")
        elif self.is_playing:
            self.status_var.set("▶️ Playing... / 재생 중...")
        else:
            event_count = len(self.macro_data.get('events', []))
            if event_count > 0:
                self.status_var.set(f"Ready ({event_count} events) / 준비 ({event_count}개 이벤트)")
            else:
                self.status_var.set("Ready / 준비")


    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top_var.get())

    def toggle_dark_mode(self):
        """Toggle between light and dark mode"""
        style = ttk.Style()
        if self.dark_mode_var.get():
            # Dark Mode
            style.theme_use('clam')
            bg_color = '#2d2d2d'
            fg_color = '#ffffff'
            self.root.configure(bg=bg_color)
            style.configure(".", background=bg_color, foreground=fg_color, fieldbackground='#3d3d3d')
            style.configure("TFrame", background=bg_color)
            style.configure("TLabel", background=bg_color, foreground=fg_color)
            style.configure("TLabelframe", background=bg_color, foreground=fg_color)
            style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
            style.configure("TButton", background='#4a4a4a', foreground=fg_color)
            style.configure("Treeview", background='#3d3d3d', foreground=fg_color, fieldbackground='#3d3d3d')
            style.configure("Treeview.Heading", background='#4a4a4a', foreground=fg_color)
            self.log_text.configure(bg='#3d3d3d', fg=fg_color, insertbackground=fg_color)
        else:
            # Light Mode (default)
            style.theme_use('default')
            self.root.configure(bg='SystemButtonFace')
            style.configure(".", background='SystemButtonFace', foreground='black')
            self.log_text.configure(bg='white', fg='black', insertbackground='black')

    def _get_clean_data(self):
        """
        Regenerates the events list based on visible actions only.
        Returns (clean_events, clean_actions)
        """
        if not self.visible_actions:
            return [], []

        clean_events = []
        clean_actions = []
        
        current_idx = 0
        import copy
        
        for action in self.visible_actions:
            # Create a copy of the action to avoid modifying the current view in-place immediately
            new_action = copy.deepcopy(action)
            
            new_indices = []
            
            # Extract events for this action
            for old_idx in action.indices:
                if 0 <= old_idx < len(self.macro_data['events']):
                    event = self.macro_data['events'][old_idx]
                    clean_events.append(event)
                    new_indices.append(current_idx)
                    current_idx += 1
            
            if new_indices:
                new_action.indices = new_indices
                new_action.start_index = new_indices[0]
                new_action.end_index = new_indices[-1]
                clean_actions.append(new_action)
        
        # Normalization: Shift all events so the first event starts at 0.0
        if clean_events:
            start_offset = clean_events[0][0]
            if start_offset > 0:
                normalized_events = []
                for t, data in clean_events:
                    new_t = t - start_offset
                    # Update logic event time if present
                    if 'time' in data:
                        data['time'] = new_t # This might be redundant if data is just a dict, but safe
                    
                    # Update object time if possible (for completeness, though serialization uses tuple time)
                    if 'obj' in data:
                        try:
                            data['obj'].time = new_t
                        except:
                            pass
                            
                    normalized_events.append((new_t, data))
                clean_events = normalized_events
                
                # We also need to update the start/end times in clean_actions
                for action in clean_actions:
                    action.start_time -= start_offset
                    action.end_time -= start_offset

        return clean_events, clean_actions

    def save_events(self):
        if not self.macro_data.get('events'):
            self.add_log_message("No macro data to save.")
            return
            
        # Clean data (Garbage Collection)
        clean_events, clean_actions = self._get_clean_data()
        self.macro_data['events'] = clean_events
        self.macro_data['grouped_actions'] = clean_actions
        self.visible_actions = clean_actions
        self._populate_treeview()
        
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

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def import_at_selection(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select an action to insert after.")
            return
        idx = self.tree.index(selected[0])
        self.load_events(mode='insert', target_index=idx + 1)

    def load_events(self, mode='replace', target_index=None):
        if self.is_recording or self.is_playing:
            self.add_log_message("Cannot load macro while recording or playing.")
            return

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

            # Load grouped actions for the new macro
            new_groups = []
            loaded_groups_data = loaded_data.get('grouped_actions')
            if loaded_groups_data:
                for action_dict in loaded_groups_data:
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
                    new_groups.append(action)
            else:
                # If no groups in file, group them now
                new_groups = event_grouper.group_events(new_events)

            # Determine Import Mode
            current_events = self.macro_data.get('events', [])
            if not current_events:
                mode = 'replace'
            
            action_insert_idx = 0
            if mode == 'insert':
                if target_index is not None:
                    action_insert_idx = target_index
                else:
                    # Fallback if called without index (shouldn't happen with new UI)
                    action_insert_idx = len(self.visible_actions)

            # Execute Import Logic
            if mode == 'replace':
                # Normalize timestamps for backward compatibility
                if new_events:
                    start_offset = new_events[0][0]
                    if start_offset > 0:
                        # Shift events
                        normalized_events = []
                        for t, data in new_events:
                            new_t = t - start_offset
                            if 'obj' in data and hasattr(data['obj'], 'time'):
                                try: data['obj'].time = new_t
                                except: pass
                            normalized_events.append((new_t, data))
                        new_events = normalized_events
                        
                        # Shift groups
                        for g in new_groups:
                            g.start_time -= start_offset
                            g.end_time -= start_offset

                self.macro_data = {
                    'mode': loaded_data.get('mode', 'absolute'),
                    'origin': loaded_data.get('origin', (0,0)),
                    'events': new_events,
                    'grouped_actions': new_groups
                }
                self.add_log_message(f"Replaced macro with {file_path}")

            else:
                # Prepare segments
                current_groups = self.macro_data.get('grouped_actions', [])
                if not current_groups and current_events:
                     current_groups = event_grouper.group_events(current_events)

                # Calculate split point (event index)
                if mode == 'prepend':
                    split_event_idx = 0
                    split_group_idx = 0
                elif mode == 'append':
                    split_event_idx = len(current_events)
                    split_group_idx = len(current_groups)
                else: # insert
                    if action_insert_idx >= len(current_groups):
                        split_event_idx = len(current_events)
                        split_group_idx = len(current_groups)
                    elif action_insert_idx == 0:
                        split_event_idx = 0
                        split_group_idx = 0
                    else:
                        prev_action = current_groups[action_insert_idx - 1]
                        split_event_idx = prev_action.end_index + 1
                        split_group_idx = action_insert_idx

                events_before = current_events[:split_event_idx]
                events_after = current_events[split_event_idx:]
                groups_before = current_groups[:split_group_idx]
                groups_after = current_groups[split_group_idx:]

                # 1. Adjust New Events (Shift timestamps)
                # Start time for new events should be: (end of before) + 1.0
                start_time_new = 0.0
                if events_before:
                    start_time_new = events_before[-1][0] + 1.0

                # Shift new events to start at 0 first (normalize), then add start_time_new
                if new_events:
                    first_new_t = new_events[0][0]
                    shifted_new_events = []
                    for t, e in new_events:
                        new_t = (t - first_new_t) + start_time_new
                        # Update event object time if possible
                        if 'obj' in e and hasattr(e['obj'], 'time'):
                            try: e['obj'].time = new_t
                            except: pass
                        shifted_new_events.append((new_t, e))
                    new_events = shifted_new_events

                # 2. Adjust After Events (Shift timestamps)
                # Start time for after events should be: (end of new) + 1.0
                start_time_after = start_time_new
                if new_events:
                    start_time_after = new_events[-1][0] + 1.0

                if events_after:
                    first_after_t = events_after[0][0]
                    shifted_after_events = []
                    for t, e in events_after:
                        new_t = (t - first_after_t) + start_time_after
                        if 'obj' in e and hasattr(e['obj'], 'time'):
                            try: e['obj'].time = new_t
                            except: pass
                        shifted_after_events.append((new_t, e))
                    events_after = shifted_after_events

                # 3. Merge Events
                merged_events = events_before + new_events + events_after

                # 4. Update Group Indices
                # New groups need to be shifted by len(events_before)
                offset_new = len(events_before)
                for g in new_groups:
                    g.start_index += offset_new
                    g.end_index += offset_new
                    g.indices = [i + offset_new for i in g.indices]

                # After groups need to be shifted by len(new_events)
                offset_after = len(new_events)
                for g in groups_after:
                    g.start_index += offset_after
                    g.end_index += offset_after
                    g.indices = [i + offset_after for i in g.indices]

                merged_groups = groups_before + new_groups + groups_after

                self.macro_data['events'] = merged_events
                self.macro_data['grouped_actions'] = merged_groups
                self.add_log_message(f"Imported macro (Mode: {mode}) from {file_path}")

            self._invalidate_grouped_actions() # Actually we just built them, but safe to refresh
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

        if 'Executing high-level' not in message:
            self.root.after(0, self._update_log_text, log_message)

    def _update_log_text(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def highlight_playing_action(self, action_index):
        real_idx = action_index + self.playback_idx_offset
        self.root.after(0, self._update_highlight, real_idx)

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
            on_complete_callback=self.on_action_edit_complete
        )
    def on_action_edit_complete(self):
        self._invalidate_grouped_actions()
        self._populate_treeview()

    def _setup_quick_slots_tab(self):
        canvas = tk.Canvas(self.quick_slots_frame)
        scrollbar = ttk.Scrollbar(self.quick_slots_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.slot_vars = {}
        for i in range(1, 10):
            frame = ttk.LabelFrame(scrollable_frame, text=f"Slot {i} (Ctrl+Alt+{i})")
            frame.pack(fill="x", padx=5, pady=5, expand=True)
            
            path_var = tk.StringVar(value=self.quick_slots.get(str(i), ""))
            self.slot_vars[i] = path_var
            
            entry = ttk.Entry(frame, textvariable=path_var, state="readonly")
            entry.pack(side="left", fill="x", expand=True, padx=5)
            
            load_btn = ttk.Button(frame, text="Load", command=lambda idx=i: self.load_quick_slot_file(idx))
            load_btn.pack(side="left", padx=2)
            
            clear_btn = ttk.Button(frame, text="Clear", command=lambda idx=i: self.clear_quick_slot(idx))
            clear_btn.pack(side="left", padx=2)
            
            play_btn = ttk.Button(frame, text="Play", command=lambda idx=i: self.play_quick_slot(idx))
            play_btn.pack(side="left", padx=2)

    def load_quick_slot_file(self, slot_idx):
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON Macro Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            self.quick_slots[str(slot_idx)] = file_path
            self.slot_vars[slot_idx].set(file_path)
            self.save_quick_slots_config()

    def clear_quick_slot(self, slot_idx):
        if str(slot_idx) in self.quick_slots:
            del self.quick_slots[str(slot_idx)]
            self.slot_vars[slot_idx].set("")
            self.save_quick_slots_config()

    def load_quick_slots_config(self):
        try:
            with open("quick_slots.json", "r") as f:
                self.quick_slots = json.load(f)
        except FileNotFoundError:
            self.quick_slots = {}
        except Exception as e:
            self.add_log_message(f"Error loading quick slots: {e}")
            self.quick_slots = {}

    def save_quick_slots_config(self):
        try:
            with open("quick_slots.json", "w") as f:
                json.dump(self.quick_slots, f)
        except Exception as e:
            self.add_log_message(f"Error saving quick slots: {e}")

    def register_quick_slot_hotkeys(self):
        for i in range(1, 10):
            hotkey = f"ctrl+alt+{i}"
            try:
                keyboard.add_hotkey(hotkey, lambda idx=i: self.root.after(0, self.play_quick_slot, idx))
            except Exception as e:
                self.add_log_message(f"Failed to register hotkey {hotkey}: {e}")

    def play_quick_slot(self, slot_idx):
        file_path = self.quick_slots.get(str(slot_idx))
        if not file_path:
            self.add_log_message(f"Slot {slot_idx} is empty.")
            return
        
        if self.is_recording or self.is_playing:
            self.add_log_message("Cannot play quick slot while recording or playing.")
            return
        
        self.add_log_message(f"Playing Quick Slot {slot_idx}: {file_path}")
        
        # Load and play
        try:
            with open(file_path, 'r') as f:
                loaded_data = json.load(f)
            
            new_events = [_deserialize_event(e) for e in loaded_data.get('events', [])]
            new_events = [e for e in new_events if e is not None]
            
            if not new_events:
                self.add_log_message("Macro file contains no valid events.")
                return
            
            # Update macro_data (replace mode)
            self.macro_data = {
                'mode': loaded_data.get('mode', 'absolute'),
                'origin': loaded_data.get('origin', (0,0)),
                'events': new_events
            }
            
            # Load grouped actions if available
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
            
            self._populate_treeview()
            self.start_playing()
            
        except Exception as e:
            self.add_log_message(f"Error playing quick slot: {e}")

    def insert_loop(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select actions to wrap in a loop.")
            return
        
        import tkinter.simpledialog as simpledialog
        count = simpledialog.askinteger("Loop Count", "Enter loop count (0 for infinite):", minvalue=0, initialvalue=1)
        if count is None: return
        
        # Get indices
        indices = sorted([self.tree.index(item) for item in selected_items])
        start_action_idx = indices[0]
        end_action_idx = indices[-1]
        
        start_action = self.visible_actions[start_action_idx]
        end_action = self.visible_actions[end_action_idx]
        
        raw_start_idx = start_action.indices[0]
        raw_end_idx = end_action.indices[-1]
        
        # Create Logic Events
        start_event = (start_action.start_time, {'logic_type': 'loop_start', 'count': count})
        end_event = (end_action.end_time, {'logic_type': 'loop_end'})
        
        # Insert into macro_data['events']
        # Insert End first to not mess up Start index
        self.macro_data['events'].insert(raw_end_idx + 1, end_event)
        self.macro_data['events'].insert(raw_start_idx, start_event)
        
        self._invalidate_grouped_actions()
        self._populate_treeview()
        self.add_log_message(f"Inserted Loop (Count: {count}) around actions {start_action_idx+1}-{end_action_idx+1}")

    def insert_color_wait(self):
        messagebox.showinfo("Color Picker", "Move mouse to target pixel and press 'C' to capture.")
        self.root.withdraw()
        self.picking_color = True
        self._check_color_pick_key()

    def _check_color_pick_key(self):
        if not getattr(self, 'picking_color', False): return
        
        if keyboard.is_pressed('c'):
            self.picking_color = False
            # Wait for key release to avoid repeated triggers
            while keyboard.is_pressed('c'):
                time.sleep(0.05)
                
            x, y = mouse.get_position()
            rgb = event_utils.get_pixel_color(x, y)
            hex_color = event_utils.rgb_to_hex(rgb)
            
            self._finish_color_pick(x, y, hex_color)
        else:
            self.root.after(50, self._check_color_pick_key)

    def _finish_color_pick(self, x, y, hex_color):
        self.root.deiconify()
        
        import tkinter.simpledialog as simpledialog
        timeout = simpledialog.askinteger("Timeout", f"Captured {hex_color} at ({x}, {y}).\nEnter timeout in seconds:", minvalue=1, initialvalue=10)
        if timeout is None: return
        
        # Insert Logic Event
        selected_items = self.tree.selection()
        if selected_items:
            idx = self.tree.index(selected_items[-1])
            action = self.visible_actions[idx]
            if action.indices:
                insert_idx = action.indices[-1] + 1
            else:
                insert_idx = action.start_index
        else:
            insert_idx = len(self.macro_data['events'])
            
        # Calculate appropriate timestamp (relative)
        if insert_idx > 0:
            prev_time = self.macro_data['events'][insert_idx - 1][0]
            new_time = prev_time + 0.1
        else:
            new_time = 0.0

        event = (new_time, {'logic_type': 'wait_color', 'x': x, 'y': y, 'target_hex': hex_color, 'timeout': timeout})
        self.macro_data['events'].insert(insert_idx, event)
        
        self._invalidate_grouped_actions()
        self._populate_treeview()
        self.add_log_message(f"Inserted Wait Color ({hex_color}) at ({x}, {y})")

    def insert_sound_wait(self):
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            messagebox.showerror("Missing Library", "Please install 'sounddevice' and 'numpy' to use this feature.\npip install sounddevice numpy")
            return
            
        import tkinter.simpledialog as simpledialog
        threshold = simpledialog.askfloat("Sound Threshold", "Enter volume threshold (0.0 - 1.0):", minvalue=0.0, maxvalue=1.0, initialvalue=0.1)
        if threshold is None: return
        
        timeout = simpledialog.askinteger("Timeout", "Enter timeout in seconds:", minvalue=1, initialvalue=10)
        if timeout is None: return
        
        # Insert Logic Event
        selected_items = self.tree.selection()
        if selected_items:
            idx = self.tree.index(selected_items[-1])
            action = self.visible_actions[idx]
            if action.indices:
                insert_idx = action.indices[-1] + 1
            else:
                insert_idx = action.start_index
        else:
            insert_idx = len(self.macro_data['events'])
            
        # Calculate appropriate timestamp (relative)
        if insert_idx > 0:
            prev_time = self.macro_data['events'][insert_idx - 1][0]
            new_time = prev_time + 0.1
        else:
            new_time = 0.0

        event = (new_time, {'logic_type': 'wait_sound', 'threshold': threshold, 'timeout': timeout})
        self.macro_data['events'].insert(insert_idx, event)
        
        self._invalidate_grouped_actions()
        self._populate_treeview()
        self.add_log_message(f"Inserted Wait Sound (Threshold: {threshold})")

    def insert_if_color_block(self):
        """Insert IF Color block around selected actions (IF + ELSE + END IF)"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select actions for IF block (True branch).")
            return
        
        # Get the range of selected actions
        indices = sorted([self.tree.index(item) for item in selected_items])
        start_action_idx = indices[0]
        end_action_idx = indices[-1]
        
        messagebox.showinfo("Color Picker", 
            "Move mouse to target pixel and press 'C' to capture.\n\n"
            "The selected actions will run IF the color matches.\n"
            "Otherwise, they will be skipped.")
        
        self.root.withdraw()
        self.if_color_selection = (start_action_idx, end_action_idx)
        self.picking_if_color = True
        self._check_if_color_pick_key()

    def _check_if_color_pick_key(self):
        if not getattr(self, 'picking_if_color', False): 
            return
        
        if keyboard.is_pressed('c'):
            self.picking_if_color = False
            while keyboard.is_pressed('c'):
                time.sleep(0.05)
            
            x, y = mouse.get_position()
            rgb = event_utils.get_pixel_color(x, y)
            hex_color = event_utils.rgb_to_hex(rgb)
            
            self._finish_if_color_pick(x, y, hex_color)
        else:
            self.root.after(50, self._check_if_color_pick_key)

    def _finish_if_color_pick(self, x, y, hex_color):
        self.root.deiconify()
        
        start_action_idx, end_action_idx = self.if_color_selection
        start_action = self.visible_actions[start_action_idx]
        end_action = self.visible_actions[end_action_idx]
        
        raw_start_idx = start_action.indices[0] if start_action.indices else start_action.start_index
        raw_end_idx = end_action.indices[-1] if end_action.indices else end_action.end_index
        
        # Calculate jump indices (after insertion)
        # Structure: [IF_MATCH] [selected actions] [IF_ELSE] [IF_END]
        # IF matched: execute selected actions, then hit IF_ELSE which jumps to IF_END
        # IF not matched: jump to IF_ELSE+1 = IF_END
        
        num_selected_events = raw_end_idx - raw_start_idx + 1
        
        # Create logic events
        start_time = start_action.start_time
        end_time = end_action.end_time
        
        # IF_MATCH event (at start, before selected actions)
        if_match_event = (start_time, {
            'logic_type': 'if_color_match',
            'x': x, 'y': y, 
            'target_hex': hex_color,
            'else_jump_idx': -1  # Will be calculated after regrouping
        })
        
        # IF_ELSE event (after selected actions)
        if_else_event = (end_time + 0.01, {
            'logic_type': 'if_color_else',
            'end_jump_idx': -1  # Will be calculated after regrouping
        })
        
        # IF_END event (at the very end)
        if_end_event = (end_time + 0.02, {
            'logic_type': 'if_color_end'
        })
        
        # Insert events (in reverse order to maintain indices)
        self.macro_data['events'].insert(raw_end_idx + 1, if_end_event)
        self.macro_data['events'].insert(raw_end_idx + 1, if_else_event)
        self.macro_data['events'].insert(raw_start_idx, if_match_event)
        
        # Now we need to regroup and calculate jump indices
        self._invalidate_grouped_actions()
        self._populate_treeview()
        
        # Find the IF_MATCH, IF_ELSE, IF_END in grouped actions and set jump indices
        if_match_idx = None
        if_else_idx = None
        if_end_idx = None
        
        for i, action in enumerate(self.visible_actions):
            if action.type == 'if_color_match' and if_match_idx is None:
                if action.details.get('target_hex') == hex_color:
                    if_match_idx = i
            elif action.type == 'if_color_else' and if_else_idx is None and if_match_idx is not None:
                if_else_idx = i
            elif action.type == 'if_color_end' and if_end_idx is None and if_else_idx is not None:
                if_end_idx = i
                break
        
        # Update jump indices in the action details
        if if_match_idx is not None and if_else_idx is not None:
            self.visible_actions[if_match_idx].details['else_jump_idx'] = if_else_idx
            # Also update the event data
            evt_idx = self.visible_actions[if_match_idx].start_index
            self.macro_data['events'][evt_idx][1]['else_jump_idx'] = if_else_idx
        
        if if_else_idx is not None and if_end_idx is not None:
            self.visible_actions[if_else_idx].details['end_jump_idx'] = if_end_idx
            evt_idx = self.visible_actions[if_else_idx].start_index
            self.macro_data['events'][evt_idx][1]['end_jump_idx'] = if_end_idx
        
        self._populate_treeview()
        self.add_log_message(f"Inserted IF Color ({hex_color}) block around actions {start_action_idx+1}-{end_action_idx+1}")

    def insert_call_macro(self):
        """Insert a call to another macro file (subroutine)"""
        file_path = filedialog.askopenfilename(
            title="Select Macro to Call",
            defaultextension=".json",
            filetypes=[("JSON Macro Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        # Determine insert position
        selected_items = self.tree.selection()
        if selected_items:
            idx = self.tree.index(selected_items[-1])
            action = self.visible_actions[idx]
            if action.indices:
                insert_idx = action.indices[-1] + 1
            else:
                insert_idx = action.start_index + 1
        else:
            insert_idx = len(self.macro_data['events'])
        
        # Calculate timestamp
        if insert_idx > 0 and insert_idx <= len(self.macro_data['events']):
            prev_time = self.macro_data['events'][insert_idx - 1][0]
            new_time = prev_time + 0.1
        else:
            new_time = 0.0
        
        # Create logic event
        import os
        event = (new_time, {
            'logic_type': 'call_macro',
            'file_path': file_path
        })
        self.macro_data['events'].insert(insert_idx, event)
        
        self._invalidate_grouped_actions()
        self._populate_treeview()
        self.add_log_message(f"Inserted Call Macro: {os.path.basename(file_path)}")

    def insert_if_color_only(self):
        """Insert only IF Color (without ELSE and END IF)"""
        messagebox.showinfo("Color Picker", "Move mouse to target pixel and press 'C' to capture.")
        self.root.withdraw()
        self.if_only_mode = True
        self.picking_simple_if = True
        self._check_simple_if_pick()

    def _check_simple_if_pick(self):
        if not getattr(self, 'picking_simple_if', False):
            return
        
        if keyboard.is_pressed('c'):
            self.picking_simple_if = False
            while keyboard.is_pressed('c'):
                time.sleep(0.05)
            
            x, y = mouse.get_position()
            rgb = event_utils.get_pixel_color(x, y)
            hex_color = event_utils.rgb_to_hex(rgb)
            
            self.root.deiconify()
            self._insert_single_logic_event('if_color_match', {
                'x': x, 'y': y, 'target_hex': hex_color, 'else_jump_idx': -1
            }, f"IF Color ({hex_color})")
        else:
            self.root.after(50, self._check_simple_if_pick)

    def insert_else_only(self):
        """Insert only ELSE"""
        self._insert_single_logic_event('if_color_else', {'end_jump_idx': -1}, "ELSE")

    def insert_end_if_only(self):
        """Insert only END IF"""
        self._insert_single_logic_event('if_color_end', {}, "END IF")

    def _insert_single_logic_event(self, logic_type, details, display_name):
        """Helper to insert a single logic event at selection point"""
        selected_items = self.tree.selection()
        if selected_items:
            idx = self.tree.index(selected_items[-1])
            action = self.visible_actions[idx]
            if action.indices:
                insert_idx = action.indices[-1] + 1
            else:
                insert_idx = action.start_index + 1
        else:
            insert_idx = len(self.macro_data['events'])
        
        if insert_idx > 0 and insert_idx <= len(self.macro_data['events']):
            prev_time = self.macro_data['events'][insert_idx - 1][0]
            new_time = prev_time + 0.01
        else:
            new_time = 0.0
        
        event_data = {'logic_type': logic_type}
        event_data.update(details)
        event = (new_time, event_data)
        self.macro_data['events'].insert(insert_idx, event)
        
        self._invalidate_grouped_actions()
        self._populate_treeview()
        self.add_log_message(f"Inserted {display_name}")
