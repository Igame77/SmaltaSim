import pygame
import math
from typing import Optional
from devices.device_base import DeviceBase
from core.algorithm_service import ActionName
from config import COLOR_ACCENT, COLOR_WARNING

class HintRenderer:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 15, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 13)

    def draw(self, surface: pygame.Surface, device: DeviceBase):
        if not device.hint_service or not device.hint_service.algorithm:
            return

        action = device.hint_service.get_current_action()
        if not action or device.hint_service.is_training_complete:
            return

        target_el = device.get_element_by_name(action.parent_element_name)
        if not target_el:
            return

        ticks = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(ticks * 0.006)

        # 1. Target element is on CURRENT page
        if target_el.page_key == device.current_page_key:
            # Pulsing target highlight box
            glow_alpha = int(120 + 135 * pulse)
            glow_surf = pygame.Surface((target_el.width + 12, target_el.height + 12), pygame.SRCALPHA)
            pygame.draw.rect(
                glow_surf,
                (0, 210, 255, glow_alpha),
                (0, 0, target_el.width + 12, target_el.height + 12),
                width=3,
                border_radius=6
            )
            surface.blit(glow_surf, (target_el.pos_left - 6, target_el.pos_top - 6))

            # Speech bubble / hint box
            hint_text = action.hint_text
            lines = hint_text.split("\n")
            if action.name == ActionName.INFO:
                lines.append("(Кликните по элементу или нажмите Пробел для продолжения)")

            rendered_lines = [self.font.render(l, True, (255, 255, 255)) for l in lines]
            max_w = max(r.get_width() for r in rendered_lines) + 24
            box_h = len(rendered_lines) * 22 + 16

            # Position popup next to element
            bx = target_el.pos_left + target_el.width + 16
            if bx + max_w > 1580:
                bx = target_el.pos_left - max_w - 16
            if bx < 10:
                bx = 10

            by = target_el.pos_top - 10
            if by + box_h > 790:
                by = 790 - box_h
            if by < 10:
                by = 10

            bubble_rect = pygame.Rect(bx, by, max_w, box_h)
            pygame.draw.rect(surface, (15, 25, 35), bubble_rect, border_radius=6)
            pygame.draw.rect(surface, (0, 180, 220), bubble_rect, width=2, border_radius=6)

            # Draw pointer arrow to element
            if bx > target_el.pos_left:
                p1 = (bx, by + 18)
                p2 = (bx - 8, target_el.pos_top + target_el.height // 2)
                p3 = (bx, by + 28)
                pygame.draw.polygon(surface, (0, 180, 220), [p1, p2, p3])

            for i, r in enumerate(rendered_lines):
                surface.blit(r, (bx + 12, by + 10 + i * 22))

        # 2. Target element is on a DIFFERENT page
        else:
            # Need navigation hint on bottom bar
            curr_idx = device.pages.index(device.current_page_key)
            target_idx = device.pages.index(target_el.page_key)
            is_forward = target_idx > curr_idx

            target_page_name = target_el.page_key.value if hasattr(target_el.page_key, 'value') else str(target_el.page_key)
            nav_hint = f"Нужный прибор на странице: {target_page_name} ->" if is_forward else f"<- Нужный прибор на странице: {target_page_name}"

            # Draw banner above navbar
            banner_w = 480
            banner_h = 36
            banner_x = (1600 - banner_w) // 2
            banner_y = 755

            banner_rect = pygame.Rect(banner_x, banner_y, banner_w, banner_h)
            pygame.draw.rect(surface, (20, 30, 40), banner_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_WARNING, banner_rect, width=2, border_radius=6)

            txt = self.font.render(nav_hint, True, (255, 230, 120))
            tx = banner_x + (banner_w - txt.get_width()) // 2
            ty = banner_y + (banner_h - txt.get_height()) // 2
            surface.blit(txt, (tx, ty))
