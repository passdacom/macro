import sys

with open('c:/cli/macro2/event_player.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Insert wait_sound logic
insert_idx = -1
for i, line in enumerate(lines):
    if "elif action.type == 'wait_color':" in line:
        # Find the end of this block
        for j in range(i, len(lines)):
            if "continue" in lines[j] and lines[j].strip().startswith("continue"):
                insert_idx = j + 1
                break
        break

if insert_idx != -1:
    indent = "            "
    new_logic = [
        f"{indent}    elif action.type == 'wait_sound':\n",
        f"{indent}        threshold = action.details.get('threshold', 0.1)\n",
        f"{indent}        timeout = action.details.get('timeout', 10)\n",
        f"{indent}        \n",
        f"{indent}        try:\n",
        f"{indent}            import sounddevice as sd\n",
        f"{indent}            import numpy as np\n",
        f"{indent}            \n",
        f"{indent}            self.log_callback(f\"Waiting for sound (Threshold: {{threshold}})...\")\n",
        f"{indent}            start_wait = time.time()\n",
        f"{indent}            \n",
        f"{indent}            with sd.InputStream() as stream:\n",
        f"{indent}                while True:\n",
        f"{indent}                    if not self.playing: break\n",
        f"{indent}                    \n",
        f"{indent}                    data, overflow = stream.read(1024)\n",
        f"{indent}                    volume = np.abs(data).mean()\n",
        f"{indent}                    \n",
        f"{indent}                    if volume > threshold:\n",
        f"{indent}                        self.log_callback(\"Sound detected!\")\n",
        f"{indent}                        break\n",
        f"{indent}                        \n",
        f"{indent}                    if time.time() - start_wait > timeout:\n",
        f"{indent}                        self.log_callback(\"Wait Sound Timeout!\")\n",
        f"{indent}                        break\n",
        f"{indent}        except Exception as e:\n",
        f"{indent}            self.log_callback(f\"Sound Error: {{e}}\")\n",
        f"{indent}        \n",
        f"{indent}        idx += 1\n",
        f"{indent}        continue\n"
    ]
    lines[insert_idx:insert_idx] = new_logic
    print("Updated event_player.py with wait_sound logic")

with open('c:/cli/macro2/event_player.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
