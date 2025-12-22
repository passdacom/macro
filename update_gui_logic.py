import sys

# Modify app_gui.py
with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add buttons
for i, line in enumerate(lines):
    if 'self.bulk_edit_btn.pack(pady=5)' in line:
        indent = "        "
        new_lines = [
            f"{indent}self.insert_loop_btn = ttk.Button(editor_button_frame, text=\"Insert Loop\", command=self.insert_loop)\n",
            f"{indent}self.insert_loop_btn.pack(pady=5)\n"
        ]
        lines[i+1:i+1] = new_lines
        print("Added Insert Loop button")
        break

# Add insert_loop method
# Find end of class
last_line = len(lines)
indent = "    "
new_method = [
    f"\n",
    f"{indent}def insert_loop(self):\n",
    f"{indent}    selected_items = self.tree.selection()\n",
    f"{indent}    if not selected_items:\n",
    f"{indent}        messagebox.showwarning(\"No Selection\", \"Please select actions to wrap in a loop.\")\n",
    f"{indent}        return\n",
    f"{indent}    \n",
    f"{indent}    import tkinter.simpledialog as simpledialog\n",
    f"{indent}    count = simpledialog.askinteger(\"Loop Count\", \"Enter loop count (0 for infinite):\", minvalue=0, initialvalue=1)\n",
    f"{indent}    if count is None: return\n",
    f"{indent}    \n",
    f"{indent}    # Get indices\n",
    f"{indent}    indices = sorted([self.tree.index(item) for item in selected_items])\n",
    f"{indent}    start_action_idx = indices[0]\n",
    f"{indent}    end_action_idx = indices[-1]\n",
    f"{indent}    \n",
    f"{indent}    start_action = self.visible_actions[start_action_idx]\n",
    f"{indent}    end_action = self.visible_actions[end_action_idx]\n",
    f"{indent}    \n",
    f"{indent}    raw_start_idx = start_action.indices[0]\n",
    f"{indent}    raw_end_idx = end_action.indices[-1]\n",
    f"{indent}    \n",
    f"{indent}    # Create Logic Events\n",
    f"{indent}    start_event = (start_action.start_time, {{'logic_type': 'loop_start', 'count': count}})\n",
    f"{indent}    end_event = (end_action.end_time, {{'logic_type': 'loop_end'}})\n",
    f"{indent}    \n",
    f"{indent}    # Insert into macro_data['events']\n",
    f"{indent}    # Insert End first to not mess up Start index\n",
    f"{indent}    self.macro_data['events'].insert(raw_end_idx + 1, end_event)\n",
    f"{indent}    self.macro_data['events'].insert(raw_start_idx, start_event)\n",
    f"{indent}    \n",
    f"{indent}    self._invalidate_grouped_actions()\n",
    f"{indent}    self._populate_treeview()\n",
    f"{indent}    self.add_log_message(f\"Inserted Loop (Count: {{count}}) around actions {{start_action_idx+1}}-{{end_action_idx+1}}\")\n"
]
lines.extend(new_method)

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
