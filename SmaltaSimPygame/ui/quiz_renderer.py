import pygame
from typing import Optional, Callable, Dict, Any, List
from core.quiz_engine import QuizSession, QuizResult
from config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER

class QuizRenderer:
    def __init__(
        self,
        session: QuizSession,
        on_finish: Optional[Callable[[QuizResult], None]] = None,
        on_exit: Optional[Callable[[], None]] = None
    ):
        self.session = session
        self.on_finish = on_finish
        self.on_exit = on_exit

        self.font_title = pygame.font.SysFont("Segoe UI", 26, bold=True)
        self.font_subtitle = pygame.font.SysFont("Segoe UI", 18)
        self.font_question = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.font_option = pygame.font.SysFont("Segoe UI", 18)
        self.font_badge = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_grade = pygame.font.SysFont("Segoe UI", 48, bold=True)

        self.option_rects: List[pygame.Rect] = []
        self.hovered_option: Optional[int] = None
        self.result: Optional[QuizResult] = None

        self.btn_prev_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_next_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_exit_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_retry_rect = pygame.Rect(0, 0, 0, 0)

        self.network_status_msg: str = "Готов к передаче результатов"

    def set_network_status(self, msg: str):
        self.network_status_msg = msg

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            self.hovered_option = None
            for idx, r in enumerate(self.option_rects):
                if r.collidepoint(mouse_pos):
                    self.hovered_option = idx
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            if not self.session.is_finished:
                # Option clicks
                for idx, r in enumerate(self.option_rects):
                    if r.collidepoint(mouse_pos):
                        self.session.select_answer(idx)
                        return

                # Prev button
                if self.btn_prev_rect.collidepoint(mouse_pos):
                    self.session.prev_question()
                    return

                # Next / Finish button
                if self.btn_next_rect.collidepoint(mouse_pos):
                    if self.session.current_idx == self.session.total_questions - 1:
                        self._finish_and_evaluate()
                    else:
                        self.session.next_question()
                    return

                # Exit button
                if self.btn_exit_rect.collidepoint(mouse_pos):
                    if self.on_exit:
                        self.on_exit()
                    return

            else:
                # On results screen
                if self.btn_retry_rect.collidepoint(mouse_pos):
                    # Restart test
                    self.session = QuizSession(self.session.test_id, self.session.student_info)
                    self.result = None
                    return

                if self.btn_exit_rect.collidepoint(mouse_pos):
                    if self.on_exit:
                        self.on_exit()
                    return

        elif event.type == pygame.KEYDOWN:
            if not self.session.is_finished:
                # Keys 1..4 to select answer
                if event.key in [pygame.K_1, pygame.K_KP1]:
                    self.session.select_answer(0)
                elif event.key in [pygame.K_2, pygame.K_KP2]:
                    self.session.select_answer(1)
                elif event.key in [pygame.K_3, pygame.K_KP3]:
                    self.session.select_answer(2)
                elif event.key in [pygame.K_4, pygame.K_KP4]:
                    self.session.select_answer(3)
                elif event.key in [pygame.K_RIGHT, pygame.K_SPACE, pygame.K_RETURN]:
                    if self.session.current_idx == self.session.total_questions - 1:
                        self._finish_and_evaluate()
                    else:
                        self.session.next_question()
                elif event.key == pygame.K_LEFT:
                    self.session.prev_question()
                elif event.key == pygame.K_ESCAPE:
                    if self.on_exit:
                        self.on_exit()

    def _finish_and_evaluate(self):
        self.result = self.session.finish_quiz()
        if self.on_finish:
            self.on_finish(self.result)

    def draw(self, surface: pygame.Surface):
        # Draw background
        surface.fill((20, 24, 28))

        if not self.session.is_finished:
            self._draw_question_view(surface)
        else:
            self._draw_results_view(surface)

    def _draw_question_view(self, surface: pygame.Surface):
        q = self.session.current_question
        if not q:
            return

        w, h = surface.get_width(), surface.get_height()
        box_w = min(1100, w - 80)
        box_x = (w - box_w) // 2

        # ---------------- HEADER ----------------
        top_y = 30
        title_surf = self.font_title.render(self.session.test_title, True, (240, 245, 250))
        surface.blit(title_surf, (box_x, top_y))

        cadet_str = f"Курсант: {self.session.student_info.get('name', '—')} | Взвод: {self.session.student_info.get('group', '—')} | Вар: {self.session.student_info.get('variant', '1')}"
        info_surf = self.font_subtitle.render(cadet_str, True, (150, 165, 180))
        surface.blit(info_surf, (box_x, top_y + 35))

        # Progress bar
        curr = self.session.current_idx + 1
        total = self.session.total_questions
        progress_text = f"Вопрос {curr} из {total}"
        prog_surf = self.font_badge.render(progress_text, True, COLOR_ACCENT)
        surface.blit(prog_surf, (box_x + box_w - prog_surf.get_width(), top_y + 10))

        bar_rect = pygame.Rect(box_x, top_y + 68, box_w, 8)
        pygame.draw.rect(surface, (40, 50, 60), bar_rect, border_radius=4)
        fill_w = int(box_w * (curr / total))
        pygame.draw.rect(surface, COLOR_ACCENT, pygame.Rect(box_x, top_y + 68, fill_w, 8), border_radius=4)

        # ---------------- QUESTION CARD ----------------
        card_y = top_y + 95
        card_h = 140
        card_rect = pygame.Rect(box_x, card_y, box_w, card_h)
        pygame.draw.rect(surface, (28, 36, 44), card_rect, border_radius=10)
        pygame.draw.rect(surface, (55, 75, 95), card_rect, width=2, border_radius=10)

        # Category badge
        cat_badge = self.font_badge.render(f"[{q.category}: {q.topic}]", True, (130, 195, 255))
        surface.blit(cat_badge, (box_x + 20, card_y + 15))

        # Question text wrapped
        self._draw_wrapped_text(surface, q.text, self.font_question, (245, 250, 255), box_x + 20, card_y + 45, box_w - 40)

        # ---------------- 4 OPTION CARDS ----------------
        self.option_rects.clear()
        options_start_y = card_y + card_h + 20
        opt_h = 70
        opt_gap = 14
        letter_badges = ["А", "Б", "В", "Г"]
        selected_idx = self.session.get_selected_answer()

        for idx, opt_text in enumerate(q.options):
            opt_y = options_start_y + idx * (opt_h + opt_gap)
            r = pygame.Rect(box_x, opt_y, box_w, opt_h)
            self.option_rects.append(r)

            is_selected = (selected_idx == idx)
            is_hovered = (self.hovered_option == idx)

            if is_selected:
                bg_color = (18, 55, 80)
                border_color = COLOR_ACCENT
                text_color = (255, 255, 255)
            elif is_hovered:
                bg_color = (36, 46, 56)
                border_color = (80, 110, 140)
                text_color = (240, 245, 250)
            else:
                bg_color = (26, 33, 40)
                border_color = (48, 62, 75)
                text_color = (210, 220, 230)

            pygame.draw.rect(surface, bg_color, r, border_radius=8)
            pygame.draw.rect(surface, border_color, r, width=2, border_radius=8)

            # Option letter badge circle
            badge_rect = pygame.Rect(box_x + 18, opt_y + 15, 40, 40)
            badge_bg = COLOR_ACCENT if is_selected else (45, 58, 70)
            pygame.draw.rect(surface, badge_bg, badge_rect, border_radius=6)
            b_text = self.font_badge.render(f"{letter_badges[idx]} ({idx+1})", True, (255, 255, 255))
            surface.blit(b_text, b_text.get_rect(center=badge_rect.center))

            # Option text wrapped
            self._draw_wrapped_text(surface, opt_text, self.font_option, text_color, box_x + 72, opt_y + 14, box_w - 90)

        # ---------------- BOTTOM CONTROLS ----------------
        btn_y = options_start_y + 4 * (opt_h + opt_gap) + 20
        btn_w, btn_h_nav = 180, 50

        # Exit / Back
        self.btn_exit_rect = pygame.Rect(box_x, btn_y, 160, btn_h_nav)
        pygame.draw.rect(surface, (60, 45, 45), self.btn_exit_rect, border_radius=8)
        pygame.draw.rect(surface, (120, 60, 60), self.btn_exit_rect, width=2, border_radius=8)
        lbl_exit = self.font_subtitle.render("В меню", True, (240, 210, 210))
        surface.blit(lbl_exit, lbl_exit.get_rect(center=self.btn_exit_rect.center))

        # Prev
        self.btn_prev_rect = pygame.Rect(box_x + box_w - 380, btn_y, btn_w, btn_h_nav)
        prev_color = (40, 50, 60) if self.session.current_idx > 0 else (28, 34, 40)
        pygame.draw.rect(surface, prev_color, self.btn_prev_rect, border_radius=8)
        pygame.draw.rect(surface, (65, 80, 95), self.btn_prev_rect, width=2, border_radius=8)
        lbl_prev = self.font_subtitle.render("← Предыдущий", True, (200, 210, 220))
        surface.blit(lbl_prev, lbl_prev.get_rect(center=self.btn_prev_rect.center))

        # Next / Finish
        self.btn_next_rect = pygame.Rect(box_x + box_w - 180, btn_y, btn_w, btn_h_nav)
        is_last = (self.session.current_idx == self.session.total_questions - 1)
        next_bg = (30, 120, 70) if is_last else (16, 120, 180)
        pygame.draw.rect(surface, next_bg, self.btn_next_rect, border_radius=8)
        pygame.draw.rect(surface, (100, 200, 150) if is_last else (60, 180, 240), self.btn_next_rect, width=2, border_radius=8)
        lbl_next_str = "Завершить тест" if is_last else "Следующий →"
        lbl_next = self.font_subtitle.render(lbl_next_str, True, (255, 255, 255))
        surface.blit(lbl_next, lbl_next.get_rect(center=self.btn_next_rect.center))

    def _draw_results_view(self, surface: pygame.Surface):
        if not self.result:
            return

        w, h = surface.get_width(), surface.get_height()
        box_w = min(1000, w - 80)
        box_x = (w - box_w) // 2
        res_y = 60

        # Card container
        container_rect = pygame.Rect(box_x, res_y, box_w, 680)
        pygame.draw.rect(surface, (26, 33, 40), container_rect, border_radius=12)
        pygame.draw.rect(surface, (55, 70, 85), container_rect, width=2, border_radius=12)

        # Title
        t_surf = self.font_title.render("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ЗНАНИЙ", True, (245, 250, 255))
        surface.blit(t_surf, t_surf.get_rect(center=(w // 2, res_y + 40)))

        sub_surf = self.font_subtitle.render(self.result.test_title, True, COLOR_ACCENT)
        surface.blit(sub_surf, sub_surf.get_rect(center=(w // 2, res_y + 75)))

        # Big Grade Box
        grade_colors = {
            5: COLOR_SUCCESS,
            4: (56, 189, 248),
            3: COLOR_WARNING,
            2: COLOR_DANGER
        }
        g_color = grade_colors.get(self.result.grade, COLOR_WARNING)

        grade_box = pygame.Rect(w // 2 - 120, res_y + 115, 240, 130)
        pygame.draw.rect(surface, (18, 24, 30), grade_box, border_radius=10)
        pygame.draw.rect(surface, g_color, grade_box, width=3, border_radius=10)

        g_val = self.font_grade.render(str(self.result.grade), True, g_color)
        surface.blit(g_val, g_val.get_rect(center=(w // 2, res_y + 155)))

        g_txt = self.font_subtitle.render(f"Оценка: «{self.result.grade_text}»", True, g_color)
        surface.blit(g_txt, g_txt.get_rect(center=(w // 2, res_y + 215)))

        # Metrics Row
        stats_y = res_y + 270
        metrics = [
            f"Правильных ответов: {self.result.correct_answers} из {self.result.total_questions}",
            f"Успешность: {self.result.score_percent}%",
            f"Время: {self.result.time_spent_seconds // 60:02d}:{self.result.time_spent_seconds % 60:02d}"
        ]
        m_combined = "   |   ".join(metrics)
        m_surf = self.font_subtitle.render(m_combined, True, (220, 230, 240))
        surface.blit(m_surf, m_surf.get_rect(center=(w // 2, stats_y)))

        # Network transmission status badge
        net_rect = pygame.Rect(box_x + 40, stats_y + 35, box_w - 80, 40)
        pygame.draw.rect(surface, (20, 32, 28), net_rect, border_radius=6)
        pygame.draw.rect(surface, (30, 120, 80), net_rect, width=1, border_radius=6)
        net_surf = self.font_badge.render(f"СЕТЕВОЙ АУДИТ: {self.network_status_msg}", True, (90, 230, 150))
        surface.blit(net_surf, net_surf.get_rect(center=net_rect.center))

        # Review list of questions (compact scroll/table)
        rev_y = stats_y + 90
        rev_h = 200
        rev_rect = pygame.Rect(box_x + 40, rev_y, box_w - 80, rev_h)
        pygame.draw.rect(surface, (20, 25, 30), rev_rect, border_radius=8)
        pygame.draw.rect(surface, (45, 55, 65), rev_rect, width=1, border_radius=8)

        # Draw questions summary rows
        item_y = rev_y + 12
        for idx, item in enumerate(self.result.answers_detail[:5]):
            icon = "✓" if item["is_correct"] else "✗"
            icon_color = COLOR_SUCCESS if item["is_correct"] else COLOR_DANGER
            row_text = f"{icon} Вопрос {idx+1}: {item['text'][:70]}..."
            row_surf = self.font_subtitle.render(row_text, True, icon_color if not item["is_correct"] else (200, 215, 225))
            surface.blit(row_surf, (box_x + 55, item_y))
            item_y += 36

        # Action Buttons
        btn_row_y = res_y + 600
        btn_w = 220
        self.btn_retry_rect = pygame.Rect(w // 2 - btn_w - 15, btn_row_y, btn_w, 52)
        pygame.draw.rect(surface, (30, 100, 160), self.btn_retry_rect, border_radius=8)
        pygame.draw.rect(surface, (80, 160, 230), self.btn_retry_rect, width=2, border_radius=8)
        lbl_retry = self.font_subtitle.render("Пройти заново", True, (255, 255, 255))
        surface.blit(lbl_retry, lbl_retry.get_rect(center=self.btn_retry_rect.center))

        self.btn_exit_rect = pygame.Rect(w // 2 + 15, btn_row_y, btn_w, 52)
        pygame.draw.rect(surface, (50, 60, 70), self.btn_exit_rect, border_radius=8)
        pygame.draw.rect(surface, (90, 105, 120), self.btn_exit_rect, width=2, border_radius=8)
        lbl_exit = self.font_subtitle.render("Главное меню", True, (240, 245, 250))
        surface.blit(lbl_exit, lbl_exit.get_rect(center=self.btn_exit_rect.center))

    def _draw_wrapped_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font, color: tuple, x: int, y: int, max_width: int):
        words = text.split(" ")
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        line_h = font.get_linesize()
        for idx, line in enumerate(lines[:3]):  # Max 3 lines
            surf = font.render(line, True, color)
            surface.blit(surf, (x, y + idx * line_h))
