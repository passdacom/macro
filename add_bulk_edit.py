import sys

# Read the file
with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Add Button
button_added = False
for i, line in enumerate(lines):
    if 'self.bulk_delete_moves_button.pack(pady=5)' in line:
        indent = "        "
        new_lines = [
            f"{indent}self.bulk_delete_moves_button.pack(pady=5)\n",
            f"{indent}self.bulk_edit_btn = ttk.Button(editor_button_frame, text=\"Bulk Edit Interval\", command=self.bulk_edit_interval)\n",
            f"{indent}self.bulk_edit_btn.pack(pady=5)\n"
        ]
        lines[i] = "".join(new_lines) # Replace the pack line with pack + new button
        button_added = True
        print("Added Bulk Edit button")
        break

# 2. Add Methods
methods_added = False
for i, line in enumerate(lines):
    if 'def bulk_delete_mouse_moves(self):' in line:
        # Find end of this method to insert after it
        # Or just insert before it? Before is easier.
        indent = "    "
        new_methods = [
            f"\n",
            f"{indent}def bulk_edit_interval(self):\n",
            f"{indent}    selected_items = self.tree.selection()\n",
            f"{indent}    if not selected_items:\n",
            f"{indent}        messagebox.showwarning(\"No Selection\", \"Please select actions to edit.\")\n",
            f"{indent}        return\n",
            f"{indent}    \n",
            f"{indent}    indices = sorted([self.tree.index(item) for item in selected_items])\n",
            f"{indent}    start_idx = indices[0]\n",
            f"{indent}    end_idx = indices[-1]\n",
            f"{indent}    \n",
            f"{indent}    import tkinter.simpledialog as simpledialog\n",
            f"{indent}    new_interval_str = simpledialog.askstring(\"Bulk Edit Interval\", \n",
            f"{indent}        f\"Enter new delay (seconds) for actions {{start_idx+1}} to {{end_idx+1}}:\")\n",
            f"{indent}    \n",
            f"{indent}    if new_interval_str is None: return\n",
            f"{indent}    \n",
            f"{indent}    try:\n",
            f"{indent}        new_interval = float(new_interval_str)\n",
            f"{indent}        if new_interval < 0: raise ValueError\n",
            f"{indent}    except ValueError:\n",
            f"{indent}        messagebox.showerror(\"Invalid Input\", \"Please enter a valid non-negative number.\")\n",
            f"{indent}        return\n",
            f"{indent}        \n",
            f"{indent}    self._apply_bulk_interval(start_idx, end_idx, new_interval)\n",
            f"{indent}    self._populate_treeview()\n",
            f"{indent}    self.add_log_message(f\"Bulk edited interval for actions {{start_idx+1}}-{{end_idx+1}} to {{new_interval}}s\")\n",
            f"\n",
            f"{indent}def _apply_bulk_interval(self, start_idx, end_idx, new_interval):\n",
            f"{indent}    import copy\n",
            f"{indent}    events = self.macro_data['events']\n",
            f"{indent}    if not self.visible_actions: return\n",
            f"{indent}\n",
            f"{indent}    actions_info = []\n",
            f"{indent}    \n",
            f"{indent}    for i, action in enumerate(self.visible_actions):\n",
            f"{indent}        start_t = events[action.indices[0]][0]\n",
            f"{indent}        end_t = events[action.indices[-1]][0]\n",
            f"{indent}        duration = end_t - start_t\n",
            f"{indent}        \n",
            f"{indent}        if i == 0:\n",
            f"{indent}            gap = 0\n",
            f"{indent}        else:\n",
            f"{indent}            prev_action = self.visible_actions[i-1]\n",
            f"{indent}            prev_end = events[prev_action.indices[-1]][0]\n",
            f"{indent}            gap = start_t - prev_end\n",
            f"{indent}        \n",
            f"{indent}        actions_info.append({{'duration': duration, 'gap': gap, 'indices': action.indices}})\n",
            f"{indent}        \n",
            f"{indent}    for i in range(start_idx, end_idx + 1):\n",
            f"{indent}        actions_info[i]['gap'] = new_interval\n",
            f"{indent}        \n",
            f"{indent}    rebuilt_events = []\n",
            f"{indent}    last_end_time = events[self.visible_actions[0].indices[0]][0]\n",
            f"{indent}    \n",
            f"{indent}    for i, info in enumerate(actions_info):\n",
            f"{indent}        new_start_time = last_end_time + info['gap']\n",
            f"{indent}        original_start_time = events[info['indices'][0]][0]\n",
            f"{indent}        shift = new_start_time - original_start_time\n",
            f"{indent}        \n",
            f"{indent}        for idx in info['indices']:\n",
            f"{indent}            t, data = events[idx]\n",
            f"{indent}            new_data = copy.deepcopy(data)\n",
            f"{indent}            new_t = t + shift\n",
            f"{indent}            \n",
            f"{indent}            if 'time' in new_data:\n",
            f"{indent}                new_data['time'] = new_t\n",
            f"{indent}            \n",
            f"{indent}            if 'obj' in new_data:\n",
            f"{indent}                try:\n",
            f"{indent}                    new_data['obj'].time = new_t\n",
            f"{indent}                except:\n",
            f"{indent}                    pass\n",
            f"{indent}                    \n",
            f"{indent}            rebuilt_events.append((new_t, new_data))\n",
            f"{indent}        \n",
            f"{indent}        last_end_time = new_start_time + info['duration']\n",
            f"{indent}        \n",
            f"{indent}    self.macro_data['events'] = rebuilt_events\n",
            f"\n"
        ]
        lines[i:i] = new_methods # Insert before
        methods_added = True
        print("Added Bulk Edit methods")
        break

if not (button_added and methods_added):
    print("ERROR: Could not add button or methods")
    sys.exit(1)

# Write back
with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: Implemented Bulk Edit Interval")
