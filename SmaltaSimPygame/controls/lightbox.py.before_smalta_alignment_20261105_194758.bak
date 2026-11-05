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
        lines = [line.strip() for line in self.text.split("\n") if line.strip()]
        if not lines:
            surface.blit(box_surf, (self.pos_left, self.pos_top))
            return

        # Choose best font size to avoid any overflow
        font_sz = 8 if len(lines) > 1 else 9
        font = self._fonts.get(font_sz) or pygame.font.SysFont("Arial", font_sz, bold=True)
        
        # Verify text fits width, scale down to 7 if any line exceeds 68px
        max_w = max(font.render(l, True, (0, 0, 0)).get_width() for l in lines)
        if max_w > self.width - 6:
            font = self._fonts.get(7) or pygame.font.SysFont("Arial", 7, bold=True)

        text_color = (10, 25, 10) if self.value == 1 else (170, 185, 175)
        rendered_surfs = [font.render(l, True, text_color) for l in lines]
        
        total_text_h = sum(s.get_height() for s in rendered_surfs) + (len(rendered_surfs) - 1) * 1
        curr_y = max(1, (self.height - total_text_h) // 2)
        
        for s in rendered_surfs:
            line_x = (self.width - s.get_width()) // 2
            box_surf.blit(s, (line_x, curr_y))
            curr_y += s.get_height() + 1

        surface.blit(box_surf, (self.pos_left, self.pos_top))
