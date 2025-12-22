import sys

# Modify event_grouper.py
with open('c:/cli/macro2/event_grouper.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Insert logic check in group() method
for i, line in enumerate(lines):
    if 'current_event = (i, evt_time, evt_data)' in line:
        indent = "            "
        new_lines = [
            f"{indent}# Check for Logic Event\n",
            f"{indent}if 'logic_type' in evt_data:\n",
            f"{indent}    self._flush_buffer()\n",
            f"{indent}    \n",
            f"{indent}    display_text = f\"Logic: {{evt_data['logic_type']}}\"\n",
            f"{indent}    if evt_data['logic_type'] == 'loop_start':\n",
            f"{indent}        count = evt_data.get('count', 0)\n",
            f"{indent}        display_text = f\"Loop Start (Count: {{count if count > 0 else 'Infinite'}})\"\n",
            f"{indent}    elif evt_data['logic_type'] == 'loop_end':\n",
            f"{indent}        display_text = \"Loop End\"\n",
            f"{indent}    elif evt_data['logic_type'] == 'wait_color':\n",
            f"{indent}        display_text = f\"Wait Color ({{evt_data.get('target_hex')}} at {{evt_data.get('x')}},{{evt_data.get('y')}})\"\n",
            f"{indent}    elif evt_data['logic_type'] == 'wait_sound':\n",
            f"{indent}        display_text = \"Wait Sound\"\n",
            f"{indent}        \n",
            f"{indent}    action = GroupedAction(\n",
            f"{indent}        type=evt_data['logic_type'],\n",
            f"{indent}        display_text=display_text,\n",
            f"{indent}        start_time=evt_time,\n",
            f"{indent}        end_time=evt_time,\n",
            f"{indent}        start_index=i,\n",
            f"{indent}        end_index=i,\n",
            f"{indent}        indices=[i],\n",
            f"{indent}        details=evt_data\n",
            f"{indent}    )\n",
            f"{indent}    self.actions.append(action)\n",
            f"{indent}    self.processed_indices.add(i)\n",
            f"{indent}    continue\n",
            f"\n"
        ]
        lines[i+1:i+1] = new_lines
        print("Updated event_grouper.py")
        break

with open('c:/cli/macro2/event_grouper.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
