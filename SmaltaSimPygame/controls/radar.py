import pygame
import math
from typing import Any
from core.element_base import ElementBase

class RadarTarget(ElementBase):
    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 25
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=20,
            height=20
        )

    def draw(self, surface: pygame.Surface):
        if self.value <= 0:
            return
        # Opacity 0..255 from value 0..100
        alpha = min(255, int((self.value / 100.0) * 255))
        target_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        # Polygon points from XAML: 0, 20, 20, 20, 10, 0
        points = [(0, 20), (20, 20), (10, 0)]
        pygame.draw.polygon(target_surf, (50, 240, 50, alpha), points)
        pygame.draw.polygon(target_surf, (180, 255, 180, alpha), points, width=1)
        surface.blit(target_surf, (self.pos_left, self.pos_top))


class RadarNoise(ElementBase):
    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        startup_rotation: int = -60
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=300,
            height=300
        )
        self.startup_rotation = startup_rotation

    def draw(self, surface: pygame.Surface):
        if self.value <= 0:
            return

        alpha = min(230, int((self.value / 100.0) * 230))
        noise_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        center_x = self.width // 2
        center_y = self.height // 2
        radius = 140

        # Draw sector arc of noise
        start_angle = math.radians(self.startup_rotation - 25)
        end_angle = math.radians(self.startup_rotation + 35)

        points = [(center_x, center_y)]
        num_steps = 25
        for i in range(num_steps + 1):
            theta = start_angle + (end_angle - start_angle) * (i / num_steps)
            px = center_x + radius * math.cos(theta)
            py = center_y + radius * math.sin(theta)
            points.append((px, py))

        pygame.draw.polygon(noise_surf, (60, 220, 70, alpha), points)
        # Noise texture lines
        for r in range(30, radius, 20):
            pygame.draw.arc(
                noise_surf,
                (120, 255, 130, min(255, alpha + 25)),
                (center_x - r, center_y - r, r * 2, r * 2),
                -end_angle,
                -start_angle,
                width=2
            )

        surface.blit(noise_surf, (self.pos_left, self.pos_top))
