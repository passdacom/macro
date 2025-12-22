import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add checkboxes to options_frame
# Find "self.always_on_top_var"
insert_idx = -1
for i, line in enumerate(lines):
    if 'self.always_on_top_var = tk.BooleanVar()' in line:
        insert_idx = i
        break

if insert_idx != -1:
    indent = "        "
    new_options = [
        f"{indent}self.stop_on_sound_var = tk.BooleanVar()\n",
        f"{indent}ttk.Checkbutton(options_frame, text=\"Stop on Sound\", variable=self.stop_on_sound_var).pack(side=\"left\", padx=(10,0))\n",
        f"{indent}\n",
        f"{indent}self.prudent_mode_var = tk.BooleanVar()\n",
        f"{indent}ttk.Checkbutton(options_frame, text=\"Prudent Mode\", variable=self.prudent_mode_var).pack(side=\"left\", padx=(10,0))\n"
    ]
    lines[insert_idx+2:insert_idx+2] = new_options # Insert after always_on_top checkbutton
    print("Added safety checkboxes")

# Update play_events call
# Find "self.player.play_events"
for i, line in enumerate(lines):
    if 'self.player.play_events(' in line:
        # We need to pass the new options
        # Current: self.player.play_events(partial_macro, repeat_count, speed_multiplier)
        # New: self.player.play_events(partial_macro, repeat_count, speed_multiplier, stop_on_sound=..., prudent_mode=...)
        
        # There are two calls: one for full play, one for partial.
        
        # 1. Full play (in play_macro)
        # 2. Partial play (in play_partial)
        
        # Let's replace the line carefully.
        if 'partial_macro' in line:
            lines[i] = line.replace(')', ', stop_on_sound=self.stop_on_sound_var.get(), prudent_mode=self.prudent_mode_var.get())')
        elif 'self.macro_data' in line: # Full play
             lines[i] = line.replace(')', ', stop_on_sound=self.stop_on_sound_var.get(), prudent_mode=self.prudent_mode_var.get())')

    print("Updated play_events calls")

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
