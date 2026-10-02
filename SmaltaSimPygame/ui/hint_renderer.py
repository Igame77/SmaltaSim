import pygame
import math
from typing import Optional, List
from devices.device_base import DeviceBase
from core.algorithm_service import ActionName
from config import COLOR_ACCENT, COLOR_WARNING, COLOR_SUCCESS

class HintRenderer:
    def __init__(self):
        self.font = pygame.font.SysFont("Arial", 14, bold=True)
        self.info_font = pygame.font.SysFont("Arial", 12, italic=True)
        self.hud_step_font = pygame.font.SysFont("Arial", 13, bold=True)
        self.hud_badge_font = pygame.font.SysFont("Arial", 12, bold=True)
        self.hud_text_font = pygame.font.SysFont("Arial", 14, bold=True)
        self.hud_alert_font = pygame.font.SysFont("Arial", 13, bold=True)
        self.hud_btn_font = pygame.font.SysFont("Arial", 13, bold=True)
        
        self.help_button_rect = pygame.Rect(0, 0, 0, 0)
        self.is_help_hovered = False

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

    def handle_event(self, event: pygame.event.Event, device: DeviceBase) -> bool:
        if not device or not device.hint_service or not device.hint_service.algorithm:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_help_hovered = self.help_button_rect.collidepoint(event.pos)
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.help_button_rect.collidepoint(event.pos):
                device.hint_service.escalate_hint()
                return True

        return False

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
        hint_level = device.hint_service.hint_level

        # --- 1. TOP HUD BANNER (Adaptive mission & hint status) ---
        self._draw_hud_banner(surface, device, action, ticks, pulse)

        # --- 2. PINPOINT HIGHLIGHT & ARROW BUBBLE (ONLY AT LEVEL 3 or INFO) ---
        if hint_level == 3 or action.name == ActionName.INFO:
            if target_el.page_key == device.current_page_key:
                self._draw_direct_bubble(surface, target_el, action, ticks, pulse)

        # --- 3. PAGE NAVIGATION GUIDE (WHEN TARGET IS ON ANOTHER PAGE) ---
        if target_el.page_key != device.current_page_key and hint_level >= 2:
            self._draw_page_navigation_hint(surface, device, target_el)

    def _draw_hud_banner(self, surface: pygame.Surface, device: DeviceBase, action, ticks: int, pulse: float):
        hs = device.hint_service
        hint_level = hs.hint_level

        # Palette by level
        if hint_level == 1:
            border_color = (0, 210, 255)
            badge_bg = (10, 50, 75)
            badge_text_color = (100, 235, 255)
            badge_label = "УРОВЕНЬ 1: ЗАДАЧА"
            btn_label = "? Уточнить (F1)"
            btn_active = True
        elif hint_level == 2:
            border_color = (255, 195, 45)
            badge_bg = (70, 55, 10)
            badge_text_color = (255, 220, 110)
            badge_label = "УРОВЕНЬ 2: УТОЧНЕНИЕ"
            btn_label = "💡 Показать кнопку (F1)"
            btn_active = True
        else:
            border_color = (255, 90, 80)
            badge_bg = (75, 25, 20)
            badge_text_color = (255, 160, 150)
            badge_label = "УРОВЕНЬ 3: ПРЯМАЯ ПОДСКАЗКА"
            btn_label = "🎯 Прямое указание"
            btn_active = False

        # Card geometry
        card_w = 1260
        card_h = 52
        card_x = (1600 - card_w) // 2
        card_y = 42

        # Shadow
        shadow_rect = pygame.Rect(card_x + 3, card_y + 3, card_w, card_h)
        pygame.draw.rect(surface, (5, 8, 12), shadow_rect, border_radius=8)

        # Card base
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((14, 20, 28, 235))
        surface.blit(card_surf, (card_x, card_y))

        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
        pygame.draw.rect(surface, border_color, card_rect, width=2, border_radius=8)

        # Left 1: Step indicator capsule
        curr_step = hs.current_action_index + 1
        total_steps = len(hs.algorithm.actions) if hs.algorithm else 1
        step_str = f"Шаг {curr_step}/{total_steps}"
        step_surf = self.hud_step_font.render(step_str, True, (215, 230, 245))
        step_w = step_surf.get_width() + 18
        step_rect = pygame.Rect(card_x + 10, card_y + 11, step_w, 30)
        pygame.draw.rect(surface, (28, 38, 50), step_rect, border_radius=6)
        pygame.draw.rect(surface, (50, 70, 90), step_rect, width=1, border_radius=6)
        surface.blit(step_surf, (step_rect.x + 9, step_rect.y + 7))

        # Left 2: Level Badge
        badge_surf = self.hud_badge_font.render(badge_label, True, badge_text_color)
        badge_w = badge_surf.get_width() + 18
        badge_rect = pygame.Rect(step_rect.right + 8, card_y + 11, badge_w, 30)
        pygame.draw.rect(surface, badge_bg, badge_rect, border_radius=6)
        pygame.draw.rect(surface, border_color, badge_rect, width=1, border_radius=6)
        surface.blit(badge_surf, (badge_rect.x + 9, badge_rect.y + 7))

        # Right: Escalate Help Button
        btn_w = 185
        btn_h = 32
        self.help_button_rect = pygame.Rect(card_x + card_w - btn_w - 10, card_y + 10, btn_w, btn_h)

        if btn_active:
            btn_bg = (40, 60, 80) if not self.is_help_hovered else (55, 85, 115)
            btn_border = border_color
            btn_txt_col = (255, 255, 255)
        else:
            btn_bg = (30, 35, 42)
            btn_border = (80, 90, 100)
            btn_txt_col = (180, 190, 200)

        pygame.draw.rect(surface, btn_bg, self.help_button_rect, border_radius=6)
        pygame.draw.rect(surface, btn_border, self.help_button_rect, width=1, border_radius=6)
        b_surf = self.hud_btn_font.render(btn_label, True, btn_txt_col)
        surface.blit(b_surf, (self.help_button_rect.x + (btn_w - b_surf.get_width()) // 2, self.help_button_rect.y + 7))

        # Center: Hint Text or Mistake Alert
        text_avail_w = self.help_button_rect.x - badge_rect.right - 24
        text_x = badge_rect.right + 14

        is_flashing_mistake = (ticks < hs.mistake_flash_until_ms)
        if is_flashing_mistake:
            # Flashing mistake warning
            pulse_alert = int(210 + 45 * math.sin(ticks * 0.015))
            alert_prefix = f"⚠ {hs.last_mistake_text} "
            curr_text = hs.get_current_hint_text()
            full_text = alert_prefix + curr_text
            
            wrapped = self._wrap_text(full_text, self.hud_text_font, max_width=text_avail_w)
            if len(wrapped) == 1:
                t_surf = self.hud_text_font.render(wrapped[0], True, (255, pulse_alert, 90))
                surface.blit(t_surf, (text_x, card_y + 16))
            elif len(wrapped) >= 2:
                t1 = self.hud_text_font.render(wrapped[0], True, (255, pulse_alert, 90))
                t2 = self.hud_text_font.render(wrapped[1], True, (255, 240, 200))
                surface.blit(t1, (text_x, card_y + 6))
                surface.blit(t2, (text_x, card_y + 26))
        else:
            curr_text = hs.get_current_hint_text()
            wrapped = self._wrap_text(curr_text, self.hud_text_font, max_width=text_avail_w)
            if len(wrapped) == 1:
                t_surf = self.hud_text_font.render(wrapped[0], True, (245, 250, 255))
                surface.blit(t_surf, (text_x, card_y + 16))
            elif len(wrapped) >= 2:
                t1 = self.hud_text_font.render(wrapped[0], True, (245, 250, 255))
                t2 = self.hud_text_font.render(wrapped[1], True, (220, 235, 250))
                surface.blit(t1, (text_x, card_y + 6))
                surface.blit(t2, (text_x, card_y + 26))

    def _draw_direct_bubble(self, surface: pygame.Surface, target_el, action, ticks: int, pulse: float):
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

        if target_el.pos_left + target_el.width + 16 + bubble_w <= 1585:
            bx = target_el.pos_left + target_el.width + 16
            side = "left"
        elif target_el.pos_left - 16 - bubble_w >= 15:
            bx = target_el.pos_left - 16 - bubble_w
            side = "right"
        else:
            bx = max(15, min(1585 - bubble_w, el_center_x - bubble_w // 2))
            side = "none"

        by = el_center_y - 25
        by = max(100, min(785 - bubble_h, by))

        # Shadow
        shadow_rect = pygame.Rect(bx + 4, by + 4, bubble_w, bubble_h)
        pygame.draw.rect(surface, (5, 10, 15), shadow_rect, border_radius=6)

        # Bubble background & border
        bubble_rect = pygame.Rect(bx, by, bubble_w, bubble_h)
        pygame.draw.rect(surface, (18, 28, 38), bubble_rect, border_radius=6)
        pygame.draw.rect(surface, (0, 195, 235), bubble_rect, width=2, border_radius=6)

        # Pointer arrow
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

        # Text lines
        curr_ty = by + 9
        for r in rendered_lines:
            surface.blit(r, (bx + 12, curr_ty))
            curr_ty += line_h

        if info_line_surf:
            surface.blit(info_line_surf, (bx + 12, curr_ty + 2))

    def _draw_page_navigation_hint(self, surface: pygame.Surface, device: DeviceBase, target_el):
        curr_idx = device.pages.index(device.current_page_key)
        target_idx = device.pages.index(target_el.page_key)
        is_forward = target_idx > curr_idx

        target_page_name = target_el.page_key.value if hasattr(target_el.page_key, 'value') else str(target_el.page_key)
        nav_hint = f"Нужный блок: {target_page_name} ->" if is_forward else f"<- Нужный блок: {target_page_name}"

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
