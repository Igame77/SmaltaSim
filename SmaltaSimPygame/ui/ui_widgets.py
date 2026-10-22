
import pygame
from typing import Callable, Optional, Tuple, List

from config import (
    COLOR_BUTTON,
    COLOR_BUTTON_HOVER,
    COLOR_BUTTON_ACTIVE,
    COLOR_BUTTON_BORDER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
)

UI_FONT_FAMILIES = ["segoeui", "calibri", "arial", "tahoma"]

# Единая палитра интерфейса
# Сине-графитовая палитра под фон с флагом
UI_BORDER_HOVER = (165, 192, 210)
UI_DISABLED_BG = (35, 42, 48)
UI_DISABLED_BORDER = (75, 90, 102)

UI_CARD_BG = (25, 42, 54, 245)
UI_CARD_HOVER = (40, 64, 82, 250)
UI_CARD_ACTIVE = (20, 33, 44, 250)
UI_CARD_BORDER = (91, 125, 148)


def get_ui_font(
    size: int,
    bold: bool = False,
    italic: bool = False
) -> pygame.font.Font:
    """Системный сглаженный шрифт с поддержкой кириллицы."""
    return pygame.font.SysFont(
        UI_FONT_FAMILIES,
        size,
        bold=bold,
        italic=italic
    )


class UIButton:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        callback: Optional[Callable[[], None]] = None,
        font_size: int = 16,
        is_enabled: bool = True,
        bg_color: Tuple[int, int, int] = COLOR_BUTTON,
        border_radius: int = 6
    ):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.font_size = font_size
        self.is_enabled = is_enabled
        self.bg_color = bg_color
        self.border_radius = border_radius
        self.is_hovered = False
        self.is_pressed = False

        self._fonts = {
            font_size: pygame.font.SysFont("Arial", font_size, bold=True),
            font_size - 2: pygame.font.SysFont("Arial", max(10, font_size - 2), bold=True),
            font_size - 4: pygame.font.SysFont("Arial", max(9, font_size - 4), bold=True),
        }

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_enabled:
            self.is_pressed = False
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            if not self.is_hovered:
                self.is_pressed = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.is_pressed
            self.is_pressed = False

            if was_pressed and self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True

        return False

    def draw(self, surface: pygame.Surface):
        # Небольшое смещение при нажатии
        offset_y = 2 if self.is_pressed else 0
        draw_rect = self.rect.move(0, offset_y)

        if not self.is_enabled:
            bg = UI_DISABLED_BG
            txt_col = COLOR_TEXT_DIM
            border_col = UI_DISABLED_BORDER

        elif self.is_pressed:
            bg = (20, 33, 44)
            txt_col = (255, 255, 255)
            border_col = (165, 192, 210)

        elif self.is_hovered:
            bg = (56, 86, 106)
            txt_col = (255, 255, 255)
            border_col = (165, 192, 210)

        else:
            bg = self.bg_color
            txt_col = (245, 248, 250)
            border_col = (91, 125, 148)

        pygame.draw.rect(
            surface, bg, draw_rect,
            border_radius=self.border_radius
        )
        pygame.draw.rect(
            surface, border_col, draw_rect,
            width=1, border_radius=self.border_radius
        )

        # Подбираем размер текста, чтобы он не выходил за кнопку
        target_font = self._fonts[self.font_size]
        text_surf = target_font.render(self.text, True, txt_col)

        for size in (self.font_size - 2, self.font_size - 4):
            if text_surf.get_width() <= draw_rect.width - 20:
                break
            target_font = self._fonts[size]
            text_surf = target_font.render(self.text, True, txt_col)

        tx = self.rect.x + (self.rect.width - text_surf.get_width()) // 2
        ty = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (tx, ty))


class MenuCardButton:
    def __init__(
        self,
        rect: pygame.Rect,
        title: str,
        subtitle: str,
        callback: Optional[Callable[[], None]] = None,
        accent_color: Tuple[int, int, int] = UI_BORDER_HOVER,
        border_radius: int = 8,
        img_normal: Optional[pygame.Surface] = None,
        img_hover: Optional[pygame.Surface] = None
    ):
        self.rect = rect
        self.title = title
        self.subtitle = subtitle
        self.callback = callback
        self.accent_color = accent_color
        self.border_radius = border_radius
        self.img_normal = img_normal
        self.img_hover = img_hover
        self.is_hovered = False
        self.is_pressed = False

        self.font_title = get_ui_font(20, bold=True)
        self.font_sub = get_ui_font(13)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            if not self.is_hovered:
                self.is_pressed = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.is_pressed
            self.is_pressed = False

            if was_pressed and self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True

        return False

    def draw(self, surface: pygame.Surface):
        offset_y = 2 if self.is_pressed else 0
        draw_x = self.rect.x
        draw_y = self.rect.y + offset_y

        if self.img_normal:
            img = (
                self.img_hover
                if self.is_hovered and self.img_hover
                else self.img_normal
            )
            surface.blit(img, (draw_x, draw_y))
            return

        card_surf = pygame.Surface(
            (self.rect.width, self.rect.height),
            pygame.SRCALPHA
        )

        if self.is_pressed:
            bg_col = UI_CARD_ACTIVE
            border_col = self.accent_color
        elif self.is_hovered:
            bg_col = UI_CARD_HOVER
            border_col = self.accent_color
        else:
            bg_col = UI_CARD_BG
            border_col = UI_CARD_BORDER

        card_surf.fill(bg_col)

        pygame.draw.rect(
            card_surf,
            border_col,
            (0, 0, self.rect.width, self.rect.height),
            width=1,
            border_radius=self.border_radius
        )

        stripe_w = 6 if self.is_hovered else 4
        pygame.draw.rect(
            card_surf,
            self.accent_color,
            (0, 0, stripe_w, self.rect.height),
            border_top_left_radius=self.border_radius,
            border_bottom_left_radius=self.border_radius
        )

        title_color = COLOR_TEXT
        subtitle_color = COLOR_TEXT_DIM

        title_surf = self.font_title.render(
            self.title, True, title_color
        )
        subtitle_surf = self.font_sub.render(
            self.subtitle, True, subtitle_color
        )

        card_surf.blit(title_surf, (24, 14))
        card_surf.blit(subtitle_surf, (24, 44))

        surface.blit(card_surf, (draw_x, draw_y))


