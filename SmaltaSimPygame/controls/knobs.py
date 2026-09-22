import pygame
from typing import Optional, List, Any
from core.element_base import ElementBase
from core.dependency_action import DependencyAction
from config import Assets

class RotateStepWheel(ElementBase):
    _img_base: Optional[pygame.Surface] = None

    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        startup_rotation: int = 0,
        rotation_step_degrees: int = 30,
        max_value: int = 5,
        width: int = 80,
        height: int = 55,
        dependency_actions: Optional[List[DependencyAction]] = None
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=width,
            height=height,
            dependency_actions=dependency_actions
        )
        self.startup_rotation = startup_rotation
        self.rotation_step_degrees = rotation_step_degrees
        self.max_value = max_value
        self._load_images()

    @classmethod
    def _load_images(cls):
        if cls._img_base is None:
            raw = pygame.image.load(str(Assets.STEP_WHEEL))
            if pygame.display.get_surface() is not None:
                raw = raw.convert_alpha()
            cls._img_base = pygame.transform.smoothscale(raw, (80, 55))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_enabled:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if event.button == 1:  # Left click: next step
                    new_val = (self.value + 1) % self.max_value
                    self.set_value(new_val)
                    self._record_interact()
                    return True
                elif event.button == 3:  # Right click: prev step
                    new_val = (self.value - 1) % self.max_value
                    self.set_value(new_val)
                    self._record_interact()
                    return True
        return False

    def _record_interact(self):
        if self.device and self.device.history_service:
            self.device.history_service.record_click(self.name)
        if self.device and self.device.hint_service:
            self.device.hint_service.on_element_interacted(self.name, self.value)

    def draw(self, surface: pygame.Surface):
        angle = (self.value * self.rotation_step_degrees) + self.startup_rotation
        # Rotate image around center
        rotated_surf = pygame.transform.rotate(self._img_base, -angle)
        orig_center = (self.pos_left + self.width // 2, self.pos_top + self.height // 2)
        new_rect = rotated_surf.get_rect(center=orig_center)
        surface.blit(rotated_surf, new_rect.topleft)


class PotWheel(ElementBase):
    _images_cache = {}

    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        min_value: int = 0,
        max_value: int = 50,
        rotation_coefficient: int = 20,
        width: int = 65,
        height: int = 65,
        image_type: str = "Flat",
        dependency_actions: Optional[List[DependencyAction]] = None
    ):
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=width,
            height=height,
            dependency_actions=dependency_actions
        )
        self.min_value = min_value
        self.max_value = max_value
        self.rotation_coefficient = rotation_coefficient
        self.image_type = image_type
        self.base_surf = self._get_image(image_type, width, height)

    @classmethod
    def _get_image(cls, image_type: str, w: int, h: int) -> pygame.Surface:
        key = (image_type, w, h)
        if key not in cls._images_cache:
            if image_type == "Flat":
                path = Assets.WHEEL_FLAT
            elif image_type == "Point":
                path = Assets.WHEEL_POINT
            else:
                path = Assets.WHEEL
            raw = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                raw = raw.convert_alpha()
            cls._images_cache[key] = pygame.transform.smoothscale(raw, (w, h))
        return cls._images_cache[key]

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_enabled:
            return False

        # Mouse wheel scroll over knob
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.rect.collidepoint(mouse_pos):
                delta = event.y
                new_val = max(self.min_value, min(self.max_value, self.value + delta))
                if new_val != self.value:
                    self.set_value(new_val)
                    self._record_interact()
                    return True

        # Click also supported: left-click adds 1 (or 5), right-click subtracts
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                step = 5 if (self.max_value - self.min_value > 20) else 1
                if event.button == 1:
                    new_val = min(self.max_value, self.value + step)
                elif event.button == 3:
                    new_val = max(self.min_value, self.value - step)
                else:
                    return False

                if new_val != self.value:
                    self.set_value(new_val)
                    self._record_interact()
                    return True
        return False

    def _record_interact(self):
        if self.device and self.device.history_service:
            self.device.history_service.record_click(self.name)
        if self.device and self.device.hint_service:
            self.device.hint_service.on_element_interacted(self.name, self.value)

    def draw(self, surface: pygame.Surface):
        angle = self.value * self.rotation_coefficient
        rotated_surf = pygame.transform.rotate(self.base_surf, -angle)
        orig_center = (self.pos_left + self.width // 2, self.pos_top + self.height // 2)
        new_rect = rotated_surf.get_rect(center=orig_center)
        surface.blit(rotated_surf, new_rect.topleft)
