import os
import json
import socket
import threading
import time
import pygame
from typing import Optional, Callable, Dict, Any, Tuple
from config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_TEXT_DIM
from ui.ui_widgets import UIButton, get_ui_font
from network.student_client import StudentClient
from network.exam_protocol import DEFAULT_SERVER_PORT
from network.network_utils import ping_server

PROFILE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "student_profile.json")

class TextInputField:
    def __init__(self, rect: pygame.Rect, label: str, value: str = "", placeholder: str = ""):
        self.rect = rect
        self.label = label
        self.value = value
        self.placeholder = placeholder
        self.is_focused = False
        self.font = get_ui_font(15)
        self.label_font = get_ui_font(13, bold=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.is_focused = self.rect.collidepoint(event.pos)
            return self.is_focused
        elif event.type == pygame.KEYDOWN and self.is_focused:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
                return True
            elif event.key == pygame.K_RETURN:
                self.is_focused = False
                return True
            elif event.unicode and len(event.unicode) > 0 and ord(event.unicode) >= 32:
                self.value += event.unicode
                return True
        return False

    def draw(self, surface: pygame.Surface, draw_label: bool = True):
        # Отрисовка метки над полем (если не встроена в фоновую плашку)
        if draw_label:
            lbl_surf = self.label_font.render(self.label, True, (180, 200, 220))
            surface.blit(lbl_surf, (self.rect.x, self.rect.y - 20))

        # Отрисовка поля ввода
        bg_col = (25, 33, 45) if not self.is_focused else (30, 42, 60)
        border_col = (0, 180, 216) if self.is_focused else (60, 75, 95)
        pygame.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_col, self.rect, width=1, border_radius=6)

        text_to_show = self.value if self.value else self.placeholder
        text_col = COLOR_TEXT if self.value else (100, 115, 130)
        txt_surf = self.font.render(text_to_show, True, text_col)

        # Выравнивание текста с отступом
        surface.blit(txt_surf, (self.rect.x + 10, self.rect.y + (self.rect.height - txt_surf.get_height()) // 2))

        # Мигающий курсор
        if self.is_focused and int(time.time() * 2) % 2 == 0:
            cursor_x = self.rect.x + 10 + self.font.size(self.value)[0] + 2
            cursor_y = self.rect.y + 6
            pygame.draw.line(surface, (0, 210, 255), (cursor_x, cursor_y), (cursor_x, cursor_y + self.rect.height - 12), 2)


class StudentAuthDialog:
    def __init__(
        self,
        on_confirm: Callable[[Dict[str, Any], Optional[StudentClient]], None],
        on_cancel: Callable[[], None],
        client: Optional[StudentClient] = None
    ):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.client = client or StudentClient()

        self.width = 620
        self.height = 460
        self.x = (SCREEN_WIDTH - self.width) // 2
        self.y = (SCREEN_HEIGHT - self.height) // 2

        # Загрузка сохраненного профиля
        profile = self._load_profile()
        default_name = profile.get("full_name", "")
        default_group = profile.get("group", "")
        default_pc = profile.get("pc_name", socket.gethostname())
        default_ip = profile.get("server_ip", "127.0.0.1")

        field_x = self.x + 40
        field_w = self.width - 80
        fh = 36

        self.f_name = TextInputField(
            pygame.Rect(field_x, self.y + 85, field_w, fh),
            "ФИО курсанта:",
            value=default_name,
            placeholder="например: Иванов Иван Иванович"
        )
        self.f_group = TextInputField(
            pygame.Rect(field_x, self.y + 155, (field_w - 20) // 2, fh),
            "Учебная группа / взвод:",
            value=default_group,
            placeholder="например: 401"
        )
        self.f_pc = TextInputField(
            pygame.Rect(field_x + (field_w - 20) // 2 + 20, self.y + 155, (field_w - 20) // 2, fh),
            "Номер рабочего места (ПК):",
            value=default_pc,
            placeholder="ПК-01"
        )
        self.f_server_ip = TextInputField(
            pygame.Rect(field_x, self.y + 225, field_w - 140, fh),
            "IP-адрес сервера преподавателя:",
            value=default_ip,
            placeholder="127.0.0.1 или IP в сети"
        )

        self.status_msg = "Поиск сервера преподавателя в сети..."
        self.status_color = (245, 158, 11)
        self.server_found = False

        # Кнопки
        self.btn_search = UIButton(
            pygame.Rect(field_x + field_w - 130, self.y + 225, 130, fh),
            "Поиск",
            callback=self.start_auto_discovery,
            font_size=13,
            bg_color=(35, 65, 95)
        )

        btn_y = self.y + self.height - 65
        btn_w = 160
        self.btn_confirm = UIButton(
            pygame.Rect(self.x + self.width - 40 - btn_w, btn_y, btn_w, 42),
            "Продолжить ->",
            callback=self._on_submit,
            font_size=14,
            bg_color=(30, 130, 80)
        )
        self.btn_cancel = UIButton(
            pygame.Rect(self.x + 40, btn_y, 140, 42),
            "Отмена",
            callback=self.on_cancel,
            font_size=14,
            bg_color=(75, 80, 90)
        )

        self.title_font = get_ui_font(20, bold=True)
        self.sub_font = get_ui_font(13)

        from ui.plate_renderer import render_auth_dialog_plate
        field_labels = [
            (40, 66, "ФИО курсанта:"),
            (40, 136, "Учебная группа / взвод:"),
            (40 + (field_w - 20) // 2 + 20, 136, "Номер рабочего места (ПК):"),
            (40, 206, "IP-адрес сервера преподавателя:")
        ]
        self.plate_surface = render_auth_dialog_plate(self.width, self.height, field_labels)

        # Фоновый поиск сервера
        self.start_auto_discovery()

    def _load_profile(self) -> Dict[str, Any]:
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_profile(self):
        data = {
            "full_name": self.f_name.value.strip(),
            "group": self.f_group.value.strip(),
            "pc_name": self.f_pc.value.strip(),
            "server_ip": self.f_server_ip.value.strip()
        }
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def start_auto_discovery(self):
        self.status_msg = "Поиск сервера в сети..."
        self.status_color = (245, 158, 11)

        def update_status(text: str):
            self.status_msg = text

        def discover_worker():
            cur_ip = self.f_server_ip.value.strip()
            res = StudentClient.comprehensive_server_discovery(current_ip=cur_ip, on_status=update_status)
            if res:
                ip, port = res
                self.f_server_ip.value = ip
                self.client.set_server(ip, port)
                self.server_found = True
                self._save_profile()
                self.status_msg = f"[OK] Сервер преподавателя найден: {ip}:{port}"
                self.status_color = (52, 211, 153)
            else:
                self.server_found = False
                self.status_msg = "Сервер не найден в сети (введите IP преподавателя вручную)"
                self.status_color = (245, 158, 11)

        t = threading.Thread(target=discover_worker, daemon=True)
        t.start()

    def check_entered_ip(self):
        target_ip = self.f_server_ip.value.strip()
        if not target_ip:
            return
        self.status_msg = f"Проверка связи с {target_ip}..."
        self.status_color = (245, 158, 11)

        def ping_worker():
            if ping_server(target_ip, DEFAULT_SERVER_PORT, timeout=1.0):
                self.client.set_server(target_ip, DEFAULT_SERVER_PORT)
                self.server_found = True
                self._save_profile()
                self.status_msg = f"[OK] Связь с сервером подтверждена: {target_ip}:{DEFAULT_SERVER_PORT}"
                self.status_color = (52, 211, 153)
            else:
                self.server_found = False
                self.status_msg = f"[!] Сервер {target_ip} недоступен (проверьте IP или Брандмауэр)"
                self.status_color = (239, 68, 68)

        threading.Thread(target=ping_worker, daemon=True).start()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.btn_confirm.handle_event(event):
            return True
        if self.btn_cancel.handle_event(event):
            return True
        if self.btn_search.handle_event(event):
            # Кнопка Поиск проверяет введенный IP и запускает автопоиск
            self.start_auto_discovery()
            return True

        # Переключение Tab между полями
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            fields = [self.f_name, self.f_group, self.f_pc, self.f_server_ip]
            current_idx = -1
            for i, f in enumerate(fields):
                if f.is_focused:
                    current_idx = i
                    f.is_focused = False
                    break
            next_idx = (current_idx + 1) % len(fields)
            fields[next_idx].is_focused = True
            return True

        if self.f_name.handle_event(event):
            return True
        if self.f_group.handle_event(event):
            return True
        if self.f_pc.handle_event(event):
            return True
        if self.f_server_ip.handle_event(event):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.check_entered_ip()
            return True

        return True  # Блокирует клики под модальным окном

    def _on_submit(self):
        self._save_profile()
        target_ip = self.f_server_ip.value.strip() or "127.0.0.1"
        self.client.set_server(target_ip, DEFAULT_SERVER_PORT)

        data = {
            "full_name": self.f_name.value.strip() or "Курсант",
            "group": self.f_group.value.strip() or "401",
            "pc_name": self.f_pc.value.strip() or socket.gethostname(),
            "server_ip": target_ip
        }
        self.on_confirm(data, self.client)

    def draw(self, surface: pygame.Surface):
        # Затемнение фона
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        surface.blit(overlay, (0, 0))

        # Тень и плашка карточки диалога
        shadow_rect = pygame.Rect(self.x + 6, self.y + 6, self.width, self.height)
        pygame.draw.rect(surface, (10, 15, 20), shadow_rect, border_radius=14)
        surface.blit(self.plate_surface, (self.x, self.y))

        # Поля ввода
        self.f_name.draw(surface, draw_label=False)
        self.f_group.draw(surface, draw_label=False)
        self.f_pc.draw(surface, draw_label=False)
        self.f_server_ip.draw(surface, draw_label=False)
        self.btn_search.draw(surface)

        # Статус сети
        stat_surf = self.sub_font.render(self.status_msg, True, self.status_color)
        surface.blit(stat_surf, (self.x + 40, self.y + 275))

        # Кнопки
        self.btn_confirm.draw(surface)
        self.btn_cancel.draw(surface)


class WaitingForTeacherDialog:
    def __init__(
        self,
        student_data: Dict[str, Any],
        device_name: str,
        algo_name: str,
        on_start_now: Callable[[], None],
        on_cancel: Callable[[], None]
    ):
        self.student_data = student_data
        self.device_name = device_name
        self.algo_name = algo_name
        self.on_start_now = on_start_now
        self.on_cancel = on_cancel

        self.width = 560
        self.height = 320
        self.x = (SCREEN_WIDTH - self.width) // 2
        self.y = (SCREEN_HEIGHT - self.height) // 2

        self.btn_start = UIButton(
            pygame.Rect(self.x + self.width - 220, self.y + self.height - 60, 180, 40),
            "Начать автономно",
            callback=self.on_start_now,
            font_size=13,
            bg_color=(35, 95, 140)
        )
        self.btn_cancel = UIButton(
            pygame.Rect(self.x + 40, self.y + self.height - 60, 130, 40),
            "Отмена",
            callback=self.on_cancel,
            font_size=13,
            bg_color=(75, 80, 90)
        )

        from ui.plate_renderer import render_waiting_dialog_plate
        name = self.student_data.get("full_name", "")
        group = self.student_data.get("group", "")
        pc = self.student_data.get("pc_name", "")
        self.plate_surface = render_waiting_dialog_plate(
            self.width, self.height, name, group, pc, self.device_name, self.algo_name
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.btn_start.handle_event(event):
            return True
        if self.btn_cancel.handle_event(event):
            return True
        return True

    def draw(self, surface: pygame.Surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 195))
        surface.blit(overlay, (0, 0))

        shadow_rect = pygame.Rect(self.x + 6, self.y + 6, self.width, self.height)
        pygame.draw.rect(surface, (10, 15, 20), shadow_rect, border_radius=14)
        surface.blit(self.plate_surface, (self.x, self.y))

        # Анимированный пульсирующий индикатор
        pulse = (int(time.time() * 3) % 2 == 0)
        ind_col = (52, 211, 153) if pulse else (16, 185, 129)
        pygame.draw.circle(surface, ind_col, (self.x + 55, self.y + 42), 9)

        self.btn_start.draw(surface)
        self.btn_cancel.draw(surface)

