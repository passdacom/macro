import sys

with open('c:/cli/macro2/event_player.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Insert wait_color logic
insert_idx = -1
for i, line in enumerate(lines):
    if "elif action.type == 'loop_end':" in line:
        # Find the end of this block
        for j in range(i, len(lines)):
            if "continue" in lines[j] and lines[j].strip().startswith("continue"):
                insert_idx = j + 1
                break
        break

if insert_idx != -1:
    indent = "            "
    new_logic = [
        f"{indent}    elif action.type == 'wait_color':\n",
        f"{indent}        target_hex = action.details.get('target_hex')\n",
        f"{indent}        x = action.details.get('x')\n",
        f"{indent}        y = action.details.get('y')\n",
        f"{indent}        timeout = action.details.get('timeout', 10)\n",
        f"{indent}        \n",
        f"{indent}        start_wait = time.time()\n",
        f"{indent}        self.log_callback(f\"Waiting for color {{target_hex}} at ({{x}}, {{y}})...\")\n",
        f"{indent}        \n",
        f"{indent}        while True:\n",
        f"{indent}            if not self.playing: break\n",
        f"{indent}            \n",
        f"{indent}            rgb = event_utils.get_pixel_color(x, y)\n",
        f"{indent}            current_hex = event_utils.rgb_to_hex(rgb)\n",
        f"{indent}            \n",
        f"{indent}            if current_hex.lower() == target_hex.lower():\n",
        f"{indent}                self.log_callback(\"Color matched!\")\n",
        f"{indent}                break\n",
        f"{indent}                \n",
        f"{indent}            if time.time() - start_wait > timeout:\n",
        f"{indent}                self.log_callback(\"Wait Color Timeout!\")\n",
        f"{indent}                break\n",
        f"{indent}                \n",
        f"{indent}            time.sleep(0.1)\n",
        f"{indent}        \n",
        f"{indent}        idx += 1\n",
        f"{indent}        continue\n"
    ]
    lines[insert_idx:insert_idx] = new_logic
    print("Updated event_player.py with wait_color logic")

with open('c:/cli/macro2/event_player.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
