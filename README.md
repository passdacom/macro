# Advanced Macro Editor v5.2

A powerful Windows macro recorder and editor with advanced logic controls, safety features, and intuitive UX. Built with Python and Tkinter.

## ✨ Key Features

### 1. 🎯 Smart Recording & Playback
- **Intelligent Grouping**: Automatically groups raw input events into logical actions (e.g., "Click", "Double Click", "Ctrl+C").
- **Hardware-Level Accuracy**: Uses scan codes for reliable cross-keyboard compatibility.
- **Speed Control**: Adjust playback speed (0.1x ~ 5x) and repeat count (1-100).

### 2. 🧠 Logic Actions (Advanced Control)
- **Loop System**: Wrap actions with Loop Start/End to repeat sections (supports infinite loops).
- **Color Wait**: Pause macro until a specific pixel matches a target color (offline, no screenshots).
- **Sound Wait**: Trigger actions when audio is detected (e.g., game start beep).

### 3. 🛡️ Safety Features
- **Stop on Sound**: Automatically halts playback if unexpected audio is detected.
- **Prudent Mode**: Learns pixel colors before clicks, then verifies before each subsequent click to prevent mis-clicking.
- **Emergency Stop**: Press `Esc` three times quickly to abort.

### 4. 📂 Flexible File Operations (v5.0 UX Overhaul)
- **Open (Ctrl+O)**: Replace current macro with a file.
- **Import Menu**:
  - **Append to End**: Add macro to the end.
  - **Prepend to Start**: Add macro to the beginning.
  - **Insert at Selection**: Insert after the selected action.
- **Right-Click Context Menu**: Quickly import macros at any position.

### 5. ⚡ Macro Quick Slots
- Assign macros to **Slot 1-9** for instant playback with `Ctrl + Alt + [1-9]`.
- Persistent configuration saves your slots between sessions.

### 6. 📘 Built-in Help System (v5.0)
- **Help > Usage Guide**: Comprehensive, bilingual (Korean/English) documentation.
- Explains all features including loop logic, color/sound waits, and safety modes.

### 7. ⏱️ Advanced Editing
- **Bulk Edit Interval**: Set precise timing for multiple actions (start-to-start intervals).
- **Action Editor**: Double-click any action to fine-tune delays, coordinates, and remarks.
- **Partial Playback**: Test specific action ranges.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Windows OS (required for keyboard/mouse hooks)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/passdacom/macro.git
   cd macro
   ```
2. Install dependencies:
   ```bash
   pip install keyboard mouse sounddevice numpy pyinstaller
   ```

### Running the App
```bash
python main.py
```

### Download Pre-built Executable
Go to [Releases](https://github.com/passdacom/macro/releases) and download `main_v5.0.exe`.

---

## 📖 Usage Guide

### Basic Recording
1. Click **Record** or press `Ctrl + Alt + F5`.
2. Perform your actions.
3. Press `Ctrl + Alt + F5` again to stop.

### Using Logic Actions
- **Insert Loop**: Select actions in the list, click "Insert Loop", set count (0 = infinite).
- **Insert Color Wait**: Click the button, move your mouse to the target pixel, press `C`.
- **Insert Sound Wait**: Set a volume threshold (0.0-1.0) to detect audio triggers.

### Import vs Open
- **File > Open**: Replaces your current macro.
- **File > Import > Append/Prepend**: Merges macros while maintaining timing.
- **Right-Click on List**: Import directly at a specific position.

### Safety Features
- Enable **Stop on Sound** to halt on error beeps.
- Enable **Prudent Mode** for repeated macros that need pixel verification.

### Quick Slots
1. Go to the **Quick Slots** tab.
2. Click **Load** on a slot and select a `.json` file.
3. Press `Ctrl + Alt + [1-9]` anywhere to trigger.

---

## 🛠️ Technical Details

### Event Grouping (`event_grouper.py`)
- Merges raw keyboard/mouse events into high-level actions using heuristic algorithms.
- Handles complex sequences like `Tab` + `Ctrl+C` by flushing buffers on non-modifier keys.

### Safety Mechanisms
- **Prudent Mode**: Uses `ctypes` to read pixel colors (no screenshots) for secure, offline verification.
- **Sound Monitoring**: Background thread with `sounddevice` for real-time audio detection.

### File Format Compatibility
- Supports loading macros created in older versions (backward compatible).
- Automatically adjusts timestamps and indices when merging macros.

---

## 🔮 Future Development

### Planned Features
- **Range-Based Loops**: Select action range (e.g., #3 to #10) and apply a loop, instead of current single-action wrapping.
- **Conditional Logic**: IF/ELSE blocks based on color checks or sound detection.
- **Cloud Sync**: Optional cloud backup for macro files.
- **Macro Templates**: Pre-built macros for common tasks (e.g., web scraping, data entry).

---

## 📜 Version History

### v5.2 (2025-11-26)
- 🍌 **New Icon**: Nano Banana icon.
- 🛑 **Stop on Timeout**: Logic actions (Wait Color/Sound) now force stop the macro if conditions aren't met.
- 🖥️ **UI Improvements**: Wider window, optimized side-by-side layout for Import/Partial controls.
- 🐛 **Critical Fixes**: Solved save/load issues for logic actions and improved sound detection sensitivity.

### v5.0 (2025-01-25)
- 🎨 **UX Overhaul**: Separated "Open" and "Import" menus, added context menu for insertion.
- 📘 **Help System**: Built-in bilingual (KR/EN) usage guide.
- 🔧 **Improved Merging Logic**: Smart timestamp and index updates when importing macros.

### v4.x
- 🛡️ Safety features (Stop on Sound, Prudent Mode).
- 🧠 Logic actions (Loop, Color Wait, Sound Wait).

### v3.x
- ⚡ Quick Slots, Bulk Edit Interval, Recording Confirmation.

---

## 📜 License
This project is open source. Feel free to modify and distribute.

## 🙏 Acknowledgments
Built with love using Python, Tkinter, keyboard, mouse, and sounddevice libraries.