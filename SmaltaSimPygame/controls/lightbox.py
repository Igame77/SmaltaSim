import pygame
from typing import Any, Tuple, Optional
from core.element_base import ElementBase

class Lightbox(ElementBase):
    _font: Optional[pygame.font.Font] = None

    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        text: str = "",
        bg_color: Tuple[int, int, int] = (60, 200, 70),
        value: int = 0
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=75,
            height=25
        )
        self.text = text
        self.bg_color = bg_color
        self._init_font()

    @classmethod
    def _init_font(cls):
        if cls._font is None:
            # Clean legible sans-serif font for small tactical placards
            cls._font = pygame.font.SysFont("Arial", 9, bold=True)

    def on_value_changed(self):
        super().on_value_changed()
        if self.device and self.device.hint_service:
            self.device.hint_service.on_idle_completed(self.name, self.value)

    def draw(self, surface: pygame.Surface):
        # Create a surface with per-pixel alpha
        box_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # 0.3 opacity vs 1.0 opacity
        alpha = 255 if self.value == 1 else 75
        
        # Base background
        r, g, b = self.bg_color
        bg_with_alpha = (r, g, b, alpha)
        pygame.draw.rect(box_surf, bg_with_alpha, (0, 0, self.width, self.height), border_radius=3)
        
        # Border
        if self.value == 1:
            # Glowing bright border
            border_color = (min(255, r + 50), min(255, g + 50), min(255, b + 50), 255)
            pygame.draw.rect(box_surf, border_color, (0, 0, self.width, self.height), width=1, border_radius=3)
        else:
            border_color = (40, 50, 45, 120)
            pygame.draw.rect(box_surf, border_color, (0, 0, self.width, self.height), width=1, border_radius=3)

        # Draw centered multiline text
        lines = self.text.split("\n")
        total_text_h = len(lines) * 11
        start_y = (self.height - total_text_h) // 2

        text_color = (10, 20, 10) if self.value == 1 else (170, 185, 175)
        for i, line in enumerate(lines):
            line_surf = self._font.render(line, True, text_color)
            line_x = (self.width - line_surf.get_width()) // 2
            line_y = start_y + i * 11
            box_surf.blit(line_surf, (line_x, line_y))

        surface.blit(box_surf, (self.pos_left, self.pos_top))
