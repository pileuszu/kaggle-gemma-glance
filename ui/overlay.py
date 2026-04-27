from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.label = QLabel("Gemma가 화면 분석 중...")
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(350)
        self.label.setMaximumWidth(500)
        self.label.setContentsMargins(25, 20, 25, 20)
        
        self.label.setStyleSheet("""
            QLabel {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 18px;
                font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
                font-size: 14px;
                line-height: 150%;
            }
        """)
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(30)
        self.shadow.setColor(QColor(0, 0, 0, 180))
        self.shadow.setOffset(0, 5)
        self.label.setGraphicsEffect(self.shadow)
        
        self.main_layout.addWidget(self.label)
        self.current_mouse_pos = QPoint(0, 0)
        self.hide()

    def update_text(self, text, is_append=False):
        """텍스트를 업데이트하고 위치를 재조정합니다."""
        if is_append:
            self.label.setText(self.label.text() + text)
        else:
            self.label.setText(text)
        
        self.reposition()

    def reposition(self):
        """현재 마우스 위치와 창 크기를 고려하여 화면 내 최적의 위치로 이동합니다."""
        self.adjustSize()
        x, y = self.current_mouse_pos.x(), self.current_mouse_pos.y()
        
        screen_geo = self.screen().availableGeometry()
        
        # 기본 위치: 마우스 오른쪽 아래
        new_x = x + 15
        new_y = y + 15
        
        # 우측 경계 체크
        if new_x + self.width() > screen_geo.right():
            new_x = x - self.width() - 15
            
        # 하단 경계 체크 (가장 중요한 부분)
        if new_y + self.height() > screen_geo.bottom():
            # 아래가 모자라면 마우스 위쪽으로 배치
            new_y = y - self.height() - 15
            
        # 상단/좌측 경계 최종 보호
        new_x = max(screen_geo.left(), new_x)
        new_y = max(screen_geo.top(), new_y)
        
        self.move(new_x, new_y)

    def show_at(self, x, y, text=None):
        self.current_mouse_pos = QPoint(x, y)
        if text:
            self.label.setText(text)
        
        self.reposition()
        self.show()

    def hide_with_fade(self):
        self.hide()
