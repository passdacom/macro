import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add button
for i, line in enumerate(lines):
    if 'self.insert_color_btn.pack(pady=5)' in line:
        indent = "        "
        new_lines = [
            f"{indent}self.insert_sound_btn = ttk.Button(editor_button_frame, text=\"Insert Sound Wait\", command=self.insert_sound_wait)\n",
            f"{indent}self.insert_sound_btn.pack(pady=5)\n"
        ]
        lines[i+1:i+1] = new_lines
        print("Added Insert Sound Wait button")
        break

# Add methods
last_line = len(lines)
indent = "    "
new_methods = [
    f"\n",
    f"{indent}def insert_sound_wait(self):\n",
    f"{indent}    try:\n",
    f"{indent}        import sounddevice as sd\n",
    f"{indent}        import numpy as np\n",
    f"{indent}    except ImportError:\n",
    f"{indent}        messagebox.showerror(\"Missing Library\", \"Please install 'sounddevice' and 'numpy' to use this feature.\\npip install sounddevice numpy\")\n",
    f"{indent}        return\n",
    f"{indent}        \n",
    f"{indent}    import tkinter.simpledialog as simpledialog\n",
    f"{indent}    threshold = simpledialog.askfloat(\"Sound Threshold\", \"Enter volume threshold (0.0 - 1.0):\", minvalue=0.0, maxvalue=1.0, initialvalue=0.1)\n",
    f"{indent}    if threshold is None: return\n",
    f"{indent}    \n",
    f"{indent}    timeout = simpledialog.askinteger(\"Timeout\", \"Enter timeout in seconds:\", minvalue=1, initialvalue=10)\n",
    f"{indent}    if timeout is None: return\n",
    f"{indent}    \n",
    f"{indent}    # Insert Logic Event\n",
    f"{indent}    selected_items = self.tree.selection()\n",
    f"{indent}    if selected_items:\n",
    f"{indent}        idx = self.tree.index(selected_items[-1])\n",
    f"{indent}        action = self.visible_actions[idx]\n",
    f"{indent}        insert_idx = action.indices[-1] + 1\n",
    f"{indent}    else:\n",
    f"{indent}        insert_idx = len(self.macro_data['events'])\n",
    f"{indent}        \n",
    f"{indent}    event = (time.time(), {{'logic_type': 'wait_sound', 'threshold': threshold, 'timeout': timeout}})\n",
    f"{indent}    self.macro_data['events'].insert(insert_idx, event)\n",
    f"{indent}    \n",
    f"{indent}    self._invalidate_grouped_actions()\n",
    f"{indent}    self._populate_treeview()\n",
    f"{indent}    self.add_log_message(f\"Inserted Wait Sound (Threshold: {{threshold}})\")\n"
]
lines.extend(new_methods)

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
