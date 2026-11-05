import pygame
import math
from typing import Any
from core.element_base import ElementBase

class GaugeArrow(ElementBase):
    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        startup_rotation: int = 35
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=80,
            height=80
        )
        self.startup_rotation = startup_rotation
        self.coefficient = 11
        self.min_value = 0
        self.max_value = 10
        
        self.target_rotation = (self.coefficient * self.value) + self.startup_rotation
        self.current_rotation = float(self.target_rotation)

    def on_value_changed(self):
        super().on_value_changed()
        clamped_val = max(self.min_value, min(self.max_value, self.value))
        self.target_rotation = (self.coefficient * clamped_val) + self.startup_rotation

    def update(self, dt_ms: int):
        diff = self.target_rotation - self.current_rotation
        if abs(diff) > 0.1:
            # Smooth step towards target angle
            step = diff * 0.15
            if abs(step) < 0.2:
                step = 0.2 if diff > 0 else -0.2
            self.current_rotation += step
        else:
            self.current_rotation = float(self.target_rotation)

    def draw(self, surface: pygame.Surface):
        # Needles are already part of the supplied instrument artwork. Keep this
        # element and its values for algorithm dependencies, but hide the extra
        # black software needle that was being drawn over the photographed one.
        return

