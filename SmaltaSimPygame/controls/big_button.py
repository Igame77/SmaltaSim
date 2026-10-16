import pygame
from typing import Optional, List, Any
from core.element_base import ElementBase
from core.dependency_action import DependencyAction
from config import Assets

class BigButton(ElementBase):
    _img_on: Optional[pygame.Surface] = None
    _img_off: Optional[pygame.Surface] = None

    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        dependency_actions: Optional[List[DependencyAction]] = None,
        dependency_secure_element_name: Optional[str] = None
    ):
        # 175x175 scaled at 96/300 DPI ~ 56x56
        super().__init__(
            name=name,
            pos_top=pos_top,
            pos_left=pos_left,
            page_key=page_key,
            value=value,
            width=56,
            height=56,
            dependency_actions=dependency_actions
        )
        self.dependency_secure_element_name = dependency_secure_element_name
        self.is_dependency_actions_running = False
        self._is_pressed = False
        self._press_release_time = 0
        self._load_images()

    @classmethod
    def _load_images(cls):
        if cls._img_on is None:
            raw_on = pygame.image.load(str(Assets.BIG_BUTTON_ON))
            if pygame.display.get_surface() is not None:
                raw_on = raw_on.convert_alpha()
            cls._img_on = pygame.transform.smoothscale(raw_on, (56, 56))
            raw_off = pygame.image.load(str(Assets.BIG_BUTTON_OFF))
            if pygame.display.get_surface() is not None:
                raw_off = raw_off.convert_alpha()
            cls._img_off = pygame.transform.smoothscale(raw_off, (56, 56))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_enabled:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._is_pressed = True
                self._press_release_time = pygame.time.get_ticks() + 160
                self.interact()
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._is_pressed:
                if pygame.time.get_ticks() >= self._press_release_time:
                    self._is_pressed = False
                    self.set_value(0, trigger_dependencies=False)
                return True
        return False

    def update(self, dt_ms: int):
        if self._is_pressed and pygame.time.get_ticks() >= self._press_release_time:
            if not pygame.mouse.get_pressed()[0]:
                self._is_pressed = False
                self.set_value(0, trigger_dependencies=False)

    def interact(self):
        # Check secure element lock
        if self.dependency_secure_element_name and self.device:
            sec_el = self.device.get_element_by_name(self.dependency_secure_element_name)
            if sec_el and getattr(sec_el, 'is_dependency_actions_running', False):
                return

        self.set_value(1)
        if self.device and self.device.history_service:
            self.device.history_service.record_click(self.name)
        if self.device and self.device.hint_service:
            self.device.hint_service.on_element_interacted(self.name, 1)

    def notify_dependencies(self):
        if not self.device:
            return
        self.is_dependency_actions_running = True
        completed_count = 0
        total_actions = len(self.dependency_actions)

        def on_action_done(target_name: str):
            nonlocal completed_count
            completed_count += 1
            if self.device and self.device.history_service:
                self.device.history_service.record_idle(target_name)
            if completed_count >= total_actions:
                self.is_dependency_actions_running = False

        for dep in self.dependency_actions:
            dep.execute(self.value, self.device.get_element_by_name, callback=on_action_done)

    def draw(self, surface: pygame.Surface):
        # Кнопка упругая — визуально возвращается в исходное ненажатое положение
        surf = self._img_on if self._is_pressed else self._img_off
        surface.blit(surf, (self.pos_left, self.pos_top))
