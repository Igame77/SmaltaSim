import pygame
from typing import List, Dict, Optional, Any
from core.element_base import ElementBase
from core.algorithm_service import Algorithm, HistoryService, HintService
from config import CANVAS_WIDTH, CANVAS_HEIGHT

class DeviceBase:
    def __init__(self, name: str, readable_name: str, pages: List[Any], first_page_key: Any):
        self.name = name
        self.readable_name = readable_name
        self.pages = pages
        self.current_page_key = first_page_key
        
        self.elements: List[ElementBase] = []
        self.elements_by_name: Dict[str, ElementBase] = {}
        self.page_backgrounds: Dict[Any, pygame.Surface] = {}
        
        self.history_service = HistoryService()
        self.hint_service = HintService()
        self.current_algorithm: Optional[Algorithm] = None

    def add_element(self, element: ElementBase):
        element.device = self
        self.elements.append(element)
        self.elements_by_name[element.name] = element

    def get_element_by_name(self, name: str) -> Optional[ElementBase]:
        return self.elements_by_name.get(name)

    def get_elements_for_page(self, page_key: Any) -> List[ElementBase]:
        return [el for el in self.elements if el.page_key == page_key]

    def set_background(self, page_key: Any, image_path: str):
        raw = pygame.image.load(str(image_path))
        if pygame.display.get_surface() is not None:
            raw = raw.convert()
        
        # Proportional uniform scaling (WPF Stretch="Uniform") to fit CANVAS_WIDTH x CANVAS_HEIGHT
        orig_w, orig_h = raw.get_size()
        scale = min(CANVAS_WIDTH / orig_w, CANVAS_HEIGHT / orig_h)
        scaled_w = int(round(orig_w * scale))
        scaled_h = int(round(orig_h * scale))
        scaled_img = pygame.transform.smoothscale(raw, (scaled_w, scaled_h))

        # Center on 1600x800 canvas with dark station chassis background
        canvas_bg = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
        canvas_bg.fill((20, 24, 28))
        offset_x = (CANVAS_WIDTH - scaled_w) // 2
        offset_y = (CANVAS_HEIGHT - scaled_h) // 2
        canvas_bg.blit(scaled_img, (offset_x, offset_y))
        
        self.page_backgrounds[page_key] = canvas_bg

    def can_go_forward(self) -> bool:
        idx = self.pages.index(self.current_page_key)
        return idx < len(self.pages) - 1

    def can_go_previous(self) -> bool:
        idx = self.pages.index(self.current_page_key)
        return idx > 0

    def get_next_page_key(self) -> Optional[Any]:
        if self.can_go_forward():
            idx = self.pages.index(self.current_page_key)
            return self.pages[idx + 1]
        return None

    def get_previous_page_key(self) -> Optional[Any]:
        if self.can_go_previous():
            idx = self.pages.index(self.current_page_key)
            return self.pages[idx - 1]
        return None

    def go_forward(self):
        nxt = self.get_next_page_key()
        if nxt:
            self.current_page_key = nxt

    def go_previous(self):
        prv = self.get_previous_page_key()
        if prv:
            self.current_page_key = prv

    def apply_algorithm(self, algorithm: Algorithm):
        self.current_algorithm = algorithm
        self.history_service.reset()
        self.hint_service.reset()

        # Cancel any running delayed dependencies
        for el in self.elements:
            el.cancel_dependencies()

        # Set initial values
        for el in self.elements:
            el._is_initializing = True
            val = algorithm.start_state_of_elements.get(el.name, 0)
            el.set_value(val, trigger_dependencies=False)
            el._is_initializing = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Pass event to active page elements in reverse order (top z-order first)
        active_elements = self.get_elements_for_page(self.current_page_key)
        for el in reversed(active_elements):
            if el.handle_event(event):
                return True
        return False

    def update(self, dt_ms: int):
        active_elements = self.get_elements_for_page(self.current_page_key)
        for el in active_elements:
            el.update(dt_ms)

    def draw(self, surface: pygame.Surface):
        # Draw background
        bg = self.page_backgrounds.get(self.current_page_key)
        if bg:
            surface.blit(bg, (0, 0))
        else:
            surface.fill((40, 45, 50))

        # Draw elements
        active_elements = self.get_elements_for_page(self.current_page_key)
        for el in active_elements:
            el.draw(surface)
