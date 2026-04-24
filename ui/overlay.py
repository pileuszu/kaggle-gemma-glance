from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Frameless, Always on top, Tool window (no taskbar icon)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Layout and Styles
        self.layout = QVBoxLayout(self)
        self.content_box = QWidget()
        self.content_box.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 230);
                border-radius: 12px;
                border: 1px solid rgba(200, 200, 200, 100);
            }
        """)
        
        self.box_layout = QVBoxLayout(self.content_box)
        
        self.label = QLabel("분석 중...")
        self.label.setFont(QFont("Segoe UI", 11))
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: #333; background: transparent; border: none;")
        
        self.box_layout.addWidget(self.label)
        self.layout.addWidget(self.content_box)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        self.content_box.setGraphicsEffect(shadow)

        self.setFixedSize(300, 100)
        self.hide()

    def show_at(self, x, y, text):
        self.label.setText(text)
        # Adjust size based on content
        self.adjustSize()
        self.move(x + 20, y + 20) # Offset from cursor
        self.show()
        
        # Fade-in animation
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def hide_with_fade(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self.anim.start()
