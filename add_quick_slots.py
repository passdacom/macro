import sys

# Read file
with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Add init logic
for i, line in enumerate(lines):
    if 'self.key_mapper_manager = KeyMapperManager()' in line:
        indent = "        "
        new_lines = [
            f"{indent}self.quick_slots = {{}}\n",
            f"{indent}self.load_quick_slots_config()\n",
            f"{indent}self.register_quick_slot_hotkeys()\n"
        ]
        lines[i:i] = new_lines
        print("Added quick slots init logic")
        break

# 2. Modify UI structure (Notebook)
start_idx = -1
for i, line in enumerate(lines):
    if 'editor_frame = ttk.LabelFrame(main_pane, text="Macro Editor")' in line:
        start_idx = i
        break

if start_idx != -1:
    indent = "        "
    new_lines = [
        f"{indent}self.notebook = ttk.Notebook(main_pane)\n",
        f"{indent}main_pane.add(self.notebook, weight=1)\n",
        f"{indent}\n",
        f"{indent}editor_frame = ttk.Frame(self.notebook)\n",
        f"{indent}self.notebook.add(editor_frame, text=\"Editor\")\n",
        f"{indent}\n",
        f"{indent}self.quick_slots_frame = ttk.Frame(self.notebook)\n",
        f"{indent}self.notebook.add(self.quick_slots_frame, text=\"Quick Slots\")\n",
        f"{indent}self._setup_quick_slots_tab()\n"
    ]
    
    # Replace 2 lines (LabelFrame definition and main_pane.add)
    lines[start_idx:start_idx+2] = new_lines
    print("Modified UI to use Notebook")

