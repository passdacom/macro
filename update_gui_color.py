import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add button
for i, line in enumerate(lines):
    if 'self.insert_loop_btn.pack(pady=5)' in line:
        indent = "        "
        new_lines = [
            f"{indent}self.insert_color_btn = ttk.Button(editor_button_frame, text=\"Insert Color Wait\", command=self.insert_color_wait)\n",
            f"{indent}self.insert_color_btn.pack(pady=5)\n"
        ]
        lines[i+1:i+1] = new_lines
        print("Added Insert Color Wait button")
        break

# Add methods
last_line = len(lines)
indent = "    "
new_methods = [
    f"\n",
    f"{indent}def insert_color_wait(self):\n",
    f"{indent}    messagebox.showinfo(\"Color Picker\", \"Move mouse to target pixel and press 'C' to capture.\")\n",
    f"{indent}    self.root.withdraw()\n",
    f"{indent}    self.picking_color = True\n",
    f"{indent}    \n",
    f"{indent}    def on_c_press(e):\n",
    f"{indent}        if not getattr(self, 'picking_color', False): return\n",
    f"{indent}        self.picking_color = False\n",
    f"{indent}        keyboard.unhook(on_c_press)\n",
    f"{indent}        \n",
    f"{indent}        x, y = mouse.get_position()\n",
    f"{indent}        rgb = event_utils.get_pixel_color(x, y)\n",
    f"{indent}        hex_color = event_utils.rgb_to_hex(rgb)\n",
    f"{indent}        \n",
    f"{indent}        self.root.after(0, self._finish_color_pick, x, y, hex_color)\n",
    f"{indent}        \n",
    f"{indent}    keyboard.on_press_key('c', on_c_press)\n",
    f"\n",
    f"{indent}def _finish_color_pick(self, x, y, hex_color):\n",
    f"{indent}    self.root.deiconify()\n",
    f"{indent}    \n",
    f"{indent}    import tkinter.simpledialog as simpledialog\n",
    f"{indent}    timeout = simpledialog.askinteger(\"Timeout\", f\"Captured {{hex_color}} at ({{x}}, {{y}}).\\nEnter timeout in seconds:\", minvalue=1, initialvalue=10)\n",
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
    f"{indent}    event = (time.time(), {{'logic_type': 'wait_color', 'x': x, 'y': y, 'target_hex': hex_color, 'timeout': timeout}})\n",
    f"{indent}    self.macro_data['events'].insert(insert_idx, event)\n",
    f"{indent}    \n",
    f"{indent}    self._invalidate_grouped_actions()\n",
    f"{indent}    self._populate_treeview()\n",
    f"{indent}    self.add_log_message(f\"Inserted Wait Color ({{hex_color}}) at ({{x}}, {{y}})\")\n"
]
lines.extend(new_methods)

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
