
import unittest
import json
import os
from dataclasses import dataclass, field

# Mock Actions for testing
@dataclass
class GroupedAction:
    type: str
    start_time: float
    end_time: float
    start_index: int
    end_index: int
    indices: list
    details: dict = field(default_factory=dict)
    display_text: str = ""

# Mocking AppGUI components
class MockApp:
    def __init__(self):
        self.macro_data = {'events': []}
        self.visible_actions = []
        self.log = []

    def add_log_message(self, msg):
        self.log.append(msg)
    
    def _invalidate_grouped_actions(self):
        if 'grouped_actions' in self.macro_data:
            del self.macro_data['grouped_actions']

    def _populate_treeview(self):
        # Simulation of grouping logic
        events = self.macro_data['events']
        actions = []
        i = 0
        while i < len(events):
            t, data = events[i]
            if 'logic_type' in data:
                # Logic Action
                actions.append(GroupedAction(
                    type=data['logic_type'], 
                    start_time=t, end_time=t, 
                    start_index=i, end_index=i, 
                    indices=[], 
                    details=data
                ))
                i += 1
            else:
                # Normal Event (Mocking grouping 2 events = 1 action)
                # Assume Click Down/Up pairs
                if i + 1 < len(events):
                    actions.append(GroupedAction(
                        type='mouse_click', 
                        start_time=t, end_time=events[i+1][0], 
                        start_index=i, end_index=i+1, 
                        indices=[i, i+1]
                    ))
                    i += 2
                else:
                    i += 1
        self.visible_actions = actions
        self.macro_data['grouped_actions'] = actions

    def load_from_dict(self, data):
        # Simplified version of load_events logic
        new_events = data.get('events', [])
        # We assume data is already valid format for test
        self.macro_data = {
            'events': new_events
        }
        self._populate_treeview()

    def insert_loop_mock(self, start_action_idx, end_action_idx, count):
        start_action = self.visible_actions[start_action_idx]
        end_action = self.visible_actions[end_action_idx]
        
        raw_start_idx = start_action.indices[0] if start_action.indices else start_action.start_index
        raw_end_idx = end_action.indices[-1] if end_action.indices else end_action.end_index
        
        start_event = (start_action.start_time, {'logic_type': 'loop_start', 'count': count})
        end_event = (end_action.end_time, {'logic_type': 'loop_end'})
        
        self.macro_data['events'].insert(raw_end_idx + 1, end_event)
        self.macro_data['events'].insert(raw_start_idx, start_event)
        
        self._invalidate_grouped_actions()
        self._populate_treeview()

class TestLoadLoop(unittest.TestCase):
    def test_load_and_loop(self):
        app = MockApp()
        
        # 1. Create Mock Macro Data (2 Clicks)
        # Click 1: 1.0s - 1.1s
        # Click 2: 2.0s - 2.1s
        initial_events = [
            (1.0, {'type': 'mouse_click', 'event_type': 'down'}),
            (1.1, {'type': 'mouse_click', 'event_type': 'up'}),
            (2.0, {'type': 'mouse_click', 'event_type': 'down'}),
            (2.1, {'type': 'mouse_click', 'event_type': 'up'})
        ]
        
        app.load_from_dict({'events': initial_events})
        self.assertEqual(len(app.visible_actions), 2, "Should have 2 actions")
        
        # 2. Insert Loop around ALL actions (0 to 1)
        app.insert_loop_mock(0, 1, 3) # Loop 3 times
        
        # Expected Events: LoopStart, Click1_Down, Click1_Up, Click2_Down, Click2_Up, LoopEnd
        # Indices:          0          1            2            3            4          5
        
        self.assertEqual(len(app.macro_data['events']), 6, "Should have 6 events now")
        self.assertEqual(app.macro_data['events'][0][1]['logic_type'], 'loop_start')
        self.assertEqual(app.macro_data['events'][5][1]['logic_type'], 'loop_end')
        
        self.assertEqual(len(app.visible_actions), 4, "Should have 4 actions (LoopStart, Click1, Click2, LoopEnd)")
        
        # 3. Simulate Playback Logic
        actions = app.visible_actions
        loop_stack = []
        played_sequence = []
        idx = 0
        
        max_ops = 100 # Safety break
        ops = 0
        
        while idx < len(actions) and ops < max_ops:
            ops += 1
            action = actions[idx]
            
            if action.type == 'loop_start':
                count = action.details.get('count', 0)
                if not loop_stack or loop_stack[-1]['start_idx'] != idx:
                    loop_stack.append({'start_idx': idx, 'count': count, 'current': 0})
                idx += 1
                
            elif action.type == 'loop_end':
                if loop_stack:
                    ctx = loop_stack[-1]
                    ctx['current'] += 1
                    if ctx['count'] == 0 or ctx['current'] < ctx['count']:
                        idx = ctx['start_idx'] + 1 # Jump to action AFTER loop start
                        continue
                    else:
                        loop_stack.pop()
                idx += 1
                
            else:
                played_sequence.append(action.type)
                idx += 1
                
        # Expectation: 3 loops of (Click, Click) -> 6 clicks total
        self.assertEqual(len(played_sequence), 6, f"Should play 6 clicks, got {len(played_sequence)}")
        
if __name__ == '__main__':
    unittest.main()
