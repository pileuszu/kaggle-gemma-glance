import pyautogui
from PIL import Image, ImageDraw
import os
from datetime import datetime
import ctypes

class TextExtractor:
    def __init__(self):
        # DPI 배율 확인 (윈도우 전용)
        try:
            # 88: LOGPIXELSX
            hdc = ctypes.windll.user32.GetDC(0)
            self.dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
            ctypes.windll.user32.ReleaseDC(0, hdc)
            self.scale_factor = self.dpi / 96.0
        except Exception:
            self.scale_factor = 1.0
        print(f"[시스템] 인식된 DPI 배율: {self.scale_factor} (DPI: {self.dpi if hasattr(self, 'dpi') else 'unknown'})")

    def capture_area_around_mouse(self, size=300):
        try:
            # 1. 마우스 위치 캡처 (논리 좌표)
            x, y = pyautogui.position()
            
            # DPI 배율 보정: 
            # SetProcessDpiAwareness(2) 상태에서는 pyautogui.position()이 물리 좌표를 반환할 수 있습니다.
            # 하지만 일부 환경에서는 여전히 논리 좌표와 물리 좌표 간의 혼선이 있을 수 있습니다.
            # 만약 좌표가 어긋난다면 여기서 보정 로직을 추가합니다.
            
            # 현재 이미지에서 점이 아래/오른쪽에 찍혔다면, 캡처 영역이 너무 위/왼쪽으로 잡힌 것일 수 있습니다.
            # 하지만 사용자의 스크린샷을 보면 텍스트는 중앙에 오는데 점만 아래에 있는 것으로 보아, 
            # 캡처 영역 계산은 맞는데 점을 찍는 좌표가 이미지 크기와 안 맞는 것일 수도 있습니다.
            
            left, top = x - size // 2, y - size // 2
            screenshot = pyautogui.screenshot(region=(left, top, size, size))
            
            # 2. 반투명 빨간 점 가이드 추가
            # 캡처된 이미지의 크기에 맞춰 정중앙에 점을 찍습니다.
            overlay = Image.new('RGBA', screenshot.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # 캡처된 이미지의 실제 크기 기반 중앙값
            img_w, img_h = screenshot.size
            center_x, center_y = img_w // 2, img_h // 2
            
            r = 15
            draw.ellipse((center_x-r, center_y-r, center_x+r, center_y+r), fill=(255, 0, 0, 80))
            
            # 합성
            screenshot = screenshot.convert("RGBA")
            combined = Image.alpha_composite(screenshot, overlay)
            final_image = combined.convert("RGB")

            # 3. 디버그용 이미지 저장
            debug_dir = "debug_images"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = os.path.join(debug_dir, f"capture_{timestamp}.png")
            final_image.save(file_path)
            print(f"[디버그] 캡처 이미지 저장됨 (중앙점: {center_x}, {center_y}): {file_path}")

            return final_image
        except Exception as e:
            print(f"[오류] 캡처 실패: {e}")
            return None