# 3. Add methods at the end
indent = "    "
new_methods = [
    f"\n",
    f"{indent}def _setup_quick_slots_tab(self):\n",
    f"{indent}    canvas = tk.Canvas(self.quick_slots_frame)\n",
    f"{indent}    scrollbar = ttk.Scrollbar(self.quick_slots_frame, orient=\"vertical\", command=canvas.yview)\n",
    f"{indent}    scrollable_frame = ttk.Frame(canvas)\n",
    f"{indent}    \n",
    f"{indent}    scrollable_frame.bind(\n",
    f"{indent}        \"<Configure>\",\n",
    f"{indent}        lambda e: canvas.configure(scrollregion=canvas.bbox(\"all\"))\n",
    f"{indent}    )\n",
    f"{indent}    \n",
    f"{indent}    canvas.create_window((0, 0), window=scrollable_frame, anchor=\"nw\")\n",
    f"{indent}    canvas.configure(yscrollcommand=scrollbar.set)\n",
    f"{indent}    \n",
    f"{indent}    canvas.pack(side=\"left\", fill=\"both\", expand=True)\n",
    f"{indent}    scrollbar.pack(side=\"right\", fill=\"y\")\n",
    f"{indent}    \n",
    f"{indent}    self.slot_vars = {{}}\n",
    f"{indent}    for i in range(1, 10):\n",
    f"{indent}        frame = ttk.LabelFrame(scrollable_frame, text=f\"Slot {{i}} (Ctrl+Alt+{{i}})\")\n",
    f"{indent}        frame.pack(fill=\"x\", padx=5, pady=5, expand=True)\n",
    f"{indent}        \n",
    f"{indent}        path_var = tk.StringVar(value=self.quick_slots.get(str(i), \"\"))\n",
    f"{indent}        self.slot_vars[i] = path_var\n",
    f"{indent}        \n",
    f"{indent}        entry = ttk.Entry(frame, textvariable=path_var, state=\"readonly\")\n",
    f"{indent}        entry.pack(side=\"left\", fill=\"x\", expand=True, padx=5)\n",
    f"{indent}        \n",
    f"{indent}        load_btn = ttk.Button(frame, text=\"Load\", command=lambda idx=i: self.load_quick_slot_file(idx))\n",
    f"{indent}        load_btn.pack(side=\"left\", padx=2)\n",
    f"{indent}        \n",
    f"{indent}        clear_btn = ttk.Button(frame, text=\"Clear\", command=lambda idx=i: self.clear_quick_slot(idx))\n",
    f"{indent}        clear_btn.pack(side=\"left\", padx=2)\n",
    f"{indent}        \n",
    f"{indent}        play_btn = ttk.Button(frame, text=\"Play\", command=lambda idx=i: self.play_quick_slot(idx))\n",
    f"{indent}        play_btn.pack(side=\"left\", padx=2)\n",
    f"\n",
    f"{indent}def load_quick_slot_file(self, slot_idx):\n",
    f"{indent}    file_path = filedialog.askopenfilename(\n",
    f"{indent}        defaultextension=\".json\",\n",
    f"{indent}        filetypes=[(\"JSON Macro Files\", \"*.json\"), (\"All Files\", \"*.*\")]\n",
    f"{indent}    )\n",
    f"{indent}    if file_path:\n",
    f"{indent}        self.quick_slots[str(slot_idx)] = file_path\n",
    f"{indent}        self.slot_vars[slot_idx].set(file_path)\n",
    f"{indent}        self.save_quick_slots_config()\n",
    f"\n",
    f"{indent}def clear_quick_slot(self, slot_idx):\n",
    f"{indent}    if str(slot_idx) in self.quick_slots:\n",
    f"{indent}        del self.quick_slots[str(slot_idx)]\n",
    f"{indent}        self.slot_vars[slot_idx].set(\"\")\n",
    f"{indent}        self.save_quick_slots_config()\n",
    f"\n",
    f"{indent}def load_quick_slots_config(self):\n",
    f"{indent}    try:\n",
    f"{indent}        with open(\"quick_slots.json\", \"r\") as f:\n",
    f"{indent}            self.quick_slots = json.load(f)\n",
    f"{indent}    except FileNotFoundError:\n",
    f"{indent}        self.quick_slots = {{}}\n",
    f"{indent}    except Exception as e:\n",
    f"{indent}        self.add_log_message(f\"Error loading quick slots: {{e}}\")\n",
    f"{indent}        self.quick_slots = {{}}\n",
    f"\n",
    f"{indent}def save_quick_slots_config(self):\n",
    f"{indent}    try:\n",
    f"{indent}        with open(\"quick_slots.json\", \"w\") as f:\n",
    f"{indent}            json.dump(self.quick_slots, f)\n",
    f"{indent}    except Exception as e:\n",
    f"{indent}        self.add_log_message(f\"Error saving quick slots: {{e}}\")\n",
    f"\n",
    f"{indent}def register_quick_slot_hotkeys(self):\n",
    f"{indent}    for i in range(1, 10):\n",
    f"{indent}        hotkey = f\"ctrl+alt+{{i}}\"\n",
    f"{indent}        try:\n",
    f"{indent}            keyboard.add_hotkey(hotkey, lambda idx=i: self.root.after(0, self.play_quick_slot, idx))\n",
    f"{indent}        except Exception as e:\n",
    f"{indent}            self.add_log_message(f\"Failed to register hotkey {{hotkey}}: {{e}}\")\n",
    f"\n",
    f"{indent}def play_quick_slot(self, slot_idx):\n",
    f"{indent}    file_path = self.quick_slots.get(str(slot_idx))\n",
    f"{indent}    if not file_path:\n",
    f"{indent}        self.add_log_message(f\"Slot {{slot_idx}} is empty.\")\n",
    f"{indent}        return\n",
    f"{indent}    \n",
    f"{indent}    if self.is_recording or self.is_playing:\n",
    f"{indent}        self.add_log_message(\"Cannot play quick slot while recording or playing.\")\n",
    f"{indent}        return\n",
    f"{indent}    \n",
    f"{indent}    self.add_log_message(f\"Playing Quick Slot {{slot_idx}}: {{file_path}}\")\n",
    f"{indent}    \n",
    f"{indent}    # Load and play\n",
    f"{indent}    try:\n",
    f"{indent}        with open(file_path, 'r') as f:\n",
    f"{indent}            loaded_data = json.load(f)\n",
    f"{indent}        \n",
    f"{indent}        new_events = [_deserialize_event(e) for e in loaded_data.get('events', [])]\n",
    f"{indent}        new_events = [e for e in new_events if e is not None]\n",
    f"{indent}        \n",
    f"{indent}        if not new_events:\n",
    f"{indent}            self.add_log_message(\"Macro file contains no valid events.\")\n",
    f"{indent}            return\n",
    f"{indent}        \n",
    f"{indent}        # Update macro_data (replace mode)\n",
    f"{indent}        self.macro_data = {{\n",
    f"{indent}            'mode': loaded_data.get('mode', 'absolute'),\n",
    f"{indent}            'origin': loaded_data.get('origin', (0,0)),\n",
    f"{indent}            'events': new_events\n",
    f"{indent}        }}\n",
    f"{indent}        \n",
    f"{indent}        # Load grouped actions if available\n",
    f"{indent}        loaded_groups = loaded_data.get('grouped_actions')\n",
    f"{indent}        if loaded_groups:\n",
    f"{indent}            self.macro_data['grouped_actions'] = []\n",
    f"{indent}            for action_dict in loaded_groups:\n",
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
    f"{indent}                self.macro_data['grouped_actions'].append(action)\n",
    f"{indent}        \n",
    f"{indent}        self._populate_treeview()\n",
    f"{indent}        self.start_playing()\n",
    f"{indent}        \n",
    f"{indent}    except Exception as e:\n",
    f"{indent}        self.add_log_message(f\"Error playing quick slot: {{e}}\")\n"
]

lines.extend(new_methods)

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: Implemented Quick Slots")
