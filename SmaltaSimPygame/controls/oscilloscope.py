import pygame
from typing import Any
from core.element_base import ElementBase

class Oscilloscope(ElementBase):
    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        width: int = 380,
        height: int = 300
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=0,
            width=width,
            height=height
        )
        self.raw_values = [4, 4, 4, 4, 5, 3, 6, 2, 7, 1, 8, 0, 7, 2, 6, 3, 5, 4, 4, 4, 4]

    def draw(self, surface: pygame.Surface):
        # Dedicated CRT phosphor screen surface
        screen_surf = pygame.Surface((self.width, self.height))
        screen_surf.fill((12, 28, 18))  # Dark green CRT background

        # Grid lines
        grid_color = (25, 55, 35)
        num_cols = 10
        num_rows = 8
        col_w = self.width / num_cols
        row_h = self.height / num_rows

        for c in range(1, num_cols):
            x = int(c * col_w)
            pygame.draw.line(screen_surf, grid_color, (x, 0), (x, self.height), 1)

        for r in range(1, num_rows):
            y = int(r * row_h)
            pygame.draw.line(screen_surf, grid_color, (0, y), (self.width, y), 1)

        # Center reticle axes
        center_x = self.width // 2
        center_y = self.height // 2
        reticle_color = (35, 75, 45)
        pygame.draw.line(screen_surf, reticle_color, (center_x, 0), (center_x, self.height), 2)
        pygame.draw.line(screen_surf, reticle_color, (0, center_y), (self.width, center_y), 2)

        # Check scan mode from neighboring controls if available
        scan_x_active = False
        if self.device:
            sw_x = self.device.get_element_by_name("c165_thumbler_scanmode_X")
            if sw_x and sw_x.value == 1:
                scan_x_active = True

        beam_color = (100, 255, 100)
        glow_color = (30, 160, 50)

        if scan_x_active:
            # Sweep off: vertical line in center
            y1 = int(self.height * 0.2)
            y2 = int(self.height * 0.8)
            pygame.draw.line(screen_surf, glow_color, (center_x, y1), (center_x, y2), 5)
            pygame.draw.line(screen_surf, beam_color, (center_x, y1), (center_x, y2), 2)
        else:
            # Signal waveform
            num_points = len(self.raw_values)
            step_x = self.width / (num_points - 1)
            points = []
            for i, val in enumerate(self.raw_values):
                px = int(i * step_x)
                # Map value 0..8 to screen Y (inverted)
                py = int(self.height - (val / 8.0) * (self.height - 30) - 15)
                points.append((px, py))

            if len(points) > 1:
                # Glow effect
                pygame.draw.lines(screen_surf, glow_color, False, points, width=5)
                # Core bright line
                pygame.draw.lines(screen_surf, beam_color, False, points, width=2)

        # Bezel border
        pygame.draw.rect(screen_surf, (50, 70, 60), (0, 0, self.width, self.height), width=3, border_radius=4)

        surface.blit(screen_surf, (self.pos_left, self.pos_top))
