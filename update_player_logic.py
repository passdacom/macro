import sys

with open('c:/cli/macro2/event_player.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We need to replace the loop over grouped_actions.
# Find where it starts.
start_loop = -1
for i, line in enumerate(lines):
    if 'for i, action in enumerate(grouped_actions):' in line:
        start_loop = i
        break

if start_loop != -1:
    indent = "            "
    
    # Replace the loop header and add while loop logic
    lines[start_loop] = f"{indent}idx = 0\n{indent}loop_stack = []\n{indent}while idx < len(grouped_actions):\n{indent}    action = grouped_actions[idx]\n{indent}    i = idx # Compatibility\n"
    
    # Now we need to insert the Logic Action handling at the beginning of the loop
    logic_block = [
        f"{indent}    if not self.playing: break\n",
        f"{indent}    \n",
        f"{indent}    # Logic Actions\n",
        f"{indent}    if action.type == 'loop_start':\n",
        f"{indent}        count = action.details.get('count', 0)\n",
        f"{indent}        if not loop_stack or loop_stack[-1]['start_idx'] != idx:\n",
        f"{indent}            loop_stack.append({{'start_idx': idx, 'count': count, 'current': 0}})\n",
        f"{indent}            self.log_callback(f\"Loop Start: {{count if count > 0 else 'Infinite'}}\")\n",
        f"{indent}        idx += 1\n",
        f"{indent}        continue\n",
        f"{indent}    elif action.type == 'loop_end':\n",
        f"{indent}        if loop_stack:\n",
        f"{indent}            ctx = loop_stack[-1]\n",
        f"{indent}            ctx['current'] += 1\n",
        f"{indent}            if ctx['count'] == 0 or ctx['current'] < ctx['count']:\n",
        f"{indent}                idx = ctx['start_idx'] + 1\n",
        f"{indent}                self.log_callback(f\"Looping back... ({{ctx['current']}}/{{ctx['count'] if ctx['count']>0 else 'Inf'}})\")\n",
        f"{indent}                continue\n",
        f"{indent}            else:\n",
        f"{indent}                self.log_callback(\"Loop finished.\")\n",
        f"{indent}                loop_stack.pop()\n",
        f"{indent}        idx += 1\n",
        f"{indent}        continue\n",
        f"{indent}    \n"
    ]
    lines[start_loop+1:start_loop+1] = logic_block
    
    # Replace `continue` with `idx += 1; continue`
    loop_indent = "            "
    
    for j in range(start_loop + 1, len(lines)):
        line = lines[j]
        if not line.strip(): continue
        if not line.startswith(loop_indent + "    "): # End of loop block
            break
        
        if line.strip() == "continue # Skip the raw event loop for this action":
             lines[j] = line.replace("continue", "idx += 1; continue")
    
    # Add `idx += 1` at the end of the loop block
    end_loop = j
    lines.insert(end_loop, f"{loop_indent}    idx += 1\n")

    print("Updated event_player.py with logic support")

with open('c:/cli/macro2/event_player.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
