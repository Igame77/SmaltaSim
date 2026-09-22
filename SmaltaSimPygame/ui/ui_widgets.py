import pygame
from typing import Callable, Optional, Tuple, List
from config import (
    COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE,
    COLOR_BUTTON_BORDER, COLOR_TEXT, COLOR_TEXT_DIM
)

class UIButton:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        callback: Optional[Callable[[], None]] = None,
        font_size: int = 16,
        is_enabled: bool = True,
        bg_color: Tuple[int, int, int] = COLOR_BUTTON,
        border_radius: int = 4
    ):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.font_size = font_size
        self.is_enabled = is_enabled
        self.bg_color = bg_color
        self.border_radius = border_radius
        self.is_hovered = False
        self.is_pressed = False
        self._fonts = {
            font_size: pygame.font.SysFont("Arial", font_size, bold=True),
            font_size - 2: pygame.font.SysFont("Arial", max(10, font_size - 2), bold=True),
            font_size - 4: pygame.font.SysFont("Arial", max(9, font_size - 4), bold=True),
        }

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                if self.rect.collidepoint(event.pos) and self.callback:
                    self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface):
        if not self.is_enabled:
            bg = (40, 45, 50)
            txt_col = COLOR_TEXT_DIM
            border_col = (60, 65, 70)
        elif self.is_pressed:
            bg = COLOR_BUTTON_ACTIVE
            txt_col = COLOR_TEXT
            border_col = (0, 180, 216)
        elif self.is_hovered:
            bg = COLOR_BUTTON_HOVER
            txt_col = (255, 255, 255)
            border_col = (0, 200, 240)
        else:
            bg = self.bg_color
            txt_col = COLOR_TEXT
            border_col = COLOR_BUTTON_BORDER

        pygame.draw.rect(surface, bg, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, border_col, self.rect, width=1, border_radius=self.border_radius)

        # Pick font that fits inside button without overflow
        target_font = self._fonts.get(self.font_size)
        text_surf = target_font.render(self.text, True, txt_col)
        if text_surf.get_width() > self.rect.width - 12:
            target_font = self._fonts.get(self.font_size - 2, target_font)
            text_surf = target_font.render(self.text, True, txt_col)
        if text_surf.get_width() > self.rect.width - 12:
            target_font = self._fonts.get(self.font_size - 4, target_font)
            text_surf = target_font.render(self.text, True, txt_col)

        tx = self.rect.x + (self.rect.width - text_surf.get_width()) // 2
        ty = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (tx, ty))


class ModalDialog:
    def __init__(
        self,
        title: str,
        message: str,
        buttons: List[Tuple[str, Callable[[], None], Tuple[int, int, int]]],
        width: int = 580,
        height: int = 280,
        layout: str = "auto"
    ):
        self.title = title
        self.raw_message = message
        self.title_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.body_font = pygame.font.SysFont("Arial", 15)

        # Auto-wrap message text to fit within dialog width
        max_msg_w = width - 60
        self.formatted_lines = []
        for raw_line in message.split("\n"):
            if not raw_line.strip():
                self.formatted_lines.append("")
                continue
            words = raw_line.split(" ")
            curr_line = ""
            for word in words:
                test_line = f"{curr_line} {word}".strip()
                if self.body_font.render(test_line, True, (0, 0, 0)).get_width() <= max_msg_w:
                    curr_line = test_line
                else:
                    if curr_line:
                        self.formatted_lines.append(curr_line)
                    curr_line = word
            if curr_line:
                self.formatted_lines.append(curr_line)

        # Decide layout: "list" (vertical stacked) or "row" (horizontal)
        if layout == "auto":
            is_list = len(buttons) > 2 or any(len(b[0]) > 14 for b in buttons)
        else:
            is_list = (layout == "list")

        # Dynamically adjust height to guarantee zero overlap
        header_h = 65
        line_spacing = 22
        body_h = len(self.formatted_lines) * line_spacing + 20
        
        btn_h = 42
        if is_list:
            buttons_h = len(buttons) * (btn_h + 10) + 10
        else:
            buttons_h = btn_h + 20

        min_needed_h = header_h + body_h + buttons_h + 20
        self.height = max(height, min_needed_h)
        self.width = max(width, 540 if is_list else 480)

        # Center in screen (1600x870)
        self.x = (1600 - self.width) // 2
        self.y = (870 - self.height) // 2
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.is_open = True

        # Position buttons
        self.ui_buttons: List[UIButton] = []
        if is_list:
            # Vertical stacked buttons
            btn_w = self.width - 60
            curr_by = self.y + header_h + body_h
            for text, cb, color in buttons:
                b = UIButton(
                    pygame.Rect(self.x + 30, curr_by, btn_w, btn_h),
                    text,
                    callback=cb,
                    font_size=15,
                    bg_color=color
                )
                self.ui_buttons.append(b)
                curr_by += btn_h + 10
        else:
            # Horizontal row
            num_btns = len(buttons)
            btn_w = min(180, (self.width - 60 - (num_btns - 1) * 16) // max(1, num_btns))
            gap = 16
            total_w = num_btns * btn_w + (num_btns - 1) * gap
            start_bx = self.x + (self.width - total_w) // 2
            by = self.y + self.height - btn_h - 22

            for i, (text, cb, color) in enumerate(buttons):
                bx = start_bx + i * (btn_w + gap)
                b = UIButton(
                    pygame.Rect(bx, by, btn_w, btn_h),
                    text,
                    callback=cb,
                    font_size=15,
                    bg_color=color
                )
                self.ui_buttons.append(b)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        for b in self.ui_buttons:
            if b.handle_event(event):
                return True

        # Block background clicks
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return True
        return False

    def draw(self, surface: pygame.Surface):
        if not self.is_open:
            return

        # Dimmer overlay
        overlay = pygame.Surface((1600, 870), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        surface.blit(overlay, (0, 0))

        # Modal window background with shadow
        shadow_rect = pygame.Rect(self.x + 6, self.y + 6, self.width, self.height)
        pygame.draw.rect(surface, (10, 15, 20), shadow_rect, border_radius=8)

        pygame.draw.rect(surface, (40, 48, 56), self.rect, border_radius=8)
        pygame.draw.rect(surface, (70, 85, 100), self.rect, width=2, border_radius=8)

        # Title bar
        title_surf = self.title_font.render(self.title, True, (245, 245, 250))
        surface.blit(title_surf, (self.x + 25, self.y + 20))

        pygame.draw.line(
            surface, (60, 75, 90),
            (self.x + 20, self.y + 54),
            (self.x + self.width - 20, self.y + 54), 1
        )

        # Message lines
        my = self.y + 70
        for line in self.formatted_lines:
            if line:
                line_surf = self.body_font.render(line, True, (215, 225, 235))
                surface.blit(line_surf, (self.x + 30, my))
            my += 22

        # Buttons
        for b in self.ui_buttons:
            b.draw(surface)
