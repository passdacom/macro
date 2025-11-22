# Advanced CLI Macro Editor v3.2

A powerful, cross-platform macro recorder and player with advanced editing capabilities, smart event grouping, and quick slot functionality. Built with Python and Tkinter.

## ✨ Key Features

### 1. 🎯 Precision Recording & Playback
- **Smart Grouping**: Automatically groups raw input events into logical actions (e.g., "Click", "Double Click", "Ctrl+C").
- **Cross-Platform**: Works seamlessly on Windows, utilizing hardware scan codes for accurate playback.
- **Win+V Support**: Correctly handles Windows Clipboard History shortcuts.

### 2. ⚡ Macro Quick Slots (New in v3.2)
- Assign frequently used macros to **Slot 1 ~ Slot 9**.
- Trigger instantly with global hotkeys: **`Ctrl + Alt + [1-9]`**.
- Persistent configuration saves your slots between sessions.

### 3. ⏱️ Advanced Editing
- **Bulk Edit Interval**: Select multiple actions and set a fixed time interval (Start-to-Start) to create perfectly rhythmic macros (e.g., exactly 0.3s apart).
- **Action Editor**: Fine-tune individual actions, modify delays, and add remarks.
- **Partial Playback**: Play only a specific range of actions for testing.

### 4. 🛡️ Reliability & Safety
- **Emergency Stop**: Press `Esc` three times quickly to abort playback.
- **Recording Confirmation**: Prevents accidental overwriting of unsaved macros.
- **Log Filtering**: Clean UI logs focused on important events.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Windows OS (for full feature support)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/passdacom/macro.git
   cd macro
   ```
2. Install dependencies:
   ```bash
   pip install keyboard mouse pyinstaller
   ```

### Running the App
```bash
python main.py
```

### Building Executable (Optional)
To create a standalone `.exe` file:
```bash
pyinstaller --onefile --windowed --name main_v3.2 --icon=NONE main.py
```

---

## 📖 Usage Guide

### 1. Recording
- Click **Record** or press `Ctrl + Alt + F5`.
- Perform your actions.
- Click **Stop Record** or press `Ctrl + Alt + F5` again.

### 2. Editing
- **Delete**: Select actions and click "Delete Selected".
- **Bulk Edit**: Select multiple actions -> Click "Bulk Edit Interval" -> Enter seconds (e.g., `0.5`).
- **Detail Edit**: Double-click an action to edit its specific properties.

### 3. Quick Slots
1. Go to the **Quick Slots** tab.
2. Click **Load** on a slot (e.g., Slot 1) and select a `.json` macro file.
3. Press `Ctrl + Alt + 1` anywhere to play that macro.

### 4. Saving & Loading
- **File > Save Macro** to save your work as a `.json` file.
- **File > Load Macro** to open existing macros.

---

## 🛠️ Technical Details

### Event Grouping Logic (`event_grouper.py`)
- Uses a heuristic algorithm to merge raw `down`/`up` events into high-level actions.
- Handles complex scenarios like `Tab` + `Ctrl+C` sequences by flushing buffers on non-modifier key presses.

### Time Interval Logic
- **Start-to-Start Interval**: The "Delay from previous" in Bulk Edit refers to the time difference between the *start* of the previous action and the *start* of the current action. This ensures consistent timing regardless of action duration.

### Keyboard Compatibility
- Uses `scan_code` for most keys to ensure hardware-level accuracy.
- Uses `name` for special keys (Windows key, Numpad) to handle driver-specific behaviors.

---

## 📜 License
This project is open source. Feel free to modify and distribute.