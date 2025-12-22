import tkinter as tk
from tkinter import ttk, scrolledtext

class HelpWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Macro Recorder User Guide (사용 가이드)")
        self.geometry("700x800")
        self.transient(parent)
        
        # Main Container
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)
        
        # Scrolled Text Area
        self.text_area = scrolledtext.ScrolledText(container, wrap=tk.WORD, width=80, height=45)
        self.text_area.pack(fill="both", expand=True)
        
        # Configure Tags for Formatting
        self.text_area.tag_config("h1", font=("Malgun Gothic", 16, "bold"), foreground="#2c3e50", spacing1=10, spacing2=5)
        self.text_area.tag_config("h2", font=("Malgun Gothic", 12, "bold"), foreground="#34495e", spacing1=15, spacing2=5)
        self.text_area.tag_config("body", font=("Malgun Gothic", 10), spacing1=2, spacing2=2)
        self.text_area.tag_config("eng", font=("Segoe UI", 9), foreground="#7f8c8d", spacing1=0, spacing2=5) # English text style
        self.text_area.tag_config("highlight", font=("Malgun Gothic", 10, "bold"), foreground="#e74c3c")
        
        self._populate_content()
        self.text_area.config(state="disabled") # Read-only
        
        # Close Button
        ttk.Button(container, text="Close (닫기)", command=self.destroy).pack(pady=10)
        
        # Center
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def _add_text(self, text, tag="body"):
        self.text_area.insert(tk.END, text + "\n", tag)

    def _populate_content(self):
        self._add_text("매크로 레코더 사용 가이드", "h1")
        self._add_text("고급 매크로 레코더에 오신 것을 환영합니다. 이 가이드는 모든 기능을 효과적으로 사용하는 방법을 설명합니다.", "body")
        self._add_text("Welcome to the Advanced Macro Recorder. This guide explains how to use all features effectively.", "eng")
        
        # 1. Hotkeys
        self._add_text("1. 글로벌 단축키 (Global Hotkeys)", "h2")
        self._add_text("이 단축키들은 프로그램이 최소화되어 있어도 작동합니다:", "body")
        self._add_text("These hotkeys work even when the application is minimized:", "eng")
        
        self._add_text("• 녹화 시작/정지: Ctrl + Alt + F5", "body")
        self._add_text("  Start/Stop Recording: Ctrl + Alt + F5", "eng")
        
        self._add_text("• 매크로 재생: Ctrl + Alt + F6", "body")
        self._add_text("  Play Macro: Ctrl + Alt + F6", "eng")
        
        self._add_text("• 재생 중지: Ctrl + Alt + F7", "body")
        self._add_text("  Stop Playback: Ctrl + Alt + F7", "eng")
        
        self._add_text("• 비상 정지: ESC 키를 빠르게 3번 누르세요", "highlight")
        self._add_text("  Emergency Stop: Press ESC three times quickly", "eng")

        # 2. File Operations
        self._add_text("2. 파일 관리 (File Operations)", "h2")
        self._add_text("• 열기 (Open, Ctrl+O): 현재 매크로를 불러온 파일로 완전히 교체합니다.", "body")
        self._add_text("  Open (Ctrl+O): Replaces the current macro with the loaded file.", "eng")
        
        self._add_text("• 가져오기 > 뒤에 추가 (Import > Append): 불러온 매크로를 현재 리스트의 맨 뒤에 추가합니다.", "body")
        self._add_text("  Import > Append: Adds the loaded macro to the END of the current list.", "eng")
        
        self._add_text("• 가져오기 > 앞에 추가 (Import > Prepend): 불러온 매크로를 현재 리스트의 맨 앞에 추가합니다.", "body")
        self._add_text("  Import > Prepend: Adds the loaded macro to the START of the current list.", "eng")
        
        self._add_text("• 가져오기 > 선택 위치에 삽입 (Import > At Selection): 불러온 매크로를 현재 선택된 액션 바로 뒤에 삽입합니다.", "body")
        self._add_text("  Import > At Selection: Inserts the loaded macro AFTER the selected action.", "eng")
        
        self._add_text("• 우클릭 메뉴: 리스트에서 우클릭하여 'Import Here'를 선택할 수도 있습니다.", "body")
        self._add_text("  Right-Click Context Menu: You can also right-click on the list to 'Import Here'.", "eng")

        # 3. Logic Actions
        self._add_text("3. 로직 액션 (Logic Actions - 고급 제어)", "h2")
        self._add_text("이 버튼들을 사용하여 매크로에 스마트한 로직을 추가하세요:", "body")
        self._add_text("Use these buttons to add smart logic to your macro:", "eng")
        
        self._add_text("A. 루프 삽입 (Insert Loop - 구간 반복)", "highlight")
        self._add_text("매크로의 특정 구간을 여러 번 반복하게 합니다.", "body")
        self._add_text("Allows you to repeat a specific section of the macro multiple times.", "eng")
        self._add_text("1. 리스트에서 반복할 액션들을 선택합니다.", "body")
        self._add_text("   Select the actions you want to repeat in the list.", "eng")
        self._add_text("2. 'Insert Loop'를 클릭합니다.", "body")
        self._add_text("   Click 'Insert Loop'.", "eng")
        self._add_text("3. 반복 횟수(Loop Count)를 입력합니다 (예: 5). 0을 입력하면 무한 반복합니다.", "body")
        self._add_text("   Enter the Loop Count (e.g., 5). Enter 0 for Infinite Loop.", "eng")
        self._add_text("결과: 'Loop Start'와 'Loop End' 이벤트가 선택한 구간을 감쌉니다.", "body")
        self._add_text("Result: A 'Loop Start' and 'Loop End' event will wrap your selection.", "eng")
        
        self._add_text("B. 색상 대기 삽입 (Insert Color Wait - 픽셀 확인)", "highlight")
        self._add_text("화면의 특정 픽셀이 지정한 색상과 일치할 때까지 매크로를 일시 정지합니다.", "body")
        self._add_text("Pauses the macro until a specific pixel on the screen matches a target color.", "eng")
        self._add_text("1. 'Insert Color Wait'를 클릭합니다. 창이 숨겨집니다.", "body")
        self._add_text("   Click 'Insert Color Wait'. The window will hide.", "eng")
        self._add_text("2. 마우스를 목표 픽셀로 이동합니다.", "body")
        self._add_text("   Move your mouse to the target pixel.", "eng")
        self._add_text("3. 'C' 키를 눌러 색상과 위치를 캡처합니다.", "body")
        self._add_text("   Press 'C' to capture the color and position.", "eng")
        self._add_text("4. 제한 시간(Timeout)을 설정합니다. 시간이 지나도 색상이 안 나타나면 매크로가 멈추거나 계속합니다.", "body")
        self._add_text("   Set a Timeout (seconds). If the color doesn't appear by then, the macro continues or stops.", "eng")
        
        self._add_text("C. 소리 대기 삽입 (Insert Sound Wait - 오디오 트리거)", "highlight")
        self._add_text("큰 소리가 감지될 때까지(예: 게임 시작 소리) 매크로를 일시 정지합니다.", "body")
        self._add_text("Pauses the macro until a loud sound is detected (e.g., a game start sound).", "eng")
        self._add_text("1. 'Insert Sound Wait'를 클릭합니다.", "body")
        self._add_text("   Click 'Insert Sound Wait'.", "eng")
        self._add_text("2. 볼륨 임계값(Threshold)을 설정합니다 (0.0 ~ 1.0). 시스템 사운드는 보통 0.1 정도가 적당합니다.", "body")
        self._add_text("   Set the Volume Threshold (0.0 to 1.0). 0.1 is usually good for system sounds.", "eng")

        # 4. Safety Features
        self._add_text("4. 안전 기능 (Safety Features)", "h2")
        self._add_text("• 소리 감지 중단 (Stop on Sound): 켜져 있으면, 시스템 소리가 감지될 때 매크로가 즉시 정지합니다. 오류 경고음을 잡는 데 유용합니다.", "body")
        self._add_text("  Stop on Sound: If enabled, the macro will STOP immediately if any system sound is detected. Useful for catching error beeps.", "eng")
        
        self._add_text("• 신중 모드 (Prudent Mode): 반복 매크로용입니다. 첫 실행 시 클릭 전 픽셀 색상을 '학습'합니다. 이후 실행부터는 클릭 전에 색상이 일치하는지 확인합니다. 일치하지 않으면 재시도 후 정지하여 오클릭을 방지합니다.", "body")
        self._add_text("  Prudent Mode: For repeated macros. On the 1st run, it 'learns' the pixel color before every click. On subsequent runs, it checks if the color matches before clicking. If not, it retries and then stops to prevent mis-clicking.", "eng")

        # 5. Editing
        self._add_text("5. 매크로 편집 (Editing Macros)", "h2")
        self._add_text("• 더블 클릭: 액션을 더블 클릭하여 상세 내용(지연 시간, 좌표 등)을 수정합니다.", "body")
        self._add_text("  Double-Click an action to edit its details (Delay, Coordinates, etc.).", "eng")
        self._add_text("• 일괄 시간 수정 (Bulk Edit Interval): 여러 액션을 선택하여 지연 시간을 한꺼번에 변경합니다.", "body")
        self._add_text("  Bulk Edit Interval: Change the delay for multiple selected actions at once.", "eng")
        self._add_text("• 삭제 (Delete): 'Delete' 키를 눌러 선택한 액션을 삭제합니다.", "body")
        self._add_text("  Delete: Press 'Delete' key to remove selected actions.", "eng")
        self._add_text("• 이동 (Move): 액션을 드래그 앤 드롭하여 순서를 변경하거나 잘라내기/붙여넣기를 사용합니다.", "body")
        self._add_text("  Move: Drag and drop actions to reorder them (if supported) or use Cut/Paste.", "eng")

        self._add_text("\n\n(c) 2025 Advanced Macro Editor", "body")
