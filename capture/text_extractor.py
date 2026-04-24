import win32gui
import win32process
import pyautogui
import time

class TextExtractor:
    def __init__(self):
        pass

    def get_context_under_cursor(self):
        # Get mouse position
        x, y = pyautogui.position()
        
        # Get handle of window under cursor
        hwnd = win32gui.WindowFromPoint((x, y))
        if not hwnd:
            return None
        
        # Get window title and class
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        
        # TODO: More sophisticated extraction (UI Automation or OCR)
        # For now, return window info as context
        context = f"Window: {title} (Class: {cls})"
        
        # Fallback: OCR on small region (to be implemented)
        return context

    def get_word_under_cursor(self):
        # This is the hard part. 
        # Future: Use UI Automation to get element text or OCR.
        return "양자화" # Dummy for testing
