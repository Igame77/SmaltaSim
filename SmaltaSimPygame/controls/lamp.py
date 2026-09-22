import pygame
from typing import Optional, Any
from core.element_base import ElementBase
from config import Assets

class Lamp(ElementBase):
    _img_on: Optional[pygame.Surface] = None
    _img_off: Optional[pygame.Surface] = None

    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0
    ):
        # 85x85 scaled at 96/300 DPI ~ 27x27
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=27,
            height=27
        )
        self._load_images()

    @classmethod
    def _load_images(cls):
        if cls._img_on is None:
            raw_on = pygame.image.load(str(Assets.LAMP_ON))
            if pygame.display.get_surface() is not None:
                raw_on = raw_on.convert_alpha()
            cls._img_on = pygame.transform.smoothscale(raw_on, (27, 27))
            raw_off = pygame.image.load(str(Assets.LAMP_OFF))
            if pygame.display.get_surface() is not None:
                raw_off = raw_off.convert_alpha()
            cls._img_off = pygame.transform.smoothscale(raw_off, (27, 27))

    def on_value_changed(self):
        super().on_value_changed()
        if self.device and self.device.hint_service:
            self.device.hint_service.on_idle_completed(self.name, self.value)

    def draw(self, surface: pygame.Surface):
        surf = self._img_on if self.value == 1 else self._img_off
        surface.blit(surf, (self.pos_left, self.pos_top))
