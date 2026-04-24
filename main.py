import sys
import threading
import time
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QPoint
import keyboard
import pyautogui

from engine.llm_worker import LLMWorker
from capture.text_extractor import TextExtractor
from ui.overlay import OverlayWindow

class AppController(QObject):
    status_changed = Signal(bool)
    request_analysis = Signal(str)

    def __init__(self):
        super().__init__()
        self.analysis_mode = False
        self.last_pos = QPoint(0, 0)
        self.hover_timer = 0
        
        # Initialize Core components
        self.extractor = TextExtractor()
        
        # Setup shortcut Alt+Q
        keyboard.add_hotkey('alt+q', self.toggle_mode)

    def toggle_mode(self):
        self.analysis_mode = not self.analysis_mode
        self.status_changed.emit(self.analysis_mode)
        print(f"Analysis Mode: {'ON' if self.analysis_mode else 'OFF'}")

    def check_hover(self):
        if not self.analysis_mode:
            return

        current_pos = pyautogui.position()
        if abs(current_pos.x - self.last_pos.x()) < 5 and abs(current_pos.y - self.last_pos.y()) < 5:
            self.hover_timer += 0.1
            if self.hover_timer >= 0.8: # 0.8s hover detected
                context = self.extractor.get_context_under_cursor()
                if context:
                    self.request_analysis.emit(context)
                self.hover_timer = -5.0 # Prevent repeated triggers at same spot
        else:
            self.last_pos = QPoint(current_pos.x, current_pos.y)
            self.hover_timer = 0

class GemmaGlanceApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        self.controller = AppController()
        self.overlay = OverlayWindow()
        self.worker = LLMWorker()
        
        self.setup_tray()
        self.setup_connections()
        
        # Timer for mouse tracking
        self.timer = QTimer()
        self.timer.timeout.connect(self.controller.check_hover)
        self.timer.start(100) # 100ms interval

    def setup_connections(self):
        self.controller.status_changed.connect(self.update_tray_icon)
        self.controller.request_analysis.connect(self.handle_analysis_request)
        self.worker.response_ready.connect(self.display_result)
        self.worker.error_occurred.connect(self.display_error)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        self.tray.setIcon(QIcon.fromTheme("system-search")) 
        
        self.menu = QMenu()
        self.toggle_action = QAction("분석 모드 활성화", self.menu)
        self.toggle_action.setCheckable(True)
        self.toggle_action.triggered.connect(self.controller.toggle_mode)
        self.menu.addAction(self.toggle_action)
        
        self.menu.addSeparator()
        self.menu.addAction(QAction("설정", self.menu))
        
        self.exit_action = QAction("종료", self.menu)
        self.exit_action.triggered.connect(self.app.quit)
        self.menu.addAction(self.exit_action)
        
        self.tray.setContextMenu(self.menu)
        self.tray.show()

    @Slot(str)
    def handle_analysis_request(self, context):
        x, y = pyautogui.position()
        self.overlay.show_at(x, y, "Gemma가 분석 중...")
        # Start LLM inference in separate thread or via signal
        threading.Thread(target=self.worker.analyze_context, args=(context,), daemon=True).start()

    @Slot(str)
    def display_result(self, result):
        self.overlay.label.setText(result)
        self.overlay.adjustSize()
        # Overlay stays until mouse moves away (handled by timer logic potentially)
        QTimer.singleShot(5000, self.overlay.hide_with_fade)

    @Slot(str)
    def display_error(self, error):
        print(f"Worker Error: {error}")

    @Slot(bool)
    def update_tray_icon(self, state):
        self.toggle_action.setChecked(state)
        if state:
            self.tray.setToolTip("Gemma Glance: 분석 중...")
        else:
            self.tray.setToolTip("Gemma Glance: 대기 중")
            self.overlay.hide_with_fade()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = GemmaGlanceApp()
    app.run()
