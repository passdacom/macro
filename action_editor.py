import tkinter as tk
from tkinter import ttk, messagebox
import time
import keyboard
import mouse

def _get_event_obj(event):
    return event[1]['obj']

class ActionEditorWindow(tk.Toplevel):
    def __init__(self, parent, action, action_index, visible_actions, macro_data, on_complete_callback):
        super().__init__(parent)
        self.action = action
        self.action_index = action_index
        self.visible_actions = visible_actions
        self.macro_data = macro_data
        self.on_complete = on_complete_callback

        self.title("Edit Action")
        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        self.geometry("") # Reset geometry to let widgets determine size

        time_frame = ttk.LabelFrame(self, text="Time Edit")
        time_frame.pack(padx=10, pady=10, fill="x")

        if self.action_index == 0:
            label_text = "Start Delay (s):"
            self.current_delay = self.macro_data['events'][self.action.indices[0]][0]
        else:
            label_text = "Delay from previous (s):"
            prev_action = self.visible_actions[self.action_index - 1]
            # For interleaved events, calculate delay from the start of the previous action
            prev_action_start_time = self.macro_data['events'][prev_action.indices[0]][0]
            self.current_delay = self.macro_data['events'][self.action.indices[0]][0] - prev_action_start_time

        ttk.Label(time_frame, text=label_text).pack(side="left", padx=5, pady=5)
        self.delay_var = tk.StringVar(value=f"{self.current_delay:.4f}")
        time_entry = ttk.Entry(time_frame, textvariable=self.delay_var, width=15)
        time_entry.pack(side="left", padx=5, pady=5)

        action_frame = ttk.LabelFrame(self, text="Action Specific Edit")
        action_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.edit_params = {}
        is_editable = self._populate_action_specific_frame(action_frame)

        if not is_editable:
            ttk.Label(action_frame, text="(No action-specific edits available for this type)").pack(pady=20)

        remarks_frame = ttk.LabelFrame(self, text="Remarks")
        remarks_frame.pack(padx=10, pady=5, fill="x")
        self.remarks_var = tk.StringVar()
        remarks_entry = ttk.Entry(remarks_frame, textvariable=self.remarks_var)
        remarks_entry.pack(fill="x", expand=True, padx=5, pady=5)

        # Load existing remarks
        first_event_data = self.macro_data['events'][self.action.start_index][1]
        self.remarks_var.set(first_event_data.get('remarks', ''))

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        ok_button = ttk.Button(button_frame, text="OK", command=self._on_ok)
        ok_button.pack(side="left", padx=10)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        cancel_button.pack(side="left", padx=10)
        
        self.bind('<Return>', lambda e: self._on_ok())
        self.bind('<Escape>', lambda e: self.destroy())
        time_entry.focus_set()
        time_entry.select_range(0, 'end')

    def _populate_action_specific_frame(self, parent_frame):
        action_type = self.action.type

        if action_type in ['mouse_click', 'mouse_drag', 'raw_mouse']:
            first_event_obj = None
            for i in self.action.indices:
                evt = _get_event_obj(self.macro_data['events'][i])
                if isinstance(evt, mouse.ButtonEvent):
                    first_event_obj = evt
                    break
            if not first_event_obj: return False

            click_type_var = tk.StringVar()
            self.edit_params['click_type'] = click_type_var
            ttk.Label(parent_frame, text="Click Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
            ttk.Radiobutton(parent_frame, text="Single", variable=click_type_var, value="single").grid(row=0, column=1, sticky="w")
            ttk.Radiobutton(parent_frame, text="Double", variable=click_type_var, value="double").grid(row=0, column=2, sticky="w")
            is_double = any(isinstance(_get_event_obj(self.macro_data['events'][i]), mouse.ButtonEvent) and _get_event_obj(self.macro_data['events'][i]).event_type == 'double' for i in self.action.indices)
            click_type_var.set("double" if is_double else "single")

            button_type_var = tk.StringVar()
            self.edit_params['button_type'] = button_type_var
            ttk.Label(parent_frame, text="Button:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
            ttk.Radiobutton(parent_frame, text="Left", variable=button_type_var, value="left").grid(row=1, column=1, sticky="w")
            ttk.Radiobutton(parent_frame, text="Right", variable=button_type_var, value="right").grid(row=1, column=2, sticky="w")
            ttk.Radiobutton(parent_frame, text="Middle", variable=button_type_var, value="middle").grid(row=1, column=3, sticky="w")
            button_type_var.set(first_event_obj.button)
            return True

        elif action_type in ['key_press', 'raw_key']:
            first_event_obj = _get_event_obj(self.macro_data['events'][self.action.start_index])
            original_key = first_event_obj.name

            ttk.Label(parent_frame, text="Key:").pack(side="left", padx=5, pady=5)
            key_var = tk.StringVar(value=original_key)
            self.edit_params['new_key'] = key_var
            key_entry = ttk.Entry(parent_frame, textvariable=key_var, width=15)
            key_entry.pack(side="left", padx=5, pady=5)
            key_entry.focus_set()
            key_entry.select_range(0, 'end')
            return True

        return False

    def _on_ok(self):
        self._apply_remarks_edit()
        self._apply_action_edit()
        self.destroy()

    def _apply_remarks_edit(self):
        new_remarks = self.remarks_var.get()
        first_event_data = self.macro_data['events'][self.action.start_index][1]
        
        if new_remarks:
            first_event_data['remarks'] = new_remarks
        elif 'remarks' in first_event_data:
            del first_event_data['remarks']

    def _apply_action_edit(self):
        try:
            new_delay = float(self.delay_var.get())
            if new_delay < 0: raise ValueError("Delay cannot be negative.")
            time_delta = new_delay - self.current_delay
            if abs(time_delta) > 0.0001:
                for i in range(self.action.start_index, len(self.macro_data['events'])):
                    original_time, event_data = self.macro_data['events'][i]
                    self.macro_data['events'][i] = (original_time + time_delta, event_data)
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter a valid non-negative number for delay.\nError: {e}", parent=self)
            return

        action_type = self.action.type
        if action_type in ['mouse_click', 'mouse_drag', 'raw_mouse']:
            self._apply_mouse_edit()
        elif action_type in ['key_press', 'raw_key']:
            self._apply_key_edit()

        self.on_complete()

    def _apply_mouse_edit(self):
        if not self.edit_params: return
        
        new_click_type = self.edit_params['click_type'].get()
        new_button_type = self.edit_params['button_type'].get()
        
        original_event_index = -1
        original_event_obj = None
        for i in self.action.indices:
            evt = _get_event_obj(self.macro_data['events'][i])
            if isinstance(evt, mouse.ButtonEvent):
                original_event_index = i
                original_event_obj = evt
                break
        
        if original_event_obj is None: return

        original_click_type = "double" if original_event_obj.event_type == 'double' else "single"

        if original_event_obj.button != new_button_type:
            for i in self.action.indices:
                evt_time, evt_data = self.macro_data['events'][i]
                evt = evt_data['obj']
                if isinstance(evt, mouse.ButtonEvent):
                    new_evt = mouse.ButtonEvent(evt.event_type, new_button_type, evt.time)
                    evt_data['obj'] = new_evt

        if original_click_type != new_click_type:
            if new_click_type == 'double':
                up_event_index = -1
                for i in self.action.indices:
                    if _get_event_obj(self.macro_data['events'][i]).event_type == mouse.UP:
                        up_event_index = i
                        break
                if up_event_index != -1: del self.macro_data['events'][up_event_index]
                
                evt_time, evt_data = self.macro_data['events'][original_event_index]
                evt = evt_data['obj']
                new_evt = mouse.ButtonEvent(mouse.DOUBLE, new_button_type, evt.time)
                evt_data['obj'] = new_evt
            else:
                evt_time, evt_data = self.macro_data['events'][original_event_index]
                evt = evt_data['obj']
                new_evt = mouse.ButtonEvent(mouse.DOWN, new_button_type, evt.time)
                evt_data['obj'] = new_evt

                down_time, _ = self.macro_data['events'][original_event_index]
                up_event_time = down_time + 0.05
                up_event_obj = mouse.ButtonEvent(mouse.UP, new_button_type, time.time())
                up_event_data = {'obj': up_event_obj, 'pos': evt_data.get('pos')}
                up_event = (up_event_time, up_event_data)
                self.macro_data['events'].insert(original_event_index + 1, up_event)

                for i in range(original_event_index + 2, len(self.macro_data['events'])):
                    original_time, event_data = self.macro_data['events'][i]
                    self.macro_data['events'][i] = (original_time + 0.05, event_data)

    def _apply_key_edit(self):
        if not self.edit_params: return
        new_key = self.edit_params['new_key'].get()
        if not new_key:
            messagebox.showwarning("Invalid Key", "Key cannot be empty.", parent=self)
            return
        
        try:
            new_key_code = keyboard.key_to_scan_codes(new_key)[0]
        except IndexError:
            messagebox.showerror("Invalid Key", f"Could not find a scan code for key: '{new_key}'", parent=self)
            return

        for i in self.action.indices:
            if i < len(self.macro_data['events']):
                evt_time, evt_data = self.macro_data['events'][i]
                evt = evt_data['obj']
                if isinstance(evt, keyboard.KeyboardEvent):
                    new_evt = keyboard.KeyboardEvent(evt.event_type, scan_code=new_key_code, name=new_key)
                    evt_data['obj'] = new_evt