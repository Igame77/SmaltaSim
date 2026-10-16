import sys
import time
import socket
import pygame
from typing import Optional, List, Dict, Any
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
from ui.ui_widgets import UIButton, ModalDialog, MenuCardButton
from ui.hint_renderer import HintRenderer
from ui.student_auth_dialog import StudentAuthDialog, WaitingForTeacherDialog
from network.student_client import StudentClient
from network.action_annotator import ActionAnnotator
from network.exam_protocol import EventType, StudentStatus

class AppState(Enum):
    MAIN_MENU = auto()
    SIMULATION = auto()

class SimulatorApp:
    def __init__(self):
        # Enable Per-Monitor DPI Awareness on Windows to eliminate DWM scaling blur/artifacts
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    import ctypes
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass

        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Vkm.ComplexSim - Комплексный симулятор устройств РЭБ")
        
        # Display with hardware scaling and resizable/fullscreen support
        self.is_fullscreen = False
        flags = pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except Exception:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # Load Menu Background
        self.menu_bg = pygame.image.load(str(Assets.BG_MAIN)).convert()
        self.menu_bg = pygame.transform.smoothscale(self.menu_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # Load Crisp Menu Image Plates
        try:
            self.header_plate = pygame.image.load(str(Assets.UI_HEADER_PLATE)).convert_alpha()
        except Exception:
            self.header_plate = None

        try:
            self.devices_panel_plate = pygame.image.load(str(Assets.UI_DEVICES_PANEL)).convert_alpha()
        except Exception:
            self.devices_panel_plate = None

        # Fonts - четкие детальные шрифты с поддержкой Segoe UI / Calibri
        font_families = ["segoeui", "calibri", "arial"]
        self.title_font = pygame.font.SysFont(font_families, 34, bold=True)
        self.subtitle_font = pygame.font.SysFont(font_families, 18, bold=True)
        self.header_desc_font = pygame.font.SysFont(font_families, 13)
        self.nav_font = pygame.font.SysFont(font_families, 15, bold=True)
        self.badge_font = pygame.font.SysFont(font_families, 13, bold=True)
        self.header_font = pygame.font.SysFont(font_families, 14, bold=True)

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
        self.active_dialog: Optional[Any] = None
        self.hint_renderer = HintRenderer()

        # Network monitoring & action screenshot annotator
        self.student_client = StudentClient()
        self.action_annotator = ActionAnnotator()
        self.student_data: Dict[str, Any] = {}
        self.is_network_exam: bool = False
        self.last_heartbeat_time: float = 0.0
        self.exam_start_time: float = 0.0
        self._prev_wrong_actions: int = 0

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
            "На весь экран",
            callback=self.toggle_fullscreen,
            font_size=13,
            bg_color=(45, 60, 75),
            border_radius=6
        )
        self.btn_sim_fullscreen = UIButton(
            pygame.Rect(SCREEN_WIDTH - 60, 4, 46, 28),
            "[ ]",
            callback=self.toggle_fullscreen,
            font_size=14,
            bg_color=(40, 52, 65),
            border_radius=4
        )

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        pygame.display.toggle_fullscreen()
        self.btn_fullscreen.text = "В окно" if self.is_fullscreen else "На весь экран"

    def _build_main_menu_buttons(self):
        header_w = 1000
        header_x = (SCREEN_WIDTH - header_w) // 2
        btn_w, btn_h = 470, 78
        btn_x = header_x
        btn_y = 230
        gap = 18

        def load_btn_plates(norm_path, hov_path):
            try:
                norm_img = pygame.image.load(str(norm_path)).convert_alpha()
                hov_img = pygame.image.load(str(hov_path)).convert_alpha()
                return norm_img, hov_img
            except Exception:
                return None, None

        img_train_n, img_train_h = load_btn_plates(Assets.UI_BTN_TRAINING_NORM, Assets.UI_BTN_TRAINING_HOV)
        img_exam_n, img_exam_h = load_btn_plates(Assets.UI_BTN_EXAM_NORM, Assets.UI_BTN_EXAM_HOV)
        img_info_n, img_info_h = load_btn_plates(Assets.UI_BTN_INFO_NORM, Assets.UI_BTN_INFO_HOV)
        img_exit_n, img_exit_h = load_btn_plates(Assets.UI_BTN_EXIT_NORM, Assets.UI_BTN_EXIT_HOV)

        self.menu_buttons = [
            MenuCardButton(
                pygame.Rect(btn_x, btn_y, btn_w, btn_h),
                title="ОБУЧЕНИЕ",
                subtitle="Пошаговый тренажер с подсказками по органам управления",
                callback=lambda: self._open_device_selection(ApplicationMode.TRAINING),
                accent_color=(14, 165, 233),
                border_radius=8,
                img_normal=img_train_n,
                img_hover=img_train_h
            ),
            MenuCardButton(
                pygame.Rect(btn_x, btn_y + (btn_h + gap), btn_w, btn_h),
                title="ЭКЗАМЕН",
                subtitle="Сдача практического норматива и сетевой аудит",
                callback=self._open_exam_auth_dialog,
                accent_color=(245, 158, 11),
                border_radius=8,
                img_normal=img_exam_n,
                img_hover=img_exam_h
            ),
            MenuCardButton(
                pygame.Rect(btn_x, btn_y + 2 * (btn_h + gap), btn_w, btn_h),
                title="ИНФОРМАЦИЯ",
                subtitle="Методическое описание станций и регламентов работы",
                callback=self._show_info_dialog,
                accent_color=(99, 102, 241),
                border_radius=8,
                img_normal=img_info_n,
                img_hover=img_info_h
            ),
            MenuCardButton(
                pygame.Rect(btn_x, btn_y + 3 * (btn_h + gap), btn_w, btn_h),
                title="ВЫХОД",
                subtitle="Завершение работы программы",
                callback=self.quit,
                accent_color=(239, 68, 68),
                border_radius=8,
                img_normal=img_exit_n,
                img_hover=img_exit_h
            )
        ]

    def _open_exam_auth_dialog(self):
        self.active_dialog = StudentAuthDialog(
            on_confirm=self._on_auth_confirmed,
            on_cancel=lambda: setattr(self, 'active_dialog', None),
            client=self.student_client
        )

    def _on_auth_confirmed(self, student_data: Dict[str, Any], client: StudentClient):
        self.student_data = student_data
        self.student_client = client
        self.active_dialog = None
        self._open_device_selection(ApplicationMode.EXAMINE)

    def _show_info_dialog(self):
        msg = (
            "Vkm.ComplexSim — Комплексный симулятор устройств РЭБ и РЛС\n\n"
            "Программа предназначена для обучения и проверки знаний курсантов\n"
            "по приборам и комплексам радиоэлектронной борьбы и радиолокации:\n"
            "  * Станция активных помех ЛО01 'Смальта' (блоки П, Р, И, К)\n"
            "  * Импульсная РЛС ОНЦ (пульты управления, круговой радар, генератор Г5-15, осциллограф С1-65)\n\n"
            "В режиме 'Обучение' работает адаптивная 3-уровневая система подсказок:\n"
            "  1) Общая задача/цель действия без прямой подсказки\n"
            "  2) При неверном действии подсказка уточняется (блок/тип органа)\n"
            "  3) Если действие вызывает затруднения — переход к прямой подсветке и указанию стрелкой.\n"
            "Горячие клавиши: F1 — уточнить подсказку, Пробел — следующий шаг в инфо-подсказках, F11 — полный экран."
        )
        self.active_dialog = ModalDialog(
            "О программе",
            msg,
            [("Закрыть", lambda: setattr(self, 'active_dialog', None), (60, 75, 90))],
            width=720,
            height=410,
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
        # Пересоздаем изделие заново, чтобы исключить остаточные положения тумблеров предыдущего курсанта
        if dev_key == "smalta":
            self.devices_catalog["smalta"] = create_smalta_device()
        elif dev_key == "rls":
            self.devices_catalog["rls"] = create_rls_device()

        device = self.devices_catalog[dev_key]
        algos = self.algorithms_catalog[dev_key]

        if len(algos) == 1:
            if self.mode == ApplicationMode.EXAMINE:
                self._prepare_examine_session(device, algos[0])
            else:
                self.start_simulation(device, algos[0])
            return

        def choose_algo(algo):
            self.active_dialog = None
            if self.mode == ApplicationMode.EXAMINE:
                self._prepare_examine_session(device, algo)
            else:
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

    def _prepare_examine_session(self, device: DeviceBase, algo):
        total_steps = len([a for a in algo.actions if a.use_in_examine_check and a.name != ActionName.INFO])
        logged_in = self.student_client.login_sync(
            full_name=self.student_data.get("full_name", "Курсант"),
            group=self.student_data.get("group", "401"),
            pc_name=self.student_data.get("pc_name", socket.gethostname() if hasattr(socket, 'gethostname') else "ПК"),
            device_name=device.readable_name,
            algorithm_name=algo.name,
            max_time_seconds=600.0,
            total_steps=total_steps
        )
        if logged_in:
            self.is_network_exam = True
            # Запускаем фоновый поток клиента для своевременного получения команд от сервера
            self.student_client.start()

            if self.student_client.is_exam_started_by_server:
                self.start_simulation(device, algo)
            else:
                def on_start_offline():
                    self.active_dialog = None
                    self.start_simulation(device, algo)

                def on_cancel_wait():
                    self.active_dialog = None
                    self.student_client.stop()
                    self.state = AppState.MAIN_MENU

                self.active_dialog = WaitingForTeacherDialog(
                    self.student_data,
                    device.readable_name,
                    algo.name,
                    on_start_now=on_start_offline,
                    on_cancel=on_cancel_wait
                )
                self._pending_device = device
                self._pending_algo = algo

                def handle_cmd(cmd_type, payload):
                    self.student_client.incoming_commands.put((cmd_type, payload))

                self.student_client.on_command_callback = handle_cmd
        else:
            self.is_network_exam = False
            self.start_simulation(device, algo)

    def _on_device_action_recorded(self, action_name, element_name):
        if self.mode != ApplicationMode.EXAMINE or not self.active_device or not self.active_device.current_algorithm:
            return

        tracker = getattr(self.active_device, 'step_tracker', None)
        if not tracker:
            return

        res = getattr(self.active_device.history_service, 'last_action_result', None)
        if not res:
            el = self.active_device.get_element_by_name(element_name)
            val = el.value if el else 0
            res = tracker.on_action(action_name, element_name, val)

        # Синхронизируем индекс с hint_service для корректности HUD
        hs = self.active_device.hint_service
        hs.current_action_index = tracker.current_step_idx

        if not self.is_network_exam:
            return

        expected_action = tracker.get_current_expected_action()
        cur_step_idx = tracker.current_step_idx
        total_steps = tracker.total_steps

        # 1. Аннотированный снимок экрана с BBox ошибочного (красный) и нужного (зеленый) органа
        if res.is_mistake:
            try:
                jpeg = self.action_annotator.capture_action_snapshot(
                    screen_surface=self.screen,
                    is_mistake=True,
                    clicked_element_name=element_name,
                    device=self.active_device,
                    current_step_idx=cur_step_idx,
                    total_steps=total_steps,
                    expected_action=expected_action
                )
                if jpeg:
                    self.student_client.send_screenshot(jpeg)
            except Exception:
                pass

        # 2. Формируем подробную запись в журнал преподавателя
        hint_txt = expected_action.hint_text if expected_action else ""
        expected_name = expected_action.parent_element_name if expected_action else "—"

        event_type = EventType.MISTAKE if res.is_mistake else EventType.ACTION
        self.student_client.send_event(
            event_type,
            res.message,
            details={
                "step": cur_step_idx + 1 if cur_step_idx < total_steps else total_steps,
                "total_steps": total_steps,
                "completed_steps": res.completed_steps,
                "max_reached_step": res.max_reached_step_idx,
                "clicked_element": element_name,
                "expected_element": expected_name,
                "hint_context": hint_txt,
                "is_mistake": res.is_mistake,
                "is_revert": res.is_revert,
                "is_restoration": res.is_restoration,
                "broken_step_idx": res.broken_step_idx
            },
            is_mistake=res.is_mistake
        )

    def start_simulation(self, device: DeviceBase, algorithm):
        self.active_device = device
        self.is_god_mode = False
        self.entered_keys.clear()
        self._prev_wrong_actions = 0
        self._last_wrong_element = None
        device.apply_algorithm(algorithm)
        device.hint_service.start_training(algorithm, device)

        if self.mode == ApplicationMode.TRAINING:
            pass
        else:
            for el in device.elements:
                el.is_enabled = True
                el.is_hint_open = False
            self.exam_start_time = time.time()
            self.last_heartbeat_time = time.time()
            self._prev_wrong_actions = 0
            self._last_wrong_element = None
            device.history_service.on_action_callback = self._on_device_action_recorded
            if self.is_network_exam:
                self.student_client.send_event(
                    EventType.INFO,
                    f"Экзамен начат по заданию: '{algorithm.name}'"
                )

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
        }
        title = f"Результат: {grade_names.get(score, str(score))}"

        if self.is_network_exam:
            wrong_cnt = 0 if self.is_god_mode else res.get("wrong_actions", 0)
            self.student_client.send_event(
                EventType.FINISH,
                f"Экзамен завершен. Оценка: {score}. Ошибок: {wrong_cnt}",
                details={"score": score, "wrong_actions": wrong_cnt}
            )
            self.is_network_exam = False
            self.student_client.stop()

        def exit_to_menu():
            self.active_dialog = None
            self.state = AppState.MAIN_MENU
            # Полный сброс каталога изделий для следующего курсанта
            self.devices_catalog = {
                "smalta": create_smalta_device(),
                "rls": create_rls_device(),
            }
            self.active_device = None

        if self.mode == ApplicationMode.EXAMINE:
            # На экзамене кнопка 'Повторить' не имеет смысла
            buttons = [
                ("В главное меню", exit_to_menu, (30, 130, 80)),
            ]
        else:
            def retry():
                self.active_dialog = None
                self.start_simulation(self.active_device, self.active_device.current_algorithm)

            buttons = [
                ("Повторить", retry, (45, 110, 160)),
                ("В главное меню", exit_to_menu, (70, 80, 90)),
            ]
        self.active_dialog = ModalDialog(title, details_str, buttons, width=560, height=280, layout="row")

    def _force_terminate_by_teacher(self):
        """
        Принудительное завершение экзамена преподавателем:
        - Мгновенно закрывает любые диалоговые окна (без вопроса подтверждения)
        - Рассчитывает и сохраняет текущий прогресс и отправляет итоговый отчет на сервер
        - Останавливает сетевой клиент и аудит (прекращает запись в журнал)
        - Выводит окно с результатом и единственной кнопкой 'В главное меню'
        """
        self.active_dialog = None

        score = 0
        details_str = ""
        res = None
        if self.active_device and self.active_device.current_algorithm:
            if self.is_god_mode:
                score = 5
                details_str = "Активирован специальный режим отличника (GodMode)!\nОценка: 5 (Отлично)\nОшибок: 0"
            else:
                res = self.active_device.history_service.calculate_score(self.active_device.current_algorithm)
                score = res["score"]
                pct_ethalon = res.get("pct_ethalon", 0.0)
                pct_order = res.get("pct_order", 0.0)
                wrong_actions = res.get("wrong_actions", 0)
                details_str = (
                    f"Итоговая оценка: {score} из 5\n"
                    f"Выполнено эталонных действий: {int(pct_ethalon * 100)}%\n"
                    f"Правильный порядок: {int(pct_order * 100)}%\n"
                    f"Ошибочных действий: {wrong_actions}"
                )

        if self.is_network_exam and self.student_client:
            wrong_cnt = 0 if self.is_god_mode else (res.get("wrong_actions", 0) if res else 0)
            try:
                self.student_client.send_event(
                    EventType.FINISH,
                    f"Экзамен принудительно остановлен преподавателем. Оценка: {score}. Ошибок: {wrong_cnt}",
                    details={
                        "score": score,
                        "wrong_actions": wrong_cnt,
                        "forced_by_teacher": True
                    }
                )
            except Exception:
                pass

        # Полная остановка сетевого клиента и аудита
        self.is_network_exam = False
        if self.student_client:
            try:
                self.student_client.stop()
            except Exception:
                pass

        def exit_to_menu():
            self.active_dialog = None
            self.state = AppState.MAIN_MENU
            self.devices_catalog = {
                "smalta": create_smalta_device(),
                "rls": create_rls_device(),
            }
            self.active_device = None

        if self.state != AppState.SIMULATION or not self.active_device:
            exit_to_menu()
            return

        grade_names = {
            5: "ОТЛИЧНО (5)",
            4: "ХОРОШО (4)",
            3: "УДОВЛЕТВОРИТЕЛЬНО (3)",
            2: "НЕУДОВЛЕТВОРИТЕЛЬНО (2)",
        }
        title = f"Экзамен остановлен преподавателем: {grade_names.get(score, str(score))}"
        msg = "Экзамен был принудительно завершен преподавателем.\nТекущий прогресс и оценка сохранены в ведомость.\n\n" + details_str
        buttons = [
            ("В главное меню", exit_to_menu, (30, 130, 80)),
        ]
        self.active_dialog = ModalDialog(title, msg, buttons, width=580, height=290, layout="row")

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

            # Обработка команд от преподавателя в главном потоке Pygame
            if self.student_client:
                while not self.student_client.incoming_commands.empty():
                    try:
                        cmd_type, payload = self.student_client.incoming_commands.get_nowait()
                        if cmd_type == "START_EXAM":
                            if isinstance(self.active_dialog, WaitingForTeacherDialog):
                                self.active_dialog = None
                                if hasattr(self, '_pending_device') and hasattr(self, '_pending_algo') and self._pending_device and self._pending_algo:
                                    self.start_simulation(self._pending_device, self._pending_algo)
                        elif cmd_type == "STOP_EXAM":
                            self._force_terminate_by_teacher()
                    except Exception:
                        pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.student_client:
                        self.student_client.stop()
                    self.quit()

                # Fullscreen hotkeys: F11 or Alt+Enter
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                        self.toggle_fullscreen()
                        continue

                    # Cheat key listener
                    self._check_cheat_code(event.key)

                    # F1 or H escalates hint level in training mode
                    if event.key in (pygame.K_F1, pygame.K_h) and self.active_device and self.active_device.hint_service:
                        if self.mode == ApplicationMode.TRAINING:
                            self.active_device.hint_service.escalate_hint()
                    
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

                    # Training Hint HUD interactive elements (e.g. Help button click / hover)
                    if self.mode == ApplicationMode.TRAINING and self.active_device:
                        if self.hint_renderer.handle_event(event, self.active_device):
                            continue

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
                tracker = getattr(self.active_device, 'step_tracker', None)
                if tracker:
                    tracker.check_idle_advancement()
                self._update_navbar_buttons_state()

                # Telemetry Update
                now = time.time()
                if self.mode == ApplicationMode.EXAMINE and self.is_network_exam:
                    # Heartbeat every 1.5s
                    if now - self.last_heartbeat_time >= 1.5 and self.active_device.current_algorithm:
                        self.last_heartbeat_time = now
                        score_data = tracker.get_score() if tracker else self.active_device.history_service.calculate_score(self.active_device.current_algorithm)
                        total_steps = score_data.get("total_steps", 0)
                        pct = score_data.get("pct_ethalon", 0.0)
                        completed = score_data.get("completed_steps", int(pct * total_steps))
                        mistakes = score_data.get("wrong_actions", 0)
                        elapsed = now - self.exam_start_time
                        self.student_client.queue_heartbeat(
                            progress_pct=pct,
                            completed_steps=completed,
                            mistakes_count=mistakes,
                            elapsed_sec=elapsed,
                            score=score_data.get("score")
                        )

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

        header_w, header_h = 1000, 140
        header_x = (SCREEN_WIDTH - header_w) // 2
        header_y = 60

        # Header Card (Top Center)
        if self.header_plate:
            self.screen.blit(self.header_plate, (header_x, header_y))
        else:
            header_surf = pygame.Surface((header_w, header_h), pygame.SRCALPHA)
            header_surf.fill((15, 23, 42, 220))
            pygame.draw.rect(header_surf, (30, 41, 59), (0, 0, header_w, header_h), width=1, border_radius=12)
            pygame.draw.line(header_surf, (14, 165, 233), (20, 0), (header_w - 20, 0), 2)

            t_main = self.title_font.render("VKM.COMPLEXSIM", True, (248, 250, 252))
            t_sub = self.subtitle_font.render("Комплексный учебно-тренировочный симулятор устройств РЭБ и радиолокации", True, (56, 189, 248))
            t_desc = self.header_desc_font.render("Отработка практических регламентов по станциям ЛО01 «Смальта» и РЛС ОНЦ", True, (148, 163, 184))

            header_surf.blit(t_main, (35, 20))
            header_surf.blit(t_sub, (35, 66))
            header_surf.blit(t_desc, (35, 96))

            badges = [("[ v2.2.0 ]", (148, 163, 184)), ("[ СЕТЕВОЙ МОНИТОРИНГ ]", (148, 163, 184)), ("[ ГОТОВ ]", (52, 211, 153))]
            bx = header_w - 35
            for badge_text, badge_col in badges:
                b_surf = self.badge_font.render(badge_text, True, badge_col)
                bx -= (b_surf.get_width() + 12)
                header_surf.blit(b_surf, (bx, 28))

            self.screen.blit(header_surf, (header_x, header_y))

        # Buttons (Left Column)
        for b in self.menu_buttons:
            b.draw(self.screen)

        # Right Column: Overview Panel
        btn_w, btn_h = 470, 78
        gap = 18
        panel_x = header_x + btn_w + 30
        panel_y = 230
        panel_w = header_w - btn_w - 30
        panel_h = (btn_h + gap) * 4 - gap

        if self.devices_panel_plate:
            self.screen.blit(self.devices_panel_plate, (panel_x, panel_y))
        else:
            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel_surf.fill((15, 23, 42, 220))
            pygame.draw.rect(panel_surf, (30, 41, 59), (0, 0, panel_w, panel_h), width=1, border_radius=10)

            p_title = self.subtitle_font.render("Доступные изделия тренажера", True, (241, 245, 249))
            panel_surf.blit(p_title, (25, 20))

            devs = [
                ("Станция помех ЛО01 «Смальта»",
                 "Вертолетная станция активных помех РЭБ.\nПульты ЛО01-П, передатчик ЛО01-Р, блок ЛО01-И/К.",
                 (14, 165, 233)),
                ("РЛС ОНЦ",
                 "Радиолокационная станция обнаружения надводных целей.\nГенератор Г5-15, осциллограф С1-65, радарный экран.",
                 (56, 189, 248)),
            ]

            for didx, (dname, ddesc, dcol) in enumerate(devs):
                dy = 65 + didx * 140
                dcard = pygame.Surface((panel_w - 50, 120), pygame.SRCALPHA)
                dcard.fill((10, 15, 28, 180))
                pygame.draw.rect(dcard, (30, 41, 59), (0, 0, panel_w - 50, 120), width=1, border_radius=6)
                pygame.draw.rect(dcard, dcol, (0, 0, 4, 120), border_top_left_radius=6, border_bottom_left_radius=6)

                dt = self.nav_font.render(dname, True, (241, 245, 249))
                dcard.blit(dt, (18, 12))

                for l_idx, line in enumerate(ddesc.split("\n")):
                    dcard.blit(self.header_desc_font.render(line, True, (148, 163, 184)), (18, 42 + l_idx * 22))

                panel_surf.blit(dcard, (25, dy))

            self.screen.blit(panel_surf, (panel_x, panel_y))

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

            # Mode badge & Network indicator
            mode_color = COLOR_SUCCESS if self.mode == ApplicationMode.TRAINING else COLOR_WARNING
            badge_surf = self.badge_font.render(f"[ {self.mode.value.upper()} ]", True, mode_color)
            self.screen.blit(badge_surf, (SCREEN_WIDTH - 200, 9))

            if self.mode == ApplicationMode.EXAMINE:
                net_str = "[ СЕТЬ: ДА ]" if self.is_network_exam else "[ АВТОНОМНО ]"
                net_col = (52, 211, 153) if self.is_network_exam else (156, 163, 175)
                net_surf = self.badge_font.render(net_str, True, net_col)
                self.screen.blit(net_surf, (SCREEN_WIDTH - 330, 9))


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
