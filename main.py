
import tkinter as tk
import ctypes
import sys
from app_gui import AppGUI

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == '__main__':
    if is_admin():
        # 관리자 권한으로 실행된 경우, 메인 애플리케이션 실행
        root = tk.Tk()
        app = AppGUI(root)
        root.mainloop()
    else:
        # 관리자 권한이 없는 경우, 권한 상승을 요청하며 재실행
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
