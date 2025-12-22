import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Update Menu in __init__
for i, line in enumerate(lines):
    if 'file_menu.add_command(label="Load Macro", command=self.load_events)' in line:
        lines[i] = """        file_menu.add_command(label="Open (Replace)", command=lambda: self.load_events(mode='replace'), accelerator="Ctrl+O")
        import_menu = Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Import", menu=import_menu)
        import_menu.add_command(label="Append to End", command=lambda: self.load_events(mode='append'))
        import_menu.add_command(label="Prepend to Start", command=lambda: self.load_events(mode='prepend'))
        import_menu.add_command(label="Insert at Selection", command=self.import_at_selection)
"""
        break

# 2. Add Context Menu Binding in __init__
for i, line in enumerate(lines):
    if 'self.tree.pack(fill=tk.BOTH, expand=True)' in line:
        lines.insert(i+1, """        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Import Macro Here", command=self.import_at_selection)
        self.tree.bind("<Button-3>", self._show_context_menu)
""")
        break

# 3. Add Ctrl+O binding
for i, line in enumerate(lines):
    if 'self.root.config(menu=menubar)' in line:
        lines.insert(i+1, "        self.root.bind('<Control-o>', lambda e: self.load_events(mode='replace'))\n")
        break

# 4. Add _show_context_menu and import_at_selection methods
load_events_idx = -1
for i, line in enumerate(lines):
    if 'def load_events(self):' in line:
        load_events_idx = i
        break

if load_events_idx != -1:
    lines.insert(load_events_idx, """    def _show_context_menu(self, event):
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

""")

# 5. Refactor load_events
new_load_events = """    def load_events(self, mode='replace', target_index=None):
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
"""

final_lines = []
skip = False
for line in lines:
    if 'def load_events(self):' in line:
        final_lines.append(new_load_events)
        skip = True
    elif skip and line.strip().startswith('def '):
        skip = False
        final_lines.append(line)
    elif not skip:
        final_lines.append(line)

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(final_lines)
