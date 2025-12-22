import tkinter as tk
from tkinter import ttk

class ImportDialog(tk.Toplevel):
    def __init__(self, parent, total_actions):
        super().__init__(parent)
        self.title("Import Macro")
        self.geometry("350x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.total_actions = total_actions
        self.result = None
        
        self.mode_var = tk.StringVar(value="append")
        
        # Main Frame
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="How would you like to import the macro?").pack(anchor="w", pady=(0, 10))
        
        # Radio Buttons
        ttk.Radiobutton(main_frame, text="Replace All (Overwrite)", variable=self.mode_var, value="replace", command=self._update_state).pack(anchor="w", pady=2)
        ttk.Radiobutton(main_frame, text="Append to End", variable=self.mode_var, value="append", command=self._update_state).pack(anchor="w", pady=2)
        ttk.Radiobutton(main_frame, text="Prepend to Start", variable=self.mode_var, value="prepend", command=self._update_state).pack(anchor="w", pady=2)
        
        # Insert Frame
        insert_frame = ttk.Frame(main_frame)
        insert_frame.pack(anchor="w", pady=2, fill="x")
        
        self.insert_radio = ttk.Radiobutton(insert_frame, text="Insert After Action #", variable=self.mode_var, value="insert", command=self._update_state)
        self.insert_radio.pack(side="left")
        
        self.index_spinbox = ttk.Spinbox(insert_frame, from_=0, to=total_actions, width=5)
        self.index_spinbox.set(total_actions if total_actions > 0 else 0)
        self.index_spinbox.pack(side="left", padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side="right")
        
        self._update_state()
        
        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def _update_state(self):
        if self.mode_var.get() == "insert":
            self.index_spinbox.state(["!disabled"])
        else:
            self.index_spinbox.state(["disabled"])

    def _on_ok(self):
        mode = self.mode_var.get()
        idx = 0
        if mode == "insert":
            try:
                idx = int(self.index_spinbox.get())
                if idx < 0 or idx > self.total_actions:
                    raise ValueError
            except ValueError:
                tk.messagebox.showerror("Invalid Input", f"Please enter a valid action number (0-{self.total_actions}).")
                return
        
        self.result = (mode, idx)
        self.destroy()
