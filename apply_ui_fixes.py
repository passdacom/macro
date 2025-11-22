import sys
import tkinter as tk

# 1. Modify action_editor.py
with open('c:/cli/macro2/action_editor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

updated_editor = False
for i, line in enumerate(lines):
    if 'self._setup_ui()' in line:
        # Insert centering logic after setup_ui
        indent = "        "
        new_lines = [
            f"{indent}self._setup_ui()\n",
            f"\n",
            f"{indent}# Center window on parent\n",
            f"{indent}self.update_idletasks()\n",
            f"{indent}width = self.winfo_width()\n",
            f"{indent}height = self.winfo_height()\n",
            f"{indent}x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)\n",
            f"{indent}y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)\n",
            f"{indent}self.geometry(f\"+{{x}}+{{y}}\")\n"
        ]
        lines[i] = "".join(new_lines)
        updated_editor = True
        print("Updated action_editor.py with centering logic")
        break

if updated_editor:
    with open('c:/cli/macro2/action_editor.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

# 2. Modify app_gui.py
with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

updated_gui = False
for i, line in enumerate(lines):
    if 'self.root.after(0, self._update_log_text, log_message)' in line:
        # Add filtering
        indent = "        "
        lines[i] = f"{indent}if 'Executing high-level' not in message:\n{indent}    self.root.after(0, self._update_log_text, log_message)\n"
        updated_gui = True
        print("Updated app_gui.py with log filtering")
        break

if updated_gui:
    with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

if not (updated_editor and updated_gui):
    print("ERROR: Could not update all files")
    sys.exit(1)

print("SUCCESS: Applied UI improvements")
