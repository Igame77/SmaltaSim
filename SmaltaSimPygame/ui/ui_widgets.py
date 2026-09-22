import pygame
from typing import Callable, Optional, Tuple, List
from config import (
    COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_BUTTON_ACTIVE,
    COLOR_BUTTON_BORDER, COLOR_TEXT, COLOR_TEXT_DIM
)

class UIButton:
    _font = None

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
        self._font = pygame.font.SysFont("Arial", font_size, bold=True)

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

        text_surf = self._font.render(self.text, True, txt_col)
        tx = self.rect.x + (self.rect.width - text_surf.get_width()) // 2
        ty = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (tx, ty))


class ModalDialog:
    def __init__(
        self,
        title: str,
        message: str,
        buttons: List[Tuple[str, Callable[[], None], Tuple[int, int, int]]],
        width: int = 560,
        height: int = 280
    ):
        self.title = title
        self.message = message
        self.width = width
        self.height = height
        self.is_open = True
        
        # Center in screen (1600x870)
        self.x = (1600 - width) // 2
        self.y = (870 - height) // 2
        self.rect = pygame.Rect(self.x, self.y, width, height)

        self.title_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.body_font = pygame.font.SysFont("Arial", 16)

        # Create buttons
        self.ui_buttons: List[UIButton] = []
        btn_w = 140
        btn_h = 42
        num_btns = len(buttons)
        gap = 20
        total_w = num_btns * btn_w + (num_btns - 1) * gap
        start_bx = self.x + (width - total_w) // 2
        by = self.y + height - btn_h - 25

        for i, (text, cb, color) in enumerate(buttons):
            bx = start_bx + i * (btn_w + gap)
            b = UIButton(pygame.Rect(bx, by, btn_w, btn_h), text, callback=cb, font_size=15, bg_color=color)
            self.ui_buttons.append(b)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        for b in self.ui_buttons:
            if b.handle_event(event):
                return True

        # Block all clicks beneath modal
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return True
        return False

    def draw(self, surface: pygame.Surface):
        if not self.is_open:
            return

        # Dimmer overlay
        overlay = pygame.Surface((1600, 870), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Modal window background with shadow
        shadow_rect = pygame.Rect(self.x + 6, self.y + 6, self.width, self.height)
        pygame.draw.rect(surface, (10, 15, 20), shadow_rect, border_radius=8)

        pygame.draw.rect(surface, (40, 48, 56), self.rect, border_radius=8)
        pygame.draw.rect(surface, (70, 85, 100), self.rect, width=2, border_radius=8)

        # Title bar
        title_surf = self.title_font.render(self.title, True, (245, 245, 250))
        surface.blit(title_surf, (self.x + 25, self.y + 25))

        pygame.draw.line(
            surface, (60, 75, 90),
            (self.x + 20, self.y + 60),
            (self.x + self.width - 20, self.y + 60), 1
        )

        # Message lines
        lines = self.message.split("\n")
        my = self.y + 80
        for line in lines:
            line_surf = self.body_font.render(line, True, (215, 225, 235))
            surface.blit(line_surf, (self.x + 25, my))
            my += 24

        # Buttons
        for b in self.ui_buttons:
            b.draw(surface)
