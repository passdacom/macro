import sys

with open('c:/cli/macro2/app_gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Update Treeview Columns
# Find "self.tree = ttk.Treeview"
tree_setup_idx = -1
for i, line in enumerate(lines):
    if 'self.tree = ttk.Treeview' in line:
        tree_setup_idx = i
        break

if tree_setup_idx != -1:
    # Update columns
    # We need to replace lines until "tree_scrollbar.pack"
    # Current lines:
    # 188: self.tree = ttk.Treeview(editor_frame, columns=("No", "Time", "Action", "Details"), show="headings")
    # 189: self.tree.heading("No", text="No.")
    # 190: self.tree.heading("Time", text="Time (s)")
    # 191: self.tree.heading("Action", text="Action")
    # 192: self.tree.heading("Details", text="Details")
    # 193: self.tree.column("No", width=40, anchor="center")
    # 194: self.tree.column("Time", width=80, anchor="center")
    # 195: self.tree.column("Action", width=120)
    # 196: self.tree.column("Details", width=80)
    
    # We will replace these with:
    indent = "        "
    new_setup = [
        f'{indent}self.tree = ttk.Treeview(editor_frame, columns=("No", "Time", "Action", "Remarks"), show="headings")\n',
        f'{indent}self.tree.heading("No", text="No.")\n',
        f'{indent}self.tree.heading("Time", text="Time (s)")\n',
        f'{indent}self.tree.heading("Action", text="Action")\n',
        f'{indent}self.tree.heading("Remarks", text="Remarks")\n',
        f'{indent}self.tree.column("No", width=30, anchor="center")\n',
        f'{indent}self.tree.column("Time", width=60, anchor="center")\n',
        f'{indent}self.tree.column("Action", width=120)\n',
        f'{indent}self.tree.column("Remarks", width=150)\n'
    ]
    
    # Find end of setup (tree_scrollbar definition)
    end_setup_idx = -1
    for j in range(tree_setup_idx, len(lines)):
        if "tree_scrollbar =" in lines[j]:
            end_setup_idx = j
            break
            
    if end_setup_idx != -1:
        lines[tree_setup_idx:end_setup_idx] = new_setup
        print("Updated Treeview columns")

# 2. Update _populate_treeview
# Find "details = first_event_data.get('remarks'"
pop_idx = -1
for i, line in enumerate(lines):
    if "details = first_event_data.get('remarks'" in line:
        pop_idx = i
        break

if pop_idx != -1:
    # Replace line
    indent = "                "
    lines[pop_idx] = f"{indent}details = first_event_data.get('remarks', \"\")\n"
    print("Updated _populate_treeview details logic")

with open('c:/cli/macro2/app_gui.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
