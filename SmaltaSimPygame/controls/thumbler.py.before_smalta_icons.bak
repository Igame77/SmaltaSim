import pygame
from typing import Optional, List, Any
from core.element_base import ElementBase
from core.dependency_action import DependencyAction
from config import Assets

class Thumbler(ElementBase):
    _img_on: Optional[pygame.Surface] = None
    _img_off: Optional[pygame.Surface] = None

    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        startup_rotation: int = 0,
        dependency_actions: Optional[List[DependencyAction]] = None
    ):
        # 77x133 scaled at 96/300 DPI ~ 25x43
        base_w, base_h = 25, 43
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=base_w,
            height=base_h,
            dependency_actions=dependency_actions
        )
        self.startup_rotation = startup_rotation
        self._load_images()
        self._update_rendered_surfaces()

    @classmethod
    def _load_images(cls):
        if cls._img_on is None:
            raw_on = pygame.image.load(str(Assets.THUMBLER_ON))
            if pygame.display.get_surface() is not None:
                raw_on = raw_on.convert_alpha()
            cls._img_on = pygame.transform.smoothscale(raw_on, (25, 43))
            raw_off = pygame.image.load(str(Assets.THUMBLER_OFF))
            if pygame.display.get_surface() is not None:
                raw_off = raw_off.convert_alpha()
            cls._img_off = pygame.transform.smoothscale(raw_off, (25, 43))

    def _update_rendered_surfaces(self):
        if self.startup_rotation != 0:
            self.rendered_on = pygame.transform.rotate(self._img_on, -self.startup_rotation)
            self.rendered_off = pygame.transform.rotate(self._img_off, -self.startup_rotation)
        else:
            self.rendered_on = self._img_on
            self.rendered_off = self._img_off
        
        # Update rect size based on rotated surface
        w, h = self.rendered_on.get_size()
        self.width = w
        self.height = h
        self.rect = pygame.Rect(self.pos_left, self.pos_top, w, h)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_enabled:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                new_val = 1 if self.value == 0 else 0
                self.set_value(new_val)
                if self.device and self.device.history_service:
                    self.device.history_service.record_click(self.name)
                if self.device and self.device.hint_service:
                    self.device.hint_service.on_element_interacted(self.name, self.value)
                return True
        return False

    def draw(self, surface: pygame.Surface):
        surf = self.rendered_on if self.value == 1 else self.rendered_off
        surface.blit(surf, (self.pos_left, self.pos_top))