class ModalDialog:
    def __init__(
        self,
        title: str,
        message: str,
        buttons: List[
            Tuple[str, Callable[[], None], Tuple[int, int, int]]
        ],
        width: int = 580,
        height: int = 280,
        layout: str = "auto"
    ):
        self.title = title
        self.raw_message = message
        self.title_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.body_font = pygame.font.SysFont("Arial", 15)

        # Переносим текст по ширине окна
        max_msg_w = width - 60
        self.formatted_lines = []

        for raw_line in message.split("\n"):
            if not raw_line.strip():
                self.formatted_lines.append("")
                continue

            words = raw_line.split()
            current_line = ""

            for word in words:
                test_line = f"{current_line} {word}".strip()
                rendered = self.body_font.render(
                    test_line, True, COLOR_TEXT
                )

                if rendered.get_width() <= max_msg_w:
                    current_line = test_line
                else:
                    if current_line:
                        self.formatted_lines.append(current_line)
                    current_line = word

            if current_line:
                self.formatted_lines.append(current_line)

        if layout == "auto":
            is_list = (
                len(buttons) > 2
                or any(len(button[0]) > 14 for button in buttons)
            )
        else:
            is_list = layout == "list"

        header_h = 65
        line_spacing = 22
        body_h = len(self.formatted_lines) * line_spacing + 20
        btn_h = 42

        if is_list:
            buttons_h = len(buttons) * (btn_h + 10) + 10
        else:
            buttons_h = btn_h + 20

        min_needed_h = header_h + body_h + buttons_h + 20
        self.height = max(height, min_needed_h)
        self.width = max(width, 540 if is_list else 480)

        # Размеры рабочего окна проекта
        screen_w, screen_h = 1600, 870
        self.x = (screen_w - self.width) // 2
        self.y = (screen_h - self.height) // 2

        self.rect = pygame.Rect(
            self.x, self.y, self.width, self.height
        )
        self.is_open = True
        self.ui_buttons: List[UIButton] = []

        if is_list:
            btn_w = self.width - 60
            current_y = self.y + header_h + body_h

            for text, callback, color in buttons:
                button = UIButton(
                    pygame.Rect(
                        self.x + 30, current_y, btn_w, btn_h
                    ),
                    text,
                    callback=callback,
                    font_size=15,
                    bg_color=color
                )
                self.ui_buttons.append(button)
                current_y += btn_h + 10

        else:
            count = len(buttons)
            btn_w = min(
                180,
                (self.width - 60 - (count - 1) * 16) // max(1, count)
            )
            gap = 16
            total_w = count * btn_w + (count - 1) * gap
            start_x = self.x + (self.width - total_w) // 2
            button_y = self.y + self.height - btn_h - 22

            for index, (text, callback, color) in enumerate(buttons):
                button_x = start_x + index * (btn_w + gap)

                button = UIButton(
                    pygame.Rect(
                        button_x, button_y, btn_w, btn_h
                    ),
                    text,
                    callback=callback,
                    font_size=15,
                    bg_color=color
                )
                self.ui_buttons.append(button)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        for button in self.ui_buttons:
            if button.handle_event(event):
                return True

        # Блокируем клики по фону за диалогом
        if event.type in (
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP
        ):
            return True

        return False

    def draw(self, surface: pygame.Surface):
        if not self.is_open:
            return

        screen_w, screen_h = surface.get_size()

        overlay = pygame.Surface(
            (screen_w, screen_h), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 165))
        surface.blit(overlay, (0, 0))

        # Тень окна
        shadow_rect = pygame.Rect(
            self.x + 6, self.y + 6,
            self.width, self.height
        )
        pygame.draw.rect(
            surface, (8, 15, 22),
            shadow_rect, border_radius=8
        )

        # Окно диалога
        pygame.draw.rect(
            surface, (25, 42, 54),
            self.rect, border_radius=8
        )
        pygame.draw.rect(
            surface, (91, 125, 148),
            self.rect, width=2, border_radius=8
        )

        title_surf = self.title_font.render(
            self.title, True, (245, 248, 250)
        )
        surface.blit(title_surf, (self.x + 25, self.y + 20))

        pygame.draw.line(
            surface,
            (91, 125, 148),
            (self.x + 20, self.y + 54),
            (self.x + self.width - 20, self.y + 54),
            1
        )

        message_y = self.y + 70
        for line in self.formatted_lines:
            if line:
                line_surf = self.body_font.render(
                    line, True, (220, 230, 238)
                )
                surface.blit(
                    line_surf, (self.x + 30, message_y)
                )
            message_y += 22

        for button in self.ui_buttons:
            button.draw(surface)
