import tkinter as tk
from tkinter import ttk, messagebox
import keyboard

# A list of suggested target key names for overriding.
SUGGESTED_TARGET_KEYS = [
    "hangul",
    "hanja",
    "print screen",
    "scroll lock",
    "pause"
]

class MappingEditorWindow(tk.Toplevel):
    """A window to add or edit a single key mapping."""
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.parent = parent
        self.on_complete = on_complete
        self.detected_key_name = None

        self.title("Add/Edit Key Override")
        self.transient(parent)
        self.grab_set()

        self.result = None

        self._setup_ui()
        self.parent.after(100, self.focus_force)
        self.parent.after(200, self.listen_for_key)

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Detected Key
        detected_frame = ttk.LabelFrame(main_frame, text="1. Press the key to override")
        detected_frame.pack(fill="x", pady=5)
        self.detected_key_var = tk.StringVar(value="Press a key...")
        ttk.Entry(detected_frame, textvariable=self.detected_key_var, state="readonly").pack(fill="x", padx=5, pady=5)

        # Mapped Key
        mapped_frame = ttk.LabelFrame(main_frame, text="2. Override with this key name")
        mapped_frame.pack(fill="x", pady=5)
        self.mapped_as_var = tk.StringVar()
        self.mapped_as_combo = ttk.Combobox(mapped_frame, textvariable=self.mapped_as_var, values=SUGGESTED_TARGET_KEYS)
        self.mapped_as_combo.pack(fill="x", padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        button_frame.pack(fill="x")
        self.ok_button = ttk.Button(button_frame, text="OK", command=self._on_ok, state="disabled")
        self.ok_button.pack(side="left")
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="right")

    def listen_for_key(self):
        """Waits for a single key press and updates the UI."""
        try:
            event = keyboard.read_event()
            if event.event_type == 'down':
                self.detected_key_info = f"'{event.name}' (Scan Code: {event.scan_code})"
                self.detected_key_var.set(self.detected_key_info)
                self.ok_button.config(state="normal")
                self.mapped_as_combo.focus()
        except Exception as e:
            messagebox.showerror("Error", f"Could not read key press: {e}", parent=self)
            self.destroy()

    def _on_ok(self):
        mapped_as = self.mapped_as_var.get()
        if not hasattr(self, 'detected_key_info') or not mapped_as:
            messagebox.showwarning("Incomplete", "Please detect a key and select a target name.", parent=self)
            return
        
        self.result = (self.detected_key_info, mapped_as)
        self.on_complete(self.result)
        self.destroy()


class KeyMapperWindow(tk.Toplevel):
    def __init__(self, parent, mapper_manager):
        super().__init__(parent)
        self.parent = parent
        self.mapper_manager = mapper_manager

        self.title("Keyboard Override Mapping")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._populate_mappings()

    def _setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Treeview to display mappings
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("Detected", "Mapped"), show="headings")
        self.tree.heading("Detected", text="Detected Key")
        self.tree.heading("Mapped", text="Overridden As")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Buttons
        button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        button_frame.pack(fill="x")

        self.add_button = ttk.Button(button_frame, text="Add", command=self.add_mapping)
        self.add_button.pack(side="left", padx=(0, 5))

        self.delete_button = ttk.Button(button_frame, text="Delete", command=self.delete_mapping)
        self.delete_button.pack(side="left")

        self.save_button = ttk.Button(button_frame, text="Save & Close", command=self.save_and_close)
        self.save_button.pack(side="right")

    def _populate_mappings(self):
        """Clears and repopulates the treeview with current mappings."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        mappings = self.mapper_manager.get_all_mappings()
        for detected_key, mapped_as in mappings.items():
            self.tree.insert("", "end", values=(detected_key, mapped_as))

    def add_mapping(self):
        """Opens the editor window to add a new mapping."""
        MappingEditorWindow(self, self.on_add_mapping_complete)

    def on_add_mapping_complete(self, result):
        if result:
            detected_key_info, mapped_as = result
            self.mapper_manager.add_or_update_mapping(detected_key_info, mapped_as)
            self._populate_mappings()

    def delete_mapping(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a mapping to delete.")
            return
        
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected mapping(s)?"):
            return

        for item in selected_items:
            detected_key = self.tree.item(item, "values")[0]
            self.mapper_manager.remove_mapping(detected_key)
        
        self._populate_mappings()

    def save_and_close(self):
        self.mapper_manager.save_mappings()
        messagebox.showinfo("Saved", "Key mappings have been saved.", parent=self)
        self.destroy()

if __name__ == '__main__':
    # For testing purposes
    root = tk.Tk()
    root.withdraw() # Hide the main window

    class MockManager:
        _mappings = {"right alt": "Hangul/English Toggle", "key 96": "Numpad 0"}
        def get_all_mappings(self):
            return self._mappings
        def remove_mapping(self, key):
            print(f"Removed {key}")
            if key in self._mappings: del self._mappings
        def add_or_update_mapping(self, key, value):
            print(f"Added/Updated {key}: {value}")
            self._mappings[key] = value
        def save_mappings(self):
            print("Saved mappings.")

    app = KeyMapperWindow(root, MockManager())
    root.mainloop()
