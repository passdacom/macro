import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Add import
for i, line in enumerate(lines):
    if "from import_dialog import ImportDialog" in line:
        lines.insert(i+1, "from help_gui import HelpWindow\n")
        break

# 2. Add Help Menu
# Find where menus are added.
for i, line in enumerate(lines):
    if 'menubar.add_cascade(label="Tools", menu=tools_menu)' in line:
        lines.insert(i+1, """
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Usage Guide", command=self.open_help)
""")
        break

# 3. Add open_help method
# Add it at the end of the class, or before on_close
on_close_idx = -1
for i, line in enumerate(lines):
    if 'def on_close(self):' in line:
        on_close_idx = i
        break

if on_close_idx != -1:
    lines.insert(on_close_idx, """    def open_help(self):
        HelpWindow(self.root)

""")

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
