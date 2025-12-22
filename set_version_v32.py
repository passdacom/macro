import sys

# Read the file
with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and update the title
updated = False
for i, line in enumerate(lines):
    if 'Advanced Macro Editor v3.1' in line:
        lines[i] = line.replace('v3.1', 'v3.2')
        updated = True
        print(f"Updated title at line {i+1}: {lines[i].strip()}")
        break

if not updated:
    print("ERROR: Could not find title to update")
    sys.exit(1)

# Write back
with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: Updated application version to v3.2")
