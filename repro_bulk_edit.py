
import unittest
from dataclasses import dataclass, field
import time

# Mocking classes from app code
@dataclass
class GroupedAction:
    type: str
    display_text: str
    start_time: float
    end_time: float
    start_index: int
    end_index: int
    indices: list[int] = field(default_factory=list)
    details: dict = field(default_factory=dict)

# Reproducing the logic from app_gui.py _apply_bulk_interval
class MockApp:
    def __init__(self):
        self.macro_data = {'events': []}
        self.visible_actions = []

    def _apply_bulk_interval(self, start_idx, end_idx, new_interval):
        events = self.macro_data['events']
        if not self.visible_actions: return

        new_start_times = []
        
        for i, action in enumerate(self.visible_actions):
            original_start = action.start_time
            
            if i < start_idx:
                new_start = original_start
            elif i <= end_idx:
                if i == 0:
                    new_start = new_interval
                else:
                    new_start = new_start_times[i-1] + new_interval
            else:
                prev_original_start = self.visible_actions[i-1].start_time
                original_interval = original_start - prev_original_start
                new_start = new_start_times[i-1] + original_interval
            
            new_start_times.append(new_start)
                
        rebuilt_events = []
        for i, action in enumerate(self.visible_actions):
            new_start = new_start_times[i]
            original_start = action.start_time
            shift = new_start - original_start
            
            action.start_time = new_start
            action.end_time += shift

            if action.indices:
                for idx in action.indices:
                    t, data = events[idx]
                    import copy
                    new_data = copy.deepcopy(data)
                    new_t = t + shift
                    
                    if 'time' in new_data:
                        new_data['time'] = new_t
                        
                    rebuilt_events.append((new_t, new_data))
            
        self.macro_data['events'] = rebuilt_events

class TestBulkEdit(unittest.TestCase):
    def test_deletion(self):
        app = MockApp()
        # Setup: 
        # Action 0: Click (indices [0, 1])
        # Action 1: Move (indices [2])
        
        # Events
        # 0: Down (0.0s)
        # 1: Up (0.1s)
        # 2: Move (0.5s)
        
        app.macro_data['events'] = [
            (0.0, {'time': 0.0, 'type': 'mouse_click', 'event_type': 'down'}),
            (0.1, {'time': 0.1, 'type': 'mouse_click', 'event_type': 'up'}),
            (0.5, {'time': 0.5, 'type': 'mouse_move', 'x': 100, 'y': 100})
        ]
        
        app.visible_actions = [
            GroupedAction(type='mouse_click', display_text='Click', start_time=0.0, end_time=0.1, start_index=0, end_index=1, indices=[0, 1], details={}),
            GroupedAction(type='mouse_move', display_text='Move', start_time=0.5, end_time=0.5, start_index=2, end_index=2, indices=[2], details={})
        ]
        
        print(f"Initial Events: {len(app.macro_data['events'])}")
        
        # Apply Bulk Edit to BOTH actions (indices 0 and 1)
        # Set interval to 1.0s
        app._apply_bulk_interval(0, 1, 1.0)
        
        print(f"Post Events: {len(app.macro_data['events'])}")
        for e in app.macro_data['events']:
            print(e)
            
        self.assertEqual(len(app.macro_data['events']), 3, "Events should be preserved")
        self.assertAlmostEqual(app.macro_data['events'][0][0], 1.0) # Start should be 1.0
        self.assertAlmostEqual(app.macro_data['events'][2][0], 2.0) # Second action should be at 1.0 + 1.0 = 2.0

if __name__ == '__main__':
    unittest.main()
