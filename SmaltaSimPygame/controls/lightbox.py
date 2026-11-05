import pygame
from typing import Any, Tuple, Optional, Dict
from core.element_base import ElementBase

class Lightbox(ElementBase):
    _fonts: Dict[int, pygame.font.Font] = {}

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
        self._init_fonts()

    @classmethod
    def _init_fonts(cls):
        if not cls._fonts:
            for sz in [8, 9, 10]:
                cls._fonts[sz] = pygame.font.SysFont("Arial", sz, bold=True)

    def on_value_changed(self):
        super().on_value_changed()
        if self.device and self.device.hint_service:
            self.device.hint_service.on_idle_completed(self.name, self.value)

    def draw(self, surface: pygame.Surface):
        # The LO01-P image already contains the printed status-label text. In
        # native-art mode only tint the physical plaque; don't print the same
        # label a second time on top of itself.
        if self.device and getattr(self.device, "use_native_coordinates", False):
            box_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
            r, g, b = self.bg_color
            alpha = 115 if self.value == 1 else 22
            pygame.draw.rect(box_surf, (r, g, b, alpha), (0, 0, self.width, self.height), border_radius=3)
            if self.value == 1:
                border = (min(255, r + 45), min(255, g + 45), min(255, b + 45), 210)
                pygame.draw.rect(box_surf, border, (0, 0, self.width, self.height), width=2, border_radius=3)
            surface.blit(box_surf, (self.pos_left, self.pos_top))
            return

        # Legacy devices keep the original label and text rendering behavior.
        box_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        alpha = 255 if self.value == 1 else 75
        r, g, b = self.bg_color
        pygame.draw.rect(box_surf, (r, g, b, alpha), (0, 0, self.width, self.height), border_radius=3)
        if self.value == 1:
            border_color = (min(255, r + 50), min(255, g + 50), min(255, b + 50), 255)
            pygame.draw.rect(box_surf, border_color, (0, 0, self.width, self.height), width=1, border_radius=3)
        else:
            pygame.draw.rect(box_surf, (40, 50, 45, 120), (0, 0, self.width, self.height), width=1, border_radius=3)

        lines = [line.strip() for line in self.text.split("\n") if line.strip()]
        if not lines:
            surface.blit(box_surf, (self.pos_left, self.pos_top))
            return
        font_sz = 8 if len(lines) > 1 else 9
        font = self._fonts.get(font_sz) or pygame.font.SysFont("Arial", font_sz, bold=True)
        max_w = max(font.render(line, True, (0, 0, 0)).get_width() for line in lines)
        if max_w > self.width - 6:
            font = self._fonts.get(7) or pygame.font.SysFont("Arial", 7, bold=True)
        text_color = (10, 25, 10) if self.value == 1 else (170, 185, 175)
        rendered = [font.render(line, True, text_color) for line in lines]
        total_h = sum(item.get_height() for item in rendered) + (len(rendered) - 1)
        y = max(1, (self.height - total_h) // 2)
        for item in rendered:
            box_surf.blit(item, ((self.width - item.get_width()) // 2, y))
            y += item.get_height() + 1
        surface.blit(box_surf, (self.pos_left, self.pos_top))

