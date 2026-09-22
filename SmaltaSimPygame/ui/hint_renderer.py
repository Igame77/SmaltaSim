import pygame
import math
from typing import Optional, List
from devices.device_base import DeviceBase
from core.algorithm_service import ActionName
from config import COLOR_ACCENT, COLOR_WARNING

class HintRenderer:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 14, bold=True)
        self.info_font = pygame.font.SysFont("Arial", 12, italic=True)

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int = 310) -> List[str]:
        result = []
        for raw_line in text.split("\n"):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            words = raw_line.split(" ")
            curr_line = ""
            for word in words:
                test_line = f"{curr_line} {word}".strip()
                if font.render(test_line, True, (0, 0, 0)).get_width() <= max_width:
                    curr_line = test_line
                else:
                    if curr_line:
                        result.append(curr_line)
                    curr_line = word
            if curr_line:
                result.append(curr_line)
        return result

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
        pulse = 0.5 + 0.5 * math.sin(ticks * 0.007)

        # 1. Target element is on CURRENT page
        if target_el.page_key == device.current_page_key:
            # Pulsing target highlight outline
            glow_alpha = int(140 + 115 * pulse)
            glow_surf = pygame.Surface((target_el.width + 12, target_el.height + 12), pygame.SRCALPHA)
            pygame.draw.rect(
                glow_surf,
                (0, 220, 255, glow_alpha),
                (0, 0, target_el.width + 12, target_el.height + 12),
                width=3,
                border_radius=6
            )
            surface.blit(glow_surf, (target_el.pos_left - 6, target_el.pos_top - 6))

            # Speech bubble with intelligent word-wrapping
            wrapped_lines = self._wrap_text(action.hint_text, self.font, max_width=320)
            rendered_lines = [self.font.render(l, True, (255, 255, 255)) for l in wrapped_lines]

            info_line_surf = None
            if action.name == ActionName.INFO:
                info_line_surf = self.info_font.render("(Кликните по органу или нажмите Пробел)", True, (120, 220, 255))

            content_w = max(r.get_width() for r in rendered_lines) if rendered_lines else 100
            if info_line_surf:
                content_w = max(content_w, info_line_surf.get_width())

            bubble_w = max(180, content_w + 24)
            line_h = 20
            bubble_h = len(rendered_lines) * line_h + (20 if info_line_surf else 0) + 18

            # Determine best side for popup (Right vs Left vs Below vs Above)
            el_center_x = target_el.pos_left + target_el.width // 2
            el_center_y = target_el.pos_top + target_el.height // 2

            # Try Right
            if target_el.pos_left + target_el.width + 16 + bubble_w <= 1585:
                bx = target_el.pos_left + target_el.width + 16
                side = "left"  # pointer points to the left
            # Try Left
            elif target_el.pos_left - 16 - bubble_w >= 15:
                bx = target_el.pos_left - 16 - bubble_w
                side = "right"  # pointer points to the right
            else:
                bx = max(15, min(1585 - bubble_w, el_center_x - bubble_w // 2))
                side = "none"

            by = el_center_y - 25
            by = max(15, min(785 - bubble_h, by))

            # Draw shadow
            shadow_rect = pygame.Rect(bx + 4, by + 4, bubble_w, bubble_h)
            pygame.draw.rect(surface, (5, 10, 15), shadow_rect, border_radius=6)

            # Draw bubble background & border
            bubble_rect = pygame.Rect(bx, by, bubble_w, bubble_h)
            pygame.draw.rect(surface, (18, 28, 38), bubble_rect, border_radius=6)
            pygame.draw.rect(surface, (0, 195, 235), bubble_rect, width=2, border_radius=6)

            # Draw pointer arrow
            arrow_y = max(by + 14, min(by + bubble_h - 14, el_center_y))
            if side == "left":
                p1 = (bx, arrow_y - 6)
                p2 = (bx - 9, arrow_y)
                p3 = (bx, arrow_y + 6)
                pygame.draw.polygon(surface, (0, 195, 235), [p1, p2, p3])
            elif side == "right":
                p1 = (bx + bubble_w, arrow_y - 6)
                p2 = (bx + bubble_w + 9, arrow_y)
                p3 = (bx + bubble_w, arrow_y + 6)
                pygame.draw.polygon(surface, (0, 195, 235), [p1, p2, p3])

            # Render text lines
            curr_ty = by + 9
            for r in rendered_lines:
                surface.blit(r, (bx + 12, curr_ty))
                curr_ty += line_h

            if info_line_surf:
                surface.blit(info_line_surf, (bx + 12, curr_ty + 2))

        # 2. Target element is on a DIFFERENT page
        else:
            curr_idx = device.pages.index(device.current_page_key)
            target_idx = device.pages.index(target_el.page_key)
            is_forward = target_idx > curr_idx

            target_page_name = target_el.page_key.value if hasattr(target_el.page_key, 'value') else str(target_el.page_key)
            nav_hint = f"Нужный блок: {target_page_name} ->" if is_forward else f"<- Нужный блок: {target_page_name}"

            # Banner above bottom navbar
            banner_w = 460
            banner_h = 36
            banner_x = (1600 - banner_w) // 2
            banner_y = 752

            # Shadow
            pygame.draw.rect(surface, (5, 10, 15), (banner_x + 3, banner_y + 3, banner_w, banner_h), border_radius=6)

            banner_rect = pygame.Rect(banner_x, banner_y, banner_w, banner_h)
            pygame.draw.rect(surface, (25, 35, 45), banner_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_WARNING, banner_rect, width=2, border_radius=6)

            txt = self.font.render(nav_hint, True, (255, 235, 130))
            tx = banner_x + (banner_w - txt.get_width()) // 2
            ty = banner_y + (banner_h - txt.get_height()) // 2
            surface.blit(txt, (tx, ty))
