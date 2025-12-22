import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'self.root.title("Macro Recorder v' in line:
        lines[i] = '        self.root.title("Macro Recorder v4.2")\n'
        print("Updated version to v4.2")
        break

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
