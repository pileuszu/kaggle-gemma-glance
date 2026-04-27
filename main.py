import sys
import os
import subprocess
import ctypes

# 윈도우 DPI 인식 강제 설정 (최우선 실행)
try:
    # PROCESS_PER_MONITOR_DPI_AWARE (2) 설정
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# .venv311 가상환경 자동 전환 로직
def ensure_venv():
    venv_python = os.path.join(os.getcwd(), ".venv311", "Scripts", "python.exe")
    if os.path.exists(venv_python) and sys.executable.lower() != venv_python.lower():
        subprocess.run([venv_python] + sys.argv)
        sys.exit()

if __name__ == "__main__":
    ensure_venv()

import threading
import time

# Qt DPI 경고 해결
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_API"] = "pyside6"
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QPoint, Qt
import keyboard
import pyautogui

from engine.llm_worker import LLMWorker
from capture.text_extractor import TextExtractor
from ui.overlay import OverlayWindow

class AppController(QObject):
    status_changed = Signal(bool)
    request_multimodal = Signal(object, str) # image, window_title
    stop_inference = Signal()

    def __init__(self):
        super().__init__()
        self.analysis_mode = False
        self.last_pos = QPoint(0, 0)
        self.hover_timer = 0
        self.extractor = TextExtractor()
        keyboard.add_hotkey('alt+q', self.toggle_mode)

    def toggle_mode(self):
        self.analysis_mode = not self.analysis_mode
        self.status_changed.emit(self.analysis_mode)
        if not self.analysis_mode:
            self.hover_timer = 0
            self.stop_inference.emit() # 모드 끄면 즉시 중단
        print(f"\n[Gemma Glance] 분석 모드: {'ON' if self.analysis_mode else 'OFF'}")

    def check_hover(self, overlay):
        if not self.analysis_mode:
            return

        current_pos = pyautogui.position()
        distance = ((current_pos.x - self.last_pos.x())**2 + (current_pos.y - self.last_pos.y())**2)**0.5
        
        if distance > 40: # 10px -> 40px로 완화 (손떨림 방지 및 의도적 이동 확인)
            if self.hover_timer >= 0.8:
                self.stop_inference.emit()
                overlay.hide_with_fade() # 마우스 움직이면 결과창 닫기
            self.last_pos = QPoint(current_pos.x, current_pos.y)
            self.hover_timer = 0
        else:
            self.hover_timer += 0.1
            if 0.8 <= self.hover_timer < 0.9:
                image = self.extractor.capture_area_around_mouse()
                if image:
                    print(f"[Gemma Glance] 멀티모달 분석 시작 (약 10-30초 소요 예상)")
                    self.request_multimodal.emit(image, "")
                self.hover_timer = 1.0

class GemmaGlanceApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.controller = AppController()
        self.overlay = OverlayWindow()
        self.worker = LLMWorker()
        self.setup_tray()
        self.setup_connections()
        threading.Thread(target=self.worker._initialize_llm, daemon=True).start()
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.controller.check_hover(self.overlay))
        self.timer.start(100)
        print("-" * 50)
        print("Gemma Glance 가동 중!")
        print("▶ 마우스 아래에 반투명 빨간 점이 생기며 분석을 시작합니다.")
        print("-" * 50)

    def setup_connections(self):
        self.controller.status_changed.connect(self.update_tray_icon)
        self.controller.request_multimodal.connect(self.handle_multimodal_request)
        self.controller.stop_inference.connect(self.worker.stop)
        self.worker.response_ready.connect(self.display_result)
        self.worker.partial_response.connect(self.update_overlay_realtime, Qt.ConnectionType.QueuedConnection)
        self.worker.error_occurred.connect(self.display_error)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        icon = self.app.style().standardIcon(self.app.style().StandardPixmap.SP_ComputerIcon)
        self.tray.setIcon(icon)
        self.menu = QMenu()
        self.toggle_action = QAction("분석 모드 활성화", self.menu)
        self.toggle_action.setCheckable(True)
        self.toggle_action.triggered.connect(self.controller.toggle_mode)
        self.menu.addAction(self.toggle_action)
        self.exit_action = QAction("종료", self.menu)
        self.exit_action.triggered.connect(self.app.quit)
        self.menu.addAction(self.exit_action)
        self.tray.setContextMenu(self.menu)
        self.tray.show()

    @Slot(object, str)
    def handle_multimodal_request(self, image, unused_title):
        x, y = pyautogui.position()
        self.overlay.show_at(x, y, "Gemma가 화면 분석 중...")
        threading.Thread(target=self.worker.analyze_multimodal, args=(image,), daemon=True).start()

    @Slot(str)
    def update_overlay_realtime(self, text):
        if not self.controller.analysis_mode: return
        current_text = self.overlay.label.text()
        if "Gemma가 화면 분석 중" in current_text:
            self.overlay.update_text(text, is_append=False)
        else:
            self.overlay.update_text(text, is_append=True)

    @Slot(str)
    def display_result(self, result):
        if not self.controller.analysis_mode: return
        self.overlay.update_text(result, is_append=False)

    @Slot(str)
    def display_error(self, error):
        print(f"\n[오류] {error}")

    @Slot(bool)
    def update_tray_icon(self, state):
        self.toggle_action.setChecked(state)
        if not state:
            self.overlay.hide()
            self.overlay.setWindowOpacity(0)

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = GemmaGlanceApp()
    app.run()
