import io
import pygame
from typing import Optional, Dict, Any

class ActionAnnotator:
    """
    Создает аннотированный снимок экрана симулятора после действия курсанта:
    - При ошибке: КРАСНЫЙ bounding box вокруг нажатого органа + ЗЕЛЕНЫЙ bounding box вокруг требуемого.
    - При успешном действии: ЗЕЛЕНЫЙ bounding box вокруг выполненного органа.
    - Верхняя карточка с детализированным контекстом этапа из обучения (подсказка, номер шага).
    """

    def __init__(self):
        # Детализированные шрифты с anti-aliasing
        self.font_title = pygame.font.SysFont(["segoeui", "calibri", "arial"], 15, bold=True)
        self.font_body = pygame.font.SysFont(["segoeui", "calibri", "arial"], 13)
        self.font_badge = pygame.font.SysFont(["segoeui", "calibri", "arial"], 12, bold=True)

    def capture_action_snapshot(
        self,
        screen_surface: pygame.Surface,
        is_mistake: bool,
        clicked_element_name: str,
        device: Any,
        current_step_idx: int,
        total_steps: int,
        expected_action: Any,
        max_width: int = 1280,
        max_height: int = 720
    ) -> Optional[bytes]:
        try:
            annotated = screen_surface.copy()
            cur_page = getattr(device, "current_page_key", None)

            clicked_el = device.get_element_by_name(clicked_element_name) if device else None
            expected_el = None
            expected_name = ""
            hint_text = ""
            if expected_action:
                expected_name = getattr(expected_action, "parent_element_name", "")
                hint_text = getattr(expected_action, "hint_text", "") or getattr(expected_action, "hint_clarify", "")
                if device:
                    expected_el = device.get_element_by_name(expected_name)

            step_str = f"Шаг {current_step_idx + 1} из {total_steps}"

            # 1. Если ОШИБКА:
            if is_mistake:
                # 1.1. Красный BBox вокруг нажатого органа (если на текущей странице)
                if clicked_el and getattr(clicked_el, "page_key", None) == cur_page:
                    box = clicked_el.rect.inflate(12, 12)
                    fill_surf = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
                    fill_surf.fill((239, 68, 68, 75))
                    annotated.blit(fill_surf, box.topleft)
                    pygame.draw.rect(annotated, (239, 68, 68), box, width=3, border_radius=6)

                    # Ярлык над элементом
                    lbl = self.font_badge.render(f"✕ ОШИБКА: {clicked_element_name}", True, (255, 255, 255))
                    lbl_bg = pygame.Rect(box.x, max(4, box.y - 24), lbl.get_width() + 10, 22)
                    pygame.draw.rect(annotated, (220, 38, 38), lbl_bg, border_radius=4)
                    annotated.blit(lbl, (lbl_bg.x + 5, lbl_bg.y + 3))

                # 1.2. Зеленый BBox вокруг требуемого органа (если на текущей странице)
                if expected_el and getattr(expected_el, "page_key", None) == cur_page:
                    box_exp = expected_el.rect.inflate(12, 12)
                    fill_exp = pygame.Surface((box_exp.width, box_exp.height), pygame.SRCALPHA)
                    fill_exp.fill((16, 185, 129, 75))
                    annotated.blit(fill_exp, box_exp.topleft)
                    pygame.draw.rect(annotated, (16, 185, 129), box_exp, width=3, border_radius=6)

                    lbl_exp = self.font_badge.render(f"✓ ТРЕБОВАЛОСЬ: {expected_name}", True, (255, 255, 255))
                    lbl_bg_exp = pygame.Rect(box_exp.x, max(4, box_exp.y - 24), lbl_exp.get_width() + 10, 22)
                    pygame.draw.rect(annotated, (16, 185, 129), lbl_bg_exp, border_radius=4)
                    annotated.blit(lbl_exp, (lbl_bg_exp.x + 5, lbl_bg_exp.y + 3))
                elif expected_el:
                    # На другом блоке
                    page_name = str(getattr(expected_el, "page_key", "другом блоке"))
                    badge_other = self.font_badge.render(f"ℹ Правильный орган ({expected_name}) находится на {page_name}", True, (255, 240, 180))
                    annotated.blit(badge_other, (30, 105))

                # 1.3. Верхняя карточка контекста ошибки
                w, h = annotated.get_size()
                card_w = w - 40
                card_h = 76
                card_rect = pygame.Rect(20, 16, card_w, card_h)

                card_bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                card_bg.fill((15, 23, 42, 235))
                annotated.blit(card_bg, card_rect.topleft)
                pygame.draw.rect(annotated, (239, 68, 68), card_rect, width=2, border_radius=8)

                t_surf = self.font_title.render(
                    f"🔴 ОШИБКА  •  {step_str}  •  Нажат: {clicked_element_name}  (Требовался: {expected_name or '—'})",
                    True, (254, 202, 202)
                )
                annotated.blit(t_surf, (card_rect.x + 16, card_rect.y + 10))

                context_str = f"💡 Задание этапа: {hint_text}" if hint_text else f"Ожидаемое действие над: {expected_name}"
                b_surf = self.font_body.render(context_str, True, (226, 232, 240))
                annotated.blit(b_surf, (card_rect.x + 16, card_rect.y + 42))

            else:
                # 2. УСПЕШНОЕ ДЕЙСТВИЕ
                if clicked_el and getattr(clicked_el, "page_key", None) == cur_page:
                    box = clicked_el.rect.inflate(12, 12)
                    fill_surf = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
                    fill_surf.fill((16, 185, 129, 65))
                    annotated.blit(fill_surf, box.topleft)
                    pygame.draw.rect(annotated, (16, 185, 129), box, width=3, border_radius=6)

                    lbl = self.font_badge.render(f"✓ ВЫПОЛНЕНО: {clicked_element_name}", True, (255, 255, 255))
                    lbl_bg = pygame.Rect(box.x, max(4, box.y - 24), lbl.get_width() + 10, 22)
                    pygame.draw.rect(annotated, (16, 185, 129), lbl_bg, border_radius=4)
                    annotated.blit(lbl, (lbl_bg.x + 5, lbl_bg.y + 3))

                w, h = annotated.get_size()
                card_w = w - 40
                card_h = 76
                card_rect = pygame.Rect(20, 16, card_w, card_h)

                card_bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                card_bg.fill((15, 23, 42, 225))
                annotated.blit(card_bg, card_rect.topleft)
                pygame.draw.rect(annotated, (16, 185, 129), card_rect, width=2, border_radius=8)

                t_surf = self.font_title.render(
                    f"🟢 ВЫПОЛНЕНО  •  {step_str}  •  Орган управления: {clicked_element_name}",
                    True, (167, 243, 208)
                )
                annotated.blit(t_surf, (card_rect.x + 16, card_rect.y + 10))

                context_str = f"💡 Выполнено задание этапа: {hint_text}" if hint_text else f"Действие подтверждено"
                b_surf = self.font_body.render(context_str, True, (226, 232, 240))
                annotated.blit(b_surf, (card_rect.x + 16, card_rect.y + 42))

            # Масштабирование под компактный JPEG
            cur_w, cur_h = annotated.get_size()
            scale = min(max_width / cur_w, max_height / cur_h, 1.0)
            target_w = max(1, int(cur_w * scale))
            target_h = max(1, int(cur_h * scale))

            if target_w != cur_w or target_h != cur_h:
                final_surf = pygame.transform.smoothscale(annotated, (target_w, target_h))
            else:
                final_surf = annotated

            bio = io.BytesIO()
            pygame.image.save(final_surf, bio, 'JPEG')
            return bio.getvalue()

        except Exception as e:
            print("Action snapshot error:", e)
            return None
