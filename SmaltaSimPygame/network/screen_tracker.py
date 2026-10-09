import sys
import time
import io
from typing import Optional, Tuple
import pygame

class ScreenTracker:
    def __init__(self, target_window_substr: str = "ComplexSim"):
        self.target_window_substr = target_window_substr
        self.is_focused: bool = True
        self.active_window_title: str = ""
        self.focus_lost_time: Optional[float] = None
        self.total_focus_lost_sec: float = 0.0
        self.focus_lost_count: int = 0
        self.is_windows: bool = sys.platform == "win32"
        self._user32 = None
        self._gdi32 = None

        if self.is_windows:
            import ctypes
            from ctypes import wintypes
            self._ctypes = ctypes
            self._wintypes = wintypes
            self._user32 = ctypes.windll.user32
            self._gdi32 = ctypes.windll.gdi32

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', wintypes.DWORD),
                    ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG),
                    ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD),
                    ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD),
                    ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG),
                    ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD)
                ]
            self._BITMAPINFOHEADER = BITMAPINFOHEADER

    def get_foreground_window_title(self) -> str:
        if not self.is_windows or not self._user32:
            return ""
        try:
            hwnd = self._user32.GetForegroundWindow()
            if not hwnd:
                return ""
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return ""
            buff = self._ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except Exception:
            return ""

    def update_focus(self, pygame_has_focus: bool) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Проверяет состояние фокуса окна.
        Возвращает кортеж: (состояние_изменилось, текст_события, длительность_отсутствия_сек)
        """
        curr_title = self.get_foreground_window_title()
        self.active_window_title = curr_title

        # Считается ли фокус утерянным
        is_now_focused = pygame_has_focus
        if self.is_windows and curr_title:
            # Если активный заголовок не пустой и не содержит название симулятора
            if self.target_window_substr.lower() in curr_title.lower():
                is_now_focused = True
            elif not pygame_has_focus:
                is_now_focused = False

        state_changed = False
        event_msg = None
        lost_duration = None

        now = time.time()
        if self.is_focused and not is_now_focused:
            # Переход: БЫЛ В ФОКУСЕ -> ПОТЕРЯЛ ФОКУС
            self.is_focused = False
            self.focus_lost_time = now
            self.focus_lost_count += 1
            state_changed = True
            other_app = f" ('{curr_title}')" if curr_title else ""
            event_msg = f"Внимание: студент свернул окно симулятора или переключился на другое приложение{other_app}"
        elif not self.is_focused and is_now_focused:
            # Переход: БЫЛ НЕ В ФОКУСЕ -> ВЕРНУЛСЯ
            self.is_focused = True
            lost_duration = 0.0
            if self.focus_lost_time:
                lost_duration = now - self.focus_lost_time
                self.total_focus_lost_sec += lost_duration
                self.focus_lost_time = None
            state_changed = True
            event_msg = f"Студент вернулся в симулятор (отсутствовал {lost_duration:.1f} сек)"

        return state_changed, event_msg, lost_duration

    def capture_screenshot_jpeg(self, max_width: int = 1024, max_height: int = 576) -> Optional[bytes]:
        """
        Захватывает снимок экрана:
        - Если Windows: полный снимок рабочего стола (чтобы видеть любые открытые шпаргалки/окна)
        - Иначе: снимок окна Pygame
        Возвращает байты JPEG или None.
        """
        surf = None

        if self.is_windows and self._user32 and self._gdi32:
            try:
                w = self._user32.GetSystemMetrics(0)
                h = self._user32.GetSystemMetrics(1)
                if w > 0 and h > 0:
                    hdesktop = self._user32.GetDesktopWindow()
                    hdc = self._user32.GetDC(hdesktop)
                    memdc = self._gdi32.CreateCompatibleDC(hdc)
                    hbitmap = self._gdi32.CreateCompatibleBitmap(hdc, w, h)
                    self._gdi32.SelectObject(memdc, hbitmap)

                    # SRCCOPY (0x00CC0020) | CAPTUREBLT (0x40000000)
                    self._gdi32.BitBlt(memdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020 | 0x40000000)

                    bmi = self._BITMAPINFOHEADER()
                    bmi.biSize = self._ctypes.sizeof(self._BITMAPINFOHEADER)
                    bmi.biWidth = w
                    bmi.biHeight = -h  # top-down DIB
                    bmi.biPlanes = 1
                    bmi.biBitCount = 32
                    bmi.biCompression = 0

                    buf_size = w * h * 4
                    raw_data = self._ctypes.create_string_buffer(buf_size)
                    self._gdi32.GetDIBits(memdc, hbitmap, 0, h, raw_data, self._ctypes.byref(bmi), 0)

                    # Освобождение ресурсов GDI
                    self._gdi32.DeleteObject(hbitmap)
                    self._gdi32.DeleteDC(memdc)
                    self._user32.ReleaseDC(hdesktop, hdc)

                    surf = pygame.image.frombuffer(raw_data.raw, (w, h), 'BGRA')
            except Exception:
                surf = None

        if surf is None:
            # Fallback к surface pygame
            try:
                cur_surf = pygame.display.get_surface()
                if cur_surf:
                    surf = cur_surf.copy()
            except Exception:
                surf = None

        if surf is None:
            return None

        # Масштабируем снимок под оптимальный размер
        try:
            cur_w, cur_h = surf.get_size()
            scale = min(max_width / cur_w, max_height / cur_h, 1.0)
            target_w = max(1, int(cur_w * scale))
            target_h = max(1, int(cur_h * scale))

            if target_w != cur_w or target_h != cur_h:
                scaled_surf = pygame.transform.smoothscale(surf, (target_w, target_h))
            else:
                scaled_surf = surf

            bio = io.BytesIO()
            pygame.image.save(scaled_surf, bio, 'JPEG')
            return bio.getvalue()
        except Exception:
            return None
