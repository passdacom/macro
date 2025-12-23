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

        # Center window on parent
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        self.geometry("") # Reset geometry to let widgets determine size

        time_frame = ttk.LabelFrame(self, text="Time Edit")
        time_frame.pack(padx=10, pady=10, fill="x")

        if self.action_index == 0:
            label_text = "Start Delay (s):"
            self.current_delay = self.action.start_time
        else:
            label_text = "Delay from previous (s):"
            prev_action = self.visible_actions[self.action_index - 1]
            # Use action start times directly, which is safer and supports logic actions
            prev_action_start_time = prev_action.start_time
            self.current_delay = self.action.start_time - prev_action_start_time
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
        # Use action details if available, otherwise check first event
        if 'remarks' in self.action.details:
             self.remarks_var.set(self.action.details['remarks'])
        elif self.action.indices:
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

        elif action_type in ['wait_color', 'wait_sound']:
            # Timeout
            ttk.Label(parent_frame, text="Timeout (s):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
            timeout_var = tk.StringVar(value=str(self.action.details.get('timeout', 10)))
            self.edit_params['timeout'] = timeout_var
            ttk.Entry(parent_frame, textvariable=timeout_var, width=10).grid(row=0, column=1, sticky="w", padx=5, pady=2)

            # Post-Match Delay
            ttk.Label(parent_frame, text="Post-Match Delay (s):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
            post_delay_var = tk.StringVar(value=str(self.action.details.get('post_delay', 0)))
            self.edit_params['post_delay'] = post_delay_var
            ttk.Entry(parent_frame, textvariable=post_delay_var, width=10).grid(row=1, column=1, sticky="w", padx=5, pady=2)

            if action_type == 'wait_color':
                target_hex = self.action.details.get('target_hex')
                ttk.Label(parent_frame, text=f"Target Color: {target_hex}").grid(row=2, column=0, sticky="w", padx=5, pady=2)
                
                # Color Swatch
                try:
                    canvas = tk.Canvas(parent_frame, width=20, height=20, bg=target_hex, highlightthickness=1, highlightbackground="black")
                    canvas.grid(row=2, column=1, sticky="w", padx=5, pady=2)
                except:
                    pass
            elif action_type == 'wait_sound':
                ttk.Label(parent_frame, text="Threshold (0.0-1.0):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
                threshold_var = tk.StringVar(value=str(self.action.details.get('threshold', 0.1)))
                self.edit_params['threshold'] = threshold_var
                ttk.Entry(parent_frame, textvariable=threshold_var, width=10).grid(row=2, column=1, sticky="w", padx=5, pady=2)
            
            return True

        return False

    def _on_ok(self):
        self._apply_remarks_edit()
        self._apply_action_edit()
        self.destroy()

    def _apply_remarks_edit(self):
        new_remarks = self.remarks_var.get()
        
        # If action has indices, update the first event
        if self.action.indices:
            first_event_data = self.macro_data['events'][self.action.start_index][1]
            if new_remarks:
                first_event_data['remarks'] = new_remarks
            elif 'remarks' in first_event_data:
                del first_event_data['remarks']
        
        # Always update action details for persistence
        if new_remarks:
            self.action.details['remarks'] = new_remarks
        elif 'remarks' in self.action.details:
            del self.action.details['remarks']

    def _apply_action_edit(self):
        try:
            new_delay = float(self.delay_var.get())
            if new_delay < 0: raise ValueError("Delay cannot be negative.")
            time_delta = new_delay - self.current_delay
            if abs(time_delta) > 0.0001:
                # Update action start/end times
                self.action.start_time += time_delta
                self.action.end_time += time_delta
                
                # Update underlying events if they exist OR if it's a virtual action (tied to next event)
                # If indices are empty (Auto-Wait), we assume it affects events starting from start_index
                effective_indices = self.action.indices if self.action.indices else range(self.action.start_index, len(self.macro_data['events']))
                
                # If we have indices, we only update those.
                # BUT if we are shifting time (Delta), we usually want to shift ALL subsequent events too?
                # The logic below (lines 235+) handles subsequent ACTIONS.
                # But here we are updating the EVENTS associated with THIS action.
                
                if self.action.indices:
                     for i in self.action.indices:
                        original_time, event_data = self.macro_data['events'][i]
                        self.macro_data['events'][i] = (original_time + time_delta, event_data)
                else:
                    # Virtual action logic (like Auto-Wait). 
                    # It doesn't own events, so we don't update "its" events.
                    # Instead, we rely on the subseqent action loop to update the real events?
                    # No, Auto-Wait is followed by Click. Click is "Subsequent Action".
                    # So Click's events will be updated by the loop below.
                    # HOWEVER, logic below ONLY updates Action objects (start_time).
                    # It does NOT update underlying events for subsequent actions!
                    # "Note: We don't need to update their events here because..." <- OLD COMMENT
                    # The old comment assumed we looped events range(start_index, len(events)).
                    # But I changed it to loop indices.
                    
                    # FIX: We MUST shift ALL events from start_index onwards to preserve relative timing
                    # if we are inserting delay at this point.
                    pass 

                # Wait, if I shift THIS action, do I shift everything after? 
                # Yes, "time_delta" implies inserting/removing time.
                # So we should shift all raw events starting from this action's start.
                
                for i in range(self.action.start_index, len(self.macro_data['events'])):
                    original_time, event_data = self.macro_data['events'][i]
                    self.macro_data['events'][i] = (original_time + time_delta, event_data)
                
                # Update subsequent actions in the list
                for i in range(self.action_index + 1, len(self.visible_actions)):
                    act = self.visible_actions[i]
                    act.start_time += time_delta
                    act.end_time += time_delta
                    # Note: We don't need to update their events here because the loop above 
                    # (range(self.action.start_index, len(events))) covers ALL subsequent events 
                    # if the actions are sequential. 
                    # However, for logic actions without indices, we MUST update them manually.
                    if not act.indices:
                        # Logic action (like Wait Color) stored in grouped_actions but not events?
                        # Wait, if it's not in events, it's not in macro_data['events'].
                        # But our architecture says logic actions ARE in events usually.
                        # EXCEPT for Auto-Wait Color which is purely synthetic in grouped_actions?
                        # If Auto-Wait is NOT in events, we have a problem: it won't be saved!
                        pass
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter a valid non-negative number for delay.\nError: {e}", parent=self)
            return

        action_type = self.action.type
        if action_type in ['mouse_click', 'mouse_drag', 'raw_mouse']:
            self._apply_mouse_edit()
        elif action_type in ['key_press', 'raw_key']:
            self._apply_key_edit()
        elif action_type in ['wait_color', 'wait_sound']:
            self._apply_wait_edit()

        self.on_complete()

    def _apply_mouse_edit(self):
        if not self.edit_params: return
        
        new_click_type = self.edit_params['click_type'].get()
        new_button_type = self.edit_params['button_type'].get()
        
        # Find the first ButtonEvent in this action (down or double)
        first_btn_event_index = -1
        first_btn_event_obj = None
        first_btn_evt_data = None
        
        for i in self.action.indices:
            if i >= len(self.macro_data['events']):
                continue
            evt_time, evt_data = self.macro_data['events'][i]
            evt = evt_data.get('obj')
            if isinstance(evt, mouse.ButtonEvent) and evt.event_type in ['down', 'double']:
                first_btn_event_index = i
                first_btn_event_obj = evt
                first_btn_evt_data = evt_data
                break
        
        if first_btn_event_obj is None: 
            return
        
        original_click_type = "double" if first_btn_event_obj.event_type == 'double' else "single"
        
        # Update button type for all button events (if changed)
        if first_btn_event_obj.button != new_button_type:
            for i in self.action.indices:
                if i >= len(self.macro_data['events']):
                    continue
                evt_time, evt_data = self.macro_data['events'][i]
                evt = evt_data.get('obj')
                if isinstance(evt, mouse.ButtonEvent):
                    new_evt = mouse.ButtonEvent(evt.event_type, new_button_type, evt.time)
                    evt_data['obj'] = new_evt
        
        # Handle click type conversion
        if original_click_type != new_click_type:
            if new_click_type == 'double':
                # Single -> Double
                # 1. Find and collect all 'up' event indices to delete
                up_indices_to_delete = []
                for i in self.action.indices:
                    if i >= len(self.macro_data['events']):
                        continue
                    evt_time, evt_data = self.macro_data['events'][i]
                    evt = evt_data.get('obj')
                    if isinstance(evt, mouse.ButtonEvent) and evt.event_type == 'up':
                        up_indices_to_delete.append(i)
                
                # 2. Change 'down' to 'double'
                first_btn_evt_data['obj'] = mouse.ButtonEvent('double', new_button_type, first_btn_event_obj.time)
                
                # 3. Delete 'up' events in reverse order (to keep indices valid)
                for idx in sorted(up_indices_to_delete, reverse=True):
                    del self.macro_data['events'][idx]
                
                # 4. Update action metadata
                self.action.type = 'mouse_double_click'
                self.action.display_text = f"Mouse Double Click ({new_button_type})"
                
                # 5. Recalculate indices (only keep the double event index)
                # After deletion, first_btn_event_index may have shifted
                new_index = first_btn_event_index
                for deleted_idx in sorted(up_indices_to_delete):
                    if deleted_idx < first_btn_event_index:
                        new_index -= 1
                
                self.action.indices = [new_index]
                self.action.start_index = new_index
                self.action.end_index = new_index
                
            else:
                # Double -> Single
                # 1. Change 'double' to 'down'
                evt_time = first_btn_event_obj.time
                first_btn_evt_data['obj'] = mouse.ButtonEvent('down', new_button_type, evt_time)
                
                # 2. Insert new 'up' event right after
                up_event_time = evt_time + 0.05
                up_event_obj = mouse.ButtonEvent('up', new_button_type, up_event_time)
                up_event_data = {'obj': up_event_obj, 'pos': first_btn_evt_data.get('pos')}
                up_event = (up_event_time, up_event_data)
                
                insert_position = first_btn_event_index + 1
                self.macro_data['events'].insert(insert_position, up_event)
                
                # 3. Update action metadata
                self.action.type = 'mouse_click'
                self.action.display_text = f"Mouse Click ({new_button_type})"
                
                # 4. Update indices to include both down and up
                self.action.indices = [first_btn_event_index, insert_position]
                self.action.start_index = first_btn_event_index
                self.action.end_index = insert_position


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

    def _apply_wait_edit(self):
        try:
            timeout = float(self.edit_params['timeout'].get())
            post_delay = float(self.edit_params['post_delay'].get())
            if timeout < 0 or post_delay < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Timeout and Post-Match Delay must be non-negative numbers.", parent=self)
            return

        self.action.details['timeout'] = timeout
        self.action.details['post_delay'] = post_delay

        if 'threshold' in self.edit_params:
            try:
                threshold = float(self.edit_params['threshold'].get())
                if not (0 <= threshold <= 1): raise ValueError
                self.action.details['threshold'] = threshold
            except ValueError:
                messagebox.showerror("Invalid Input", "Threshold must be between 0.0 and 1.0.", parent=self)
                return

        # Update the actual event data in macro_data
        # Logic actions are stored as single events
        # Update the actual event data in macro_data
        # Logic actions are stored as single events
        if self.action.indices:
            evt_idx = self.action.indices[0]
            evt_time, evt_data = self.macro_data['events'][evt_idx]
            evt_data.update(self.action.details)
        else:
            # For synthetic actions (Auto-Wait), just updating details is enough 
            # as they are stored in grouped_actions.
            # But wait, if they are not in 'events', they won't be saved unless we save grouped_actions!
            # We DO save grouped_actions now (v5.5 feature).
            pass