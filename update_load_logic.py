import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Add import
# Find existing imports
import_idx = 0
for i, line in enumerate(lines):
    if "import" in line:
        import_idx = i
    if "class AppGUI" in line:
        break

lines.insert(import_idx + 1, "from import_dialog import ImportDialog\n")
print("Added ImportDialog import")

# 2. Rewrite load_events
# Find start and end of load_events
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "def load_events(self):" in line:
        start_idx = i
        break

if start_idx != -1:
    # Find end (start of next method)
    for j in range(start_idx + 1, len(lines)):
        if "def " in lines[j] and lines[j].startswith("    def "):
            end_idx = j
            break
    
    if end_idx == -1: end_idx = len(lines)

    # New load_events implementation
    indent = "    "
    new_method = [
        f"{indent}def load_events(self):\n",
        f"{indent}    if self.is_recording or self.is_playing:\n",
        f"{indent}        self.add_log_message(\"Cannot load macro while recording or playing.\")\n",
        f"{indent}        return\n",
        f"\n",
        f"{indent}    file_path = filedialog.askopenfilename(\n",
        f"{indent}        defaultextension=\".json\",\n",
        f"{indent}        filetypes=[(\"JSON Macro Files\", \"*.json\"), (\"All Files\", \"*.* \")]\n",
        f"{indent}    )\n",
        f"{indent}    if not file_path:\n",
        f"{indent}        return\n",
        f"\n",
        f"{indent}    try:\n",
        f"{indent}        with open(file_path, 'r') as f:\n",
        f"{indent}            loaded_data = json.load(f)\n",
        f"\n",
        f"{indent}        new_events = [_deserialize_event(e) for e in loaded_data.get('events', [])]\n",
        f"{indent}        new_events = [e for e in new_events if e is not None]\n",
        f"\n",
        f"{indent}        if not new_events:\n",
        f"{indent}            self.add_log_message(\"Loaded macro file contains no valid events.\")\n",
        f"{indent}            return\n",
        f"\n",
        f"{indent}        # Load grouped actions for the new macro\n",
        f"{indent}        new_groups = []\n",
        f"{indent}        loaded_groups_data = loaded_data.get('grouped_actions')\n",
        f"{indent}        if loaded_groups_data:\n",
        f"{indent}            for action_dict in loaded_groups_data:\n",
        f"{indent}                action = GroupedAction(\n",
        f"{indent}                    type=action_dict['type'],\n",
        f"{indent}                    display_text=action_dict['display_text'],\n",
        f"{indent}                    start_time=action_dict['start_time'],\n",
        f"{indent}                    end_time=action_dict['end_time'],\n",
        f"{indent}                    start_index=action_dict['start_index'],\n",
        f"{indent}                    end_index=action_dict['end_index'],\n",
        f"{indent}                    indices=action_dict['indices'],\n",
        f"{indent}                    details=action_dict.get('details', {{}})\n",
        f"{indent}                )\n",
        f"{indent}                new_groups.append(action)\n",
        f"{indent}        else:\n",
        f"{indent}            # If no groups in file, group them now\n",
        f"{indent}            new_groups = event_grouper.group_events(new_events)\n",
        f"\n",
        f"{indent}        # Determine Import Mode\n",
        f"{indent}        current_events = self.macro_data.get('events', [])\n",
        f"{indent}        if not current_events:\n",
        f"{indent}            mode = 'replace'\n",
        f"{indent}            insert_idx = 0\n",
        f"{indent}        else:\n",
        f"{indent}            dialog = ImportDialog(self.root, len(self.visible_actions))\n",
        f"{indent}            self.root.wait_window(dialog)\n",
        f"{indent}            if not dialog.result:\n",
        f"{indent}                return\n",
        f"{indent}            mode, action_insert_idx = dialog.result\n",
        f"\n",
        f"{indent}        # Execute Import Logic\n",
        f"{indent}        if mode == 'replace':\n",
        f"{indent}            self.macro_data = {\n",
        f"{indent}                'mode': loaded_data.get('mode', 'absolute'),\n",
        f"{indent}                'origin': loaded_data.get('origin', (0,0)),\n",
        f"{indent}                'events': new_events,\n",
        f"{indent}                'grouped_actions': new_groups\n",
        f"{indent}            }\n",
        f"{indent}            self.add_log_message(f\"Replaced macro with {{file_path}}\")\n",
        f"\n",
        f"{indent}        else:\n",
        f"{indent}            # Prepare segments\n",
        f"{indent}            current_groups = self.macro_data.get('grouped_actions', [])\n",
        f"{indent}            if not current_groups and current_events:\n",
        f"{indent}                 current_groups = event_grouper.group_events(current_events)\n",
        f"\n",
        f"{indent}            # Calculate split point (event index)\n",
        f"{indent}            if mode == 'prepend':\n",
        f"{indent}                split_event_idx = 0\n",
        f"{indent}                split_group_idx = 0\n",
        f"{indent}            elif mode == 'append':\n",
        f"{indent}                split_event_idx = len(current_events)\n",
        f"{indent}                split_group_idx = len(current_groups)\n",
        f"{indent}            else: # insert\n",
        f"{indent}                if action_insert_idx >= len(current_groups):\n",
        f"{indent}                    split_event_idx = len(current_events)\n",
        f"{indent}                    split_group_idx = len(current_groups)\n",
        f"{indent}                elif action_insert_idx == 0:\n",
        f"{indent}                    split_event_idx = 0\n",
        f"{indent}                    split_group_idx = 0\n",
        f"{indent}                else:\n",
        f"{indent}                    prev_action = current_groups[action_insert_idx - 1]\n",
        f"{indent}                    split_event_idx = prev_action.end_index + 1\n",
        f"{indent}                    split_group_idx = action_insert_idx\n",
        f"\n",
        f"{indent}            events_before = current_events[:split_event_idx]\n",
        f"{indent}            events_after = current_events[split_event_idx:]\n",
        f"{indent}            groups_before = current_groups[:split_group_idx]\n",
        f"{indent}            groups_after = current_groups[split_group_idx:]\n",
        f"\n",
        f"{indent}            # 1. Adjust New Events (Shift timestamps)\n",
        f"{indent}            # Start time for new events should be: (end of before) + 1.0\n",
        f"{indent}            start_time_new = 0.0\n",
        f"{indent}            if events_before:\n",
        f"{indent}                start_time_new = events_before[-1][0] + 1.0\n",
        f"\n",
        f"{indent}            # Shift new events to start at 0 first (normalize), then add start_time_new\n",
        f"{indent}            if new_events:\n",
        f"{indent}                first_new_t = new_events[0][0]\n",
        f"{indent}                shifted_new_events = []\n",
        f"{indent}                for t, e in new_events:\n",
        f"{indent}                    new_t = (t - first_new_t) + start_time_new\n",
        f"{indent}                    # Update event object time if possible\n",
        f"{indent}                    if 'obj' in e and hasattr(e['obj'], 'time'):\n",
        f"{indent}                        try: e['obj'].time = new_t\n",
        f"{indent}                        except: pass\n",
        f"{indent}                    shifted_new_events.append((new_t, e))\n",
        f"{indent}                new_events = shifted_new_events\n",
        f"\n",
        f"{indent}            # 2. Adjust After Events (Shift timestamps)\n",
        f"{indent}            # Start time for after events should be: (end of new) + 1.0\n",
        f"{indent}            start_time_after = start_time_new\n",
        f"{indent}            if new_events:\n",
        f"{indent}                start_time_after = new_events[-1][0] + 1.0\n",
        f"\n",
        f"{indent}            if events_after:\n",
        f"{indent}                first_after_t = events_after[0][0]\n",
        f"{indent}                shifted_after_events = []\n",
        f"{indent}                for t, e in events_after:\n",
        f"{indent}                    new_t = (t - first_after_t) + start_time_after\n",
        f"{indent}                    if 'obj' in e and hasattr(e['obj'], 'time'):\n",
        f"{indent}                        try: e['obj'].time = new_t\n",
        f"{indent}                        except: pass\n",
        f"{indent}                    shifted_after_events.append((new_t, e))\n",
        f"{indent}                events_after = shifted_after_events\n",
        f"\n",
        f"{indent}            # 3. Merge Events\n",
        f"{indent}            merged_events = events_before + new_events + events_after\n",
        f"\n",
        f"{indent}            # 4. Update Group Indices\n",
        f"{indent}            # New groups need to be shifted by len(events_before)\n",
        f"{indent}            offset_new = len(events_before)\n",
        f"{indent}            for g in new_groups:\n",
        f"{indent}                g.start_index += offset_new\n",
        f"{indent}                g.end_index += offset_new\n",
        f"{indent}                g.indices = [i + offset_new for i in g.indices]\n",
        f"\n",
        f"{indent}            # After groups need to be shifted by len(new_events)\n",
        f"{indent}            offset_after = len(new_events)\n",
        f"{indent}            for g in groups_after:\n",
        f"{indent}                g.start_index += offset_after\n",
        f"{indent}                g.end_index += offset_after\n",
        f"{indent}                g.indices = [i + offset_after for i in g.indices]\n",
        f"\n",
        f"{indent}            merged_groups = groups_before + new_groups + groups_after\n",
        f"\n",
        f"{indent}            self.macro_data['events'] = merged_events\n",
        f"{indent}            self.macro_data['grouped_actions'] = merged_groups\n",
        f"{indent}            self.add_log_message(f\"Imported macro (Mode: {{mode}}) from {{file_path}}\")\n",
        f"\n",
        f"{indent}        self._invalidate_grouped_actions() # Actually we just built them, but safe to refresh\n",
        f"{indent}        self._populate_treeview()\n",
        f"{indent}        self.update_button_states()\n",
        f"\n",
        f"{indent}    except Exception as e:\n",
        f"{indent}        self.add_log_message(f\"Error loading file: {{e}}\")\n",
        f"{indent}        messagebox.showerror(\"Error\", f\"Failed to load macro file.\\n\\nDetails: {{e}}\")\n"
    ]
    
    lines[start_idx:end_idx] = new_method
    print("Rewrote load_events")

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
