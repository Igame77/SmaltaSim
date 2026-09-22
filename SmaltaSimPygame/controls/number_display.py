import pygame
from typing import Optional, Any
from core.element_base import ElementBase

class NumberDisplay(ElementBase):
    _font: Optional[pygame.font.Font] = None

    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        width: int = 140,
        height: int = 50
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=width,
            height=height
        )
        self._init_font()

    @classmethod
    def _init_font(cls):
        if cls._font is None:
            # Clean large digital font
            cls._font = pygame.font.SysFont("Consolas", 32, bold=True)

    def draw(self, surface: pygame.Surface):
        # White capsule/rounded box
        rect = pygame.Rect(self.pos_left, self.pos_top, self.width, self.height)
        pygame.draw.rect(surface, (245, 248, 250), rect, border_radius=15)
        pygame.draw.rect(surface, (130, 140, 150), rect, width=2, border_radius=15)

        # Draw number text
        text_str = str(self.value)
        text_surf = self._font.render(text_str, True, (25, 30, 35))
        text_x = self.pos_left + (self.width - text_surf.get_width()) // 2
        text_y = self.pos_top + (self.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (text_x, text_y))
