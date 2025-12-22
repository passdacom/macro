import sys

# Read the file
with open('c:/cli/macro2/event_player.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the keyboard playback logic and modify it
updated = False
for i, line in enumerate(lines):
    if 'if event.name in (\'left windows\', \'right windows\', \'win\'):' in line:
        # This line appears twice (down and up). We need to replace both.
        
        # Construct the new condition
        new_condition = "                            if event.name in ('left windows', 'right windows', 'win') or (len(event.name) == 1 and event.name.isdigit()) or event.name.startswith('numpad'):\n"
        
        lines[i] = new_condition
        updated = True
        # Don't break, continue to find the second occurrence

if not updated:
    print("ERROR: Could not find keyboard playback logic")
    sys.exit(1)

# Write back
with open('c:/cli/macro2/event_player.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: Modified keyboard playback to use names for Number/Numpad keys")
