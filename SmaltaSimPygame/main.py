import sys
import pygame
from typing import Optional, List, Dict
from enum import Enum, auto

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, CANVAS_WIDTH, CANVAS_HEIGHT, NAVBAR_HEIGHT,
    FPS, COLOR_BG, COLOR_NAVBAR, COLOR_NAVBAR_BORDER, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_ACCENT, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    ApplicationMode, Assets
)
from core.timer_service import TimerService
from core.algorithm_service import ActionName
from devices.device_base import DeviceBase
from devices.smalta import create_smalta_device, get_smalta_algorithms
from devices.rls_onc import create_rls_device, get_rls_algorithms
from ui.ui_widgets import UIButton, ModalDialog
from ui.hint_renderer import HintRenderer

class AppState(Enum):
    MAIN_MENU = auto()
    SIMULATION = auto()

class SimulatorApp:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Vkm.ComplexSim - Комплексный симулятор устройств РЭБ")
        
        # Display with hardware scaling and resizable/fullscreen support
        self.is_fullscreen = False
        flags = pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        self.clock = pygame.time.Clock()

        # Load Menu Background
        self.menu_bg = pygame.image.load(str(Assets.BG_MAIN)).convert()
        self.menu_bg = pygame.transform.smoothscale(self.menu_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 18)
        self.nav_font = pygame.font.SysFont("Arial", 14, bold=True)
        self.badge_font = pygame.font.SysFont("Arial", 13, bold=True)
        self.header_font = pygame.font.SysFont("Arial", 14, bold=True)

        # TrollFace Easter egg
        self.troll_face_img = pygame.image.load(str(Assets.TROLL_FACE)).convert_alpha()
        self.troll_face_img = pygame.transform.smoothscale(self.troll_face_img, (120, 100))
        self.cheat_sequence = [pygame.K_z, pygame.K_d, pygame.K_c, pygame.K_t, pygame.K_c, pygame.K_l, pygame.K_f, pygame.K_v]
        self.entered_keys = []
        self.is_god_mode = False
        self.show_troll_until_ms = 0

        # State
        self.state = AppState.MAIN_MENU
        self.mode = ApplicationMode.TRAINING
        self.active_device: Optional[DeviceBase] = None
        self.active_dialog: Optional[ModalDialog] = None
        self.hint_renderer = HintRenderer()

        # Build Devices and Algorithms catalog
        self.devices_catalog: Dict[str, DeviceBase] = {
            "smalta": create_smalta_device(),
            "rls": create_rls_device(),
        }
        self.algorithms_catalog = {
            "smalta": get_smalta_algorithms(),
            "rls": get_rls_algorithms(),
        }

        # UI Elements
        self._build_main_menu_buttons()
        self.btn_fullscreen = UIButton(
            pygame.Rect(SCREEN_WIDTH - 170, 18, 145, 34),
            "⛶ На весь экран",
            callback=self.toggle_fullscreen,
            font_size=13,
            bg_color=(45, 60, 75)
        )
        self.btn_sim_fullscreen = UIButton(
            pygame.Rect(SCREEN_WIDTH - 60, 4, 46, 28),
            "⛶",
            callback=self.toggle_fullscreen,
            font_size=16,
            bg_color=(40, 52, 65)
        )

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        pygame.display.toggle_fullscreen()
        self.btn_fullscreen.text = "🗗 В окно" if self.is_fullscreen else "⛶ На весь экран"

    def _build_main_menu_buttons(self):
        btn_w, btn_h = 240, 52
        start_x = 100
        start_y = 280
        gap = 22

        self.menu_buttons = [
            UIButton(
                pygame.Rect(start_x, start_y, btn_w, btn_h),
                "Обучение",
                callback=lambda: self._open_device_selection(ApplicationMode.TRAINING),
                font_size=18,
                bg_color=(35, 110, 160)
            ),
            UIButton(
                pygame.Rect(start_x, start_y + (btn_h + gap), btn_w, btn_h),
                "Экзамен",
                callback=lambda: self._open_device_selection(ApplicationMode.EXAMINE),
                font_size=18,
                bg_color=(170, 95, 30)
            ),
            UIButton(
                pygame.Rect(start_x, start_y + 2 * (btn_h + gap), btn_w, btn_h),
                "Информация",
                callback=self._show_info_dialog,
                font_size=17,
                bg_color=(50, 65, 80)
            ),
            UIButton(
                pygame.Rect(start_x, start_y + 3 * (btn_h + gap), btn_w, btn_h),
                "Выход",
                callback=self.quit,
                font_size=17,
                bg_color=(120, 45, 45)
            )
        ]

    def _show_info_dialog(self):
        msg = (
            "Vkm.ComplexSim — Комплексный симулятор устройств РЭБ и РЛС\n\n"
            "Программа предназначена для обучения и проверки знаний курсантов\n"
            "по приборам и комплексам радиоэлектронной борьбы и радиолокации:\n"
            "  * Станция активных помех ЛО01 'Смальта' (блоки П, Р, И, К)\n"
            "  * Импульсная РЛС ОНЦ (пульты управления, круговой радар, генератор Г5-15, осциллограф С1-65)\n\n"
            "В режиме 'Обучение' доступна интерактивная пошаговая инструкция с динамической подсветкой.\n"
            "В режиме 'Экзамен' оценивается полнота и правильный порядок действий по формуле кафедры.\n"
            "Горячие клавиши: F11 / Alt+Enter — полноэкранный режим, Пробел — следующий шаг в инфо-подсказках."
        )
        self.active_dialog = ModalDialog(
            "О программе",
            msg,
            [("Закрыть", lambda: setattr(self, 'active_dialog', None), (60, 75, 90))],
            width=700,
            height=380,
            layout="row"
        )

    def _open_device_selection(self, mode: ApplicationMode):
        self.mode = mode
        def choose(dev_key: str):
            self.active_dialog = None
            self._open_algorithm_selection(dev_key)

        buttons = [
            ("ЛО01 Смальта", lambda: choose("smalta"), (35, 110, 160)),
            ("РЛС ОНЦ", lambda: choose("rls"), (30, 130, 90)),
            ("Отмена", lambda: setattr(self, 'active_dialog', None), (75, 80, 85)),
        ]
        self.active_dialog = ModalDialog(
            f"Выбор изделия ({mode.value})",
            "Выберите станцию или приборный комплекс для работы:",
            buttons,
            width=620,
            height=250,
            layout="row"
        )

    def _open_algorithm_selection(self, dev_key: str):
        device = self.devices_catalog[dev_key]
        algos = self.algorithms_catalog[dev_key]

        if len(algos) == 1:
            self.start_simulation(device, algos[0])
            return

        def choose_algo(algo):
            self.active_dialog = None
            self.start_simulation(device, algo)

        buttons = []
        for a in algos:
            buttons.append((a.name, lambda alg=a: choose_algo(alg), (40, 85, 125)))
        buttons.append(("Отмена", lambda: setattr(self, 'active_dialog', None), (75, 80, 85)))

        self.active_dialog = ModalDialog(
            "Выбор алгоритма работы",
            f"Изделие: {device.readable_name}\nВыберите требуемое учебное задание:",
            buttons,
            width=700,
            height=360,
            layout="list"
        )

    def start_simulation(self, device: DeviceBase, algorithm):
        self.active_device = device
        self.is_god_mode = False
        self.entered_keys.clear()
        device.apply_algorithm(algorithm)

        if self.mode == ApplicationMode.TRAINING:
            device.hint_service.start_training(algorithm, device)
        else:
            for el in device.elements:
                el.is_enabled = True
                el.is_hint_open = False

        self._build_navbar_buttons()
        self.state = AppState.SIMULATION

    def _build_navbar_buttons(self):
        ny = CANVAS_HEIGHT + 14
        bh = 42

        # Prev button
        self.btn_prev = UIButton(
            pygame.Rect(30, ny, 250, bh),
            "<- Предыдущий блок",
            callback=self._on_prev_page,
            font_size=14
        )

        # Center finish button
        self.btn_finish = UIButton(
            pygame.Rect((SCREEN_WIDTH - 220) // 2, ny, 220, bh),
            "Завершить" if self.mode == ApplicationMode.EXAMINE else "Главное меню",
            callback=self._on_finish_click,
            font_size=15,
            bg_color=(160, 50, 45) if self.mode == ApplicationMode.EXAMINE else (45, 100, 140)
        )

        # Next button
        self.btn_next = UIButton(
            pygame.Rect(SCREEN_WIDTH - 280, ny, 250, bh),
            "Следующий блок ->",
            callback=self._on_next_page,
            font_size=14
        )

    def _update_navbar_buttons_state(self):
        if not self.active_device:
            return

        prv_key = self.active_device.get_previous_page_key()
        nxt_key = self.active_device.get_next_page_key()

        self.btn_prev.is_enabled = prv_key is not None
        if prv_key:
            name = prv_key.value if hasattr(prv_key, 'value') else str(prv_key)
            self.btn_prev.text = f"<- {name}"
        else:
            self.btn_prev.text = "<- Начало"

        self.btn_next.is_enabled = nxt_key is not None
        if nxt_key:
            name = nxt_key.value if hasattr(nxt_key, 'value') else str(nxt_key)
            self.btn_next.text = f"{name} ->"
        else:
            self.btn_next.text = "Конец ->"

    def _on_prev_page(self):
        if self.active_device:
            self.active_device.go_previous()

    def _on_next_page(self):
        if self.active_device:
            self.active_device.go_forward()

    def _on_finish_click(self):
        if self.mode == ApplicationMode.TRAINING:
            self.state = AppState.MAIN_MENU
            self.active_device = None
            return

        # Examine mode: confirm submission
        def submit():
            self.active_dialog = None
            self._show_exam_results()

        buttons = [
            ("Да, завершить", submit, (160, 50, 45)),
            ("Отмена", lambda: setattr(self, 'active_dialog', None), (70, 75, 80))
        ]
        self.active_dialog = ModalDialog(
            "Завершение экзамена",
            "Вы уверены, что хотите завершить экзамен?\nВаш результат будет рассчитан и сохранен.",
            buttons,
            width=540,
            height=240,
            layout="row"
        )

    def _show_exam_results(self):
        if not self.active_device or not self.active_device.current_algorithm:
            return

        if self.is_god_mode:
            score = 5
            details_str = "Активирован специальный режим отличника (GodMode)!\nОценка: 5 (Отлично)\nОшибок: 0"
        else:
            res = self.active_device.history_service.calculate_score(self.active_device.current_algorithm)
            score = res["score"]
            details_str = (
                f"Итоговая оценка: {score} из 5\n"
                f"Выполнено эталонных действий: {int(res['pct_ethalon'] * 100)}%\n"
                f"Правильный порядок: {int(res['pct_order'] * 100)}%\n"
                f"Ошибочных / лишних действий: {res['wrong_actions']}"
            )

        grade_names = {
            5: "ОТЛИЧНО (5)",
            4: "ХОРОШО (4)",
            3: "УДОВЛЕТВОРИТЕЛЬНО (3)",
            2: "НЕУДОВЛЕТВОРИТЕЛЬНО (2)",
            1: "НЕУДОВЛЕТВОРИТЕЛЬНО (1)",
        }
        title = f"Результат: {grade_names.get(score, str(score))}"

        def retry():
            self.active_dialog = None
            self.start_simulation(self.active_device, self.active_device.current_algorithm)

        def exit_to_menu():
            self.active_dialog = None
            self.state = AppState.MAIN_MENU
            self.active_device = None

        buttons = [
            ("Повторить", retry, (45, 110, 160)),
            ("В главное меню", exit_to_menu, (70, 80, 90)),
        ]
        self.active_dialog = ModalDialog(title, details_str, buttons, width=560, height=280, layout="row")

    def _check_cheat_code(self, key):
        if self.mode != ApplicationMode.EXAMINE or self.is_god_mode:
            return

        self.entered_keys.append(key)
        if len(self.entered_keys) > len(self.cheat_sequence):
            self.entered_keys.pop(0)

        if self.entered_keys == self.cheat_sequence:
            self.is_god_mode = True
            self.show_troll_until_ms = pygame.time.get_ticks() + 2500

    def run(self):
        while True:
            dt_ms = self.clock.tick(FPS)
            TimerService.get_instance().update()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()

                # Fullscreen hotkeys: F11 or Alt+Enter
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                        self.toggle_fullscreen()
                        continue

                    # Cheat key listener
                    self._check_cheat_code(event.key)
                    
                    # Space advances INFO step in training
                    if event.key == pygame.K_SPACE and self.active_device and self.active_device.hint_service:
                        curr_action = self.active_device.hint_service.get_current_action()
                        if curr_action and curr_action.name == ActionName.INFO:
                            self.active_device.hint_service.advance()

                # Modal dialog handles event first
                if self.active_dialog:
                    self.active_dialog.handle_event(event)
                    continue

                # Main Menu events
                if self.state == AppState.MAIN_MENU:
                    self.btn_fullscreen.handle_event(event)
                    for b in self.menu_buttons:
                        b.handle_event(event)

                # Simulation events
                elif self.state == AppState.SIMULATION:
                    self.btn_sim_fullscreen.handle_event(event)
                    # Navbar buttons
                    if self.btn_prev.handle_event(event):
                        continue
                    if self.btn_finish.handle_event(event):
                        continue
                    if self.btn_next.handle_event(event):
                        continue

                    # Device canvas elements
                    if self.active_device:
                        self.active_device.handle_event(event)

            # Update
            if self.state == AppState.SIMULATION and self.active_device:
                self.active_device.update(dt_ms)
                self._update_navbar_buttons_state()

                # Training complete check
                if (
                    self.mode == ApplicationMode.TRAINING
                    and self.active_device.hint_service.is_training_complete
                    and not self.active_dialog
                ):
                    def to_exam():
                        self.active_dialog = None
                        self.mode = ApplicationMode.EXAMINE
                        self.start_simulation(self.active_device, self.active_device.current_algorithm)

                    def to_menu():
                        self.active_dialog = None
                        self.state = AppState.MAIN_MENU
                        self.active_device = None

                    self.active_dialog = ModalDialog(
                        "Обучение завершено!",
                        "Поздравляем! Вы успешно выполнили все шаги алгоритма.\nХотите проверить свои знания в режиме 'Экзамен'?",
                        [("На экзамен", to_exam, (170, 95, 30)), ("В главное меню", to_menu, (60, 75, 90))],
                        width=580,
                        height=250,
                        layout="row"
                    )

            # Draw
            self.draw()
            pygame.display.flip()

    def draw(self):
        if self.state == AppState.MAIN_MENU:
            self.draw_main_menu()
        elif self.state == AppState.SIMULATION:
            self.draw_simulation()

        # Modal dialog on top
        if self.active_dialog:
            self.active_dialog.draw(self.screen)

    def draw_main_menu(self):
        self.screen.blit(self.menu_bg, (0, 0))

        # Title Card with dark translucent plate
        card = pygame.Surface((700, 150), pygame.SRCALPHA)
        card.fill((15, 20, 25, 210))
        pygame.draw.rect(card, (0, 180, 220), (0, 0, 700, 150), width=2, border_radius=8)

        t1 = self.title_font.render("Vkm.ComplexSim", True, (255, 255, 255))
        t2 = self.subtitle_font.render("Комплексный симулятор устройств РЭБ и радиолокации", True, (0, 210, 255))
        t3 = self.subtitle_font.render("Учебный тренажер по изделиям ЛО01 'Смальта' и РЛС ОНЦ", True, COLOR_TEXT_DIM)

        card.blit(t1, (25, 20))
        card.blit(t2, (25, 68))
        card.blit(t3, (25, 100))

        self.screen.blit(card, (100, 80))

        # Buttons
        for b in self.menu_buttons:
            b.draw(self.screen)

        # Fullscreen button in menu
        self.btn_fullscreen.draw(self.screen)

    def draw_simulation(self):
        # 1. Draw active device canvas (0..800)
        if self.active_device:
            self.active_device.draw(self.screen)

        # 2. Sleek Top Status Ribbon (Semi-transparent overlay at Y=0..36, leaves station visible)
        if self.active_device:
            top_bar = pygame.Surface((SCREEN_WIDTH, 36), pygame.SRCALPHA)
            top_bar.fill((12, 18, 24, 200))
            pygame.draw.line(top_bar, (40, 52, 65), (0, 35), (SCREEN_WIDTH, 35), 1)
            self.screen.blit(top_bar, (0, 0))

            # Device and current algorithm info
            algo_name = self.active_device.current_algorithm.name if self.active_device.current_algorithm else ""
            dev_str = f"Станция: {self.active_device.readable_name}   |   Задание: {algo_name}"
            info_surf = self.header_font.render(dev_str, True, (225, 235, 245))
            self.screen.blit(info_surf, (20, 8))

            # Mode badge
            mode_color = COLOR_SUCCESS if self.mode == ApplicationMode.TRAINING else COLOR_WARNING
            badge_surf = self.badge_font.render(f"[ {self.mode.value.upper()} ]", True, mode_color)
            self.screen.blit(badge_surf, (SCREEN_WIDTH - 210, 9))

            # Fullscreen button in simulation
            self.btn_sim_fullscreen.draw(self.screen)

        # 3. Draw Training Hints Overlay
        if self.mode == ApplicationMode.TRAINING and self.active_device:
            self.hint_renderer.draw(self.screen, self.active_device)

        # 4. Draw Bottom Navbar (800..870)
        nav_rect = pygame.Rect(0, CANVAS_HEIGHT, SCREEN_WIDTH, NAVBAR_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_NAVBAR, nav_rect)
        pygame.draw.line(self.screen, COLOR_NAVBAR_BORDER, (0, CANVAS_HEIGHT), (SCREEN_WIDTH, CANVAS_HEIGHT), 2)

        # Navbar buttons
        self.btn_prev.draw(self.screen)
        self.btn_finish.draw(self.screen)
        self.btn_next.draw(self.screen)

        # Current page name indicator in center of navbar
        if self.active_device:
            curr_pg = self.active_device.current_page_key
            pg_title = curr_pg.value if hasattr(curr_pg, 'value') else str(curr_pg)
            total_pgs = len(self.active_device.pages)
            curr_pg_idx = self.active_device.pages.index(curr_pg) + 1
            pg_label = f"Панель {curr_pg_idx}/{total_pgs}: {pg_title}"
            pg_surf = self.nav_font.render(pg_label, True, (160, 180, 200))
            # Position above finish button or centered in navbar
            px = (SCREEN_WIDTH - pg_surf.get_width()) // 2
            py = CANVAS_HEIGHT + 3
            self.screen.blit(pg_surf, (px, py))

        # 5. TrollFace easter egg popup
        if pygame.time.get_ticks() < self.show_troll_until_ms:
            tx = (SCREEN_WIDTH - 120) // 2
            ty = CANVAS_HEIGHT - 130
            self.screen.blit(self.troll_face_img, (tx, ty))

    def quit(self):
        pygame.quit()
        sys.exit(0)

if __name__ == "__main__":
    app = SimulatorApp()
    app.run()
