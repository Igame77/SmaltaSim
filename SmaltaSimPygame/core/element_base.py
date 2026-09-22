import pygame
from typing import Optional, List, Callable, Any
from core.dependency_action import DependencyAction

class ElementBase:
    def __init__(
        self,
        name: str,
        pos_top: int,
        pos_left: int,
        page_key: Any,
        value: int = 0,
        width: int = 40,
        height: int = 40,
        dependency_actions: Optional[List[DependencyAction]] = None
    ):
        self.name = name
        self.pos_top = pos_top
        self.pos_left = pos_left
        self.page_key = page_key
        self.width = width
        self.height = height
        self.rect = pygame.Rect(pos_left, pos_top, width, height)
        
        self.value = value
        self.dependency_actions = dependency_actions or []
        
        self.is_enabled = True
        self.is_hint_open = False
        self.hint_text = ""
        
        self.device = None  # Reference to parent Device
        self._is_initializing = False

    def set_value(self, new_value: int, trigger_dependencies: bool = True):
        if self.value != new_value:
            self.value = new_value
            self.on_value_changed()
            if trigger_dependencies and not self._is_initializing:
                self.notify_dependencies()

    def on_value_changed(self):
        """Hook for subclasses to update visual state, angles, images, etc."""
        pass

    def notify_dependencies(self):
        if not self.device:
            return
        for dep in self.dependency_actions:
            dep.execute(
                self.value,
                self.device.get_element_by_name,
                callback=self._dependency_executed_callback
            )

    def _dependency_executed_callback(self, dependency_element_name: str):
        if self.device and self.device.history_service:
            self.device.history_service.record_idle(dependency_element_name)

    def cancel_dependencies(self):
        for dep in self.dependency_actions:
            dep.cancel()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process PyGame event. Returns True if handled."""
        return False

    def update(self, dt_ms: int):
        """Optional update logic (e.g. smooth arrow movement, blinking)."""
        pass

    def draw(self, surface: pygame.Surface):
        """Draw element on canvas."""
        pass
