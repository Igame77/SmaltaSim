from enum import Enum, auto
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass

class ActionName(Enum):
    CLICK = auto()
    IDLE = auto()
    INFO = auto()

class Action:
    def __init__(
        self,
        name: ActionName,
        parent_element_name: str,
        hint_text: str = "",
        expected_value: Optional[int] = None,
        use_in_examine_check: bool = True,
        hint_indirect: str = "",
        hint_clarify: str = ""
    ):
        self.name = name
        self.parent_element_name = parent_element_name
        self.hint_text = hint_text  # Level 3: direct hint (старая прямая подсказка)
        self.expected_value = expected_value
        if name == ActionName.INFO:
            self.use_in_examine_check = False
        else:
            self.use_in_examine_check = use_in_examine_check
        self.is_completed = False
        self.hint_indirect = hint_indirect or hint_text  # Level 1: "запустите систему..."
        self.hint_clarify = hint_clarify or hint_text    # Level 2: уточняющая подсказка

class Algorithm:
    def __init__(
        self,
        name: str,
        start_state_of_elements: Optional[Dict[str, int]] = None,
        end_state_of_elements: Optional[Dict[str, int]] = None,
        actions: Optional[List[Action]] = None
    ):
        self.name = name
        self.start_state_of_elements = start_state_of_elements or {}
        self.end_state_of_elements = end_state_of_elements or {}
        self.actions = actions or []

@dataclass
class StepActionResult:
    is_valid_step: bool
    is_mistake: bool
    is_revert: bool
    is_restoration: bool
    broken_step_idx: Optional[int]
    current_step_idx: int
    completed_steps: int
    max_reached_step_idx: int
    total_steps: int
    progress_pct: float
    message: str


class StepTracker:
    def __init__(self, algorithm: Algorithm, device: Optional[Any] = None):
        self.algorithm = algorithm
        self.device = device

        self.examine_actions: List[Action] = [
            a for a in algorithm.actions
            if a.use_in_examine_check and a.name != ActionName.INFO
        ]
        self.total_steps: int = len(self.examine_actions)

        self.current_step_idx: int = 0
        self.max_reached_step_idx: int = 0
        self.wrong_actions_count: int = 0

        self.last_wrong_element: Optional[str] = None
        self.is_last_action_revert: bool = False

        self._simulated_values: Dict[str, int] = dict(algorithm.start_state_of_elements)

    def reset(self):
        self.current_step_idx = 0
        self.max_reached_step_idx = 0
        self.wrong_actions_count = 0
        self.last_wrong_element = None
        self.is_last_action_revert = False
        self._simulated_values = dict(self.algorithm.start_state_of_elements)

    def get_element_value(self, element_name: str) -> int:
        if self.device:
            el = self.device.get_element_by_name(element_name)
            if el is not None:
                return el.value
        return self._simulated_values.get(element_name, 0)

    def get_current_expected_action(self) -> Optional[Action]:
        if 0 <= self.current_step_idx < self.total_steps:
            return self.examine_actions[self.current_step_idx]
        return None

    def get_required_states_up_to(self, step_count: int) -> Dict[str, int]:
        required = {}
        limit = min(step_count, self.total_steps)
        for i in range(limit):
            act = self.examine_actions[i]
            if act.expected_value is not None:
                required[act.parent_element_name] = act.expected_value
        return required

    def find_lowest_broken_step(self) -> Optional[int]:
        if self.max_reached_step_idx <= 0:
            return None

        required_states = self.get_required_states_up_to(self.max_reached_step_idx)
        for i in range(self.max_reached_step_idx):
            act = self.examine_actions[i]
            if act.expected_value is not None:
                req_val = required_states.get(act.parent_element_name)
                curr_val = self.get_element_value(act.parent_element_name)
                if req_val is not None and curr_val != req_val:
                    return i
        return None

    def check_idle_advancement(self) -> List[Action]:
        advanced = []
        while self.current_step_idx < self.total_steps:
            act = self.examine_actions[self.current_step_idx]
            if act.name == ActionName.IDLE:
                curr_val = self.get_element_value(act.parent_element_name)
                if act.expected_value is None or curr_val == act.expected_value:
                    self.current_step_idx += 1
                    self.max_reached_step_idx = max(self.max_reached_step_idx, self.current_step_idx)
                    advanced.append(act)
                    continue
            break
        return advanced

    def on_action(
        self,
        action_name: ActionName,
        element_name: str,
        new_value: Optional[int] = None
    ) -> StepActionResult:
        if new_value is not None:
            self._simulated_values[element_name] = new_value
        elif self.device:
            new_value = self.get_element_value(element_name)
        else:
            prev_val = self._simulated_values.get(element_name, 0)
            new_val = 1 if prev_val == 0 else 0
            self._simulated_values[element_name] = new_val
            new_value = new_val

        if self.total_steps == 0:
            return StepActionResult(
                is_valid_step=True,
                is_mistake=False,
                is_revert=False,
                is_restoration=False,
                broken_step_idx=None,
                current_step_idx=0,
                completed_steps=0,
                max_reached_step_idx=0,
                total_steps=0,
                progress_pct=1.0,
                message="Нет эталонных шагов для проверки"
            )

        was_broken_before = (self.current_step_idx < self.max_reached_step_idx)
        lowest_broken = self.find_lowest_broken_step()

        # 1. Если нарушен один из ранее завершенных этапов
        if lowest_broken is not None:
            if not was_broken_before:
                # Курсант сбил положение тумблера с ранее пройденного этапа
                self.wrong_actions_count += 1
                self.current_step_idx = lowest_broken
                self.last_wrong_element = element_name
                self.is_last_action_revert = False
                broken_step_num = lowest_broken + 1
                return StepActionResult(
                    is_valid_step=False,
                    is_mistake=True,
                    is_revert=False,
                    is_restoration=False,
                    broken_step_idx=lowest_broken,
                    current_step_idx=self.current_step_idx,
                    completed_steps=self.current_step_idx,
                    max_reached_step_idx=self.max_reached_step_idx,
                    total_steps=self.total_steps,
                    progress_pct=self.current_step_idx / self.total_steps,
                    message=f"ОШИБКА: нарушено методическое положение органа '{element_name}' с этапа {broken_step_num}. Прогресс сброшен до шага {broken_step_num}."
                )
            else:
                if lowest_broken > self.current_step_idx:
                    # Курсант восстановил текущий нарушенный орган, но остался еще один сбитый выше
                    self.current_step_idx = lowest_broken
                    self.last_wrong_element = None
                    self.is_last_action_revert = False
                    return StepActionResult(
                        is_valid_step=True,
                        is_mistake=False,
                        is_revert=False,
                        is_restoration=True,
                        broken_step_idx=lowest_broken,
                        current_step_idx=self.current_step_idx,
                        completed_steps=self.current_step_idx,
                        max_reached_step_idx=self.max_reached_step_idx,
                        total_steps=self.total_steps,
                        progress_pct=self.current_step_idx / self.total_steps,
                        message=f"Орган '{element_name}' возвращен в норму. Требуется восстановить шаг {lowest_broken + 1}."
                    )
                elif lowest_broken < self.current_step_idx:
                    # Курсант сбил еще более ранний орган управления
                    self.wrong_actions_count += 1
                    self.current_step_idx = lowest_broken
                    self.last_wrong_element = element_name
                    self.is_last_action_revert = False
                    return StepActionResult(
                        is_valid_step=False,
                        is_mistake=True,
                        is_revert=False,
                        is_restoration=False,
                        broken_step_idx=lowest_broken,
                        current_step_idx=self.current_step_idx,
                        completed_steps=self.current_step_idx,
                        max_reached_step_idx=self.max_reached_step_idx,
                        total_steps=self.total_steps,
                        progress_pct=self.current_step_idx / self.total_steps,
                        message=f"ОШИБКА: дополнительно нарушен шаг {lowest_broken + 1} ('{element_name}')."
                    )
                else:
                    # Все еще сбит на том же шаге
                    if self.last_wrong_element == element_name and not self.is_last_action_revert:
                        self.is_last_action_revert = True
                        self.last_wrong_element = None
                        return StepActionResult(
                            is_valid_step=False,
                            is_mistake=False,
                            is_revert=True,
                            is_restoration=False,
                            broken_step_idx=lowest_broken,
                            current_step_idx=self.current_step_idx,
                            completed_steps=self.current_step_idx,
                            max_reached_step_idx=self.max_reached_step_idx,
                            total_steps=self.total_steps,
                            progress_pct=self.current_step_idx / self.total_steps,
                            message=f"Возврат органа управления '{element_name}' в исходное положение (ошибка не дублируется)"
                        )
                    else:
                        self.wrong_actions_count += 1
                        self.last_wrong_element = element_name
                        self.is_last_action_revert = False
                        exp_act = self.examine_actions[self.current_step_idx]
                        return StepActionResult(
                            is_valid_step=False,
                            is_mistake=True,
                            is_revert=False,
                            is_restoration=False,
                            broken_step_idx=lowest_broken,
                            current_step_idx=self.current_step_idx,
                            completed_steps=self.current_step_idx,
                            max_reached_step_idx=self.max_reached_step_idx,
                            total_steps=self.total_steps,
                            progress_pct=self.current_step_idx / self.total_steps,
                            message=f"ОШИБКА: нажато '{element_name}', требуется вернуть в правильное положение '{exp_act.parent_element_name}'."
                        )

        # 2. Если все ранее пройденные шаги восстановлены
        if was_broken_before:
            self.current_step_idx = self.max_reached_step_idx
            self.last_wrong_element = None
            self.is_last_action_revert = False
            self.check_idle_advancement()
            return StepActionResult(
                is_valid_step=True,
                is_mistake=False,
                is_revert=False,
                is_restoration=True,
                broken_step_idx=None,
                current_step_idx=self.current_step_idx,
                completed_steps=self.current_step_idx,
                max_reached_step_idx=self.max_reached_step_idx,
                total_steps=self.total_steps,
                progress_pct=self.current_step_idx / self.total_steps,
                message=f"Орган '{element_name}' возвращен в правильное положение. Прогресс восстановлен до шага {self.current_step_idx + 1}."
            )

        # 3. Штатный режим (current_step_idx == max_reached_step_idx)
        if self.current_step_idx >= self.total_steps:
            return StepActionResult(
                is_valid_step=False,
                is_mistake=False,
                is_revert=False,
                is_restoration=False,
                broken_step_idx=None,
                current_step_idx=self.total_steps,
                completed_steps=self.total_steps,
                max_reached_step_idx=self.total_steps,
                total_steps=self.total_steps,
                progress_pct=1.0,
                message=f"Действие '{element_name}' (все шаги задания уже выполнены)."
            )

        expected_act = self.examine_actions[self.current_step_idx]
        is_target_name = (expected_act.parent_element_name == element_name)
        is_target_val = (expected_act.expected_value is None or expected_act.expected_value == new_value)

        if is_target_name and is_target_val:
            self.current_step_idx += 1
            self.max_reached_step_idx = max(self.max_reached_step_idx, self.current_step_idx)
            self.last_wrong_element = None
            self.is_last_action_revert = False
            self.check_idle_advancement()
            return StepActionResult(
                is_valid_step=True,
                is_mistake=False,
                is_revert=False,
                is_restoration=False,
                broken_step_idx=None,
                current_step_idx=self.current_step_idx,
                completed_steps=self.current_step_idx,
                max_reached_step_idx=self.max_reached_step_idx,
                total_steps=self.total_steps,
                progress_pct=self.current_step_idx / self.total_steps,
                message=f"Выполнено действие (шаг {self.current_step_idx}/{self.total_steps}): '{element_name}'"
            )

        # Не совпало с текущим требуемым шагом
        # Проверяем немедленный откат ошибочного действия
        if self.last_wrong_element == element_name and not self.is_last_action_revert:
            self.is_last_action_revert = True
            self.last_wrong_element = None
            return StepActionResult(
                is_valid_step=False,
                is_mistake=False,
                is_revert=True,
                is_restoration=False,
                broken_step_idx=None,
                current_step_idx=self.current_step_idx,
                completed_steps=self.current_step_idx,
                max_reached_step_idx=self.max_reached_step_idx,
                total_steps=self.total_steps,
                progress_pct=self.current_step_idx / self.total_steps,
                message=f"Возврат органа управления '{element_name}' в исходное положение (ошибка не дублируется)"
            )

        # Ошибочное или внеочередное действие («в разнобой»)
        self.wrong_actions_count += 1
        self.last_wrong_element = element_name
        self.is_last_action_revert = False
        expected_name = expected_act.parent_element_name
        return StepActionResult(
            is_valid_step=False,
            is_mistake=True,
            is_revert=False,
            is_restoration=False,
            broken_step_idx=None,
            current_step_idx=self.current_step_idx,
            completed_steps=self.current_step_idx,
            max_reached_step_idx=self.max_reached_step_idx,
            total_steps=self.total_steps,
            progress_pct=self.current_step_idx / self.total_steps,
            message=f"ОШИБКА (шаг {self.current_step_idx + 1}/{self.total_steps}): нажато '{element_name}', требовалось '{expected_name}'"
        )

    def get_score(self) -> dict:
        completed = self.current_step_idx
        total = self.total_steps
        pct_ethalon = (completed / total) if total > 0 else 1.0
        pct_order = 1.0 if completed > 0 else 0.0
        wrong_cnt = self.wrong_actions_count
        raw_score = pct_ethalon * 5.0 - wrong_cnt
        score = max(1, min(5, int(round(raw_score))))
        return {
            "score": score,
            "raw_score": raw_score,
            "pct_ethalon": pct_ethalon,
            "pct_order": pct_order,
            "wrong_actions": wrong_cnt,
            "completed_steps": completed,
            "total_steps": total,
            "current_step_idx": self.current_step_idx,
            "max_reached_step_idx": self.max_reached_step_idx,
            "total_user_actions": self.wrong_actions_count + completed,
            "ethalon_count": total,
        }


class HistoryService:
    def __init__(self):
        self.actions: List[tuple[ActionName, str]] = []
        self.on_action_callback: Optional[Callable[[ActionName, str], None]] = None
        self.step_tracker: Optional[StepTracker] = None
        self.last_action_result: Optional[StepActionResult] = None

    def record_click(self, element_name: str):
        self.actions.append((ActionName.CLICK, element_name))
        if self.step_tracker:
            self.last_action_result = self.step_tracker.on_action(ActionName.CLICK, element_name)
        if self.on_action_callback:
            try:
                self.on_action_callback(ActionName.CLICK, element_name)
            except Exception:
                pass

    def record_idle(self, element_name: str):
        self.actions.append((ActionName.IDLE, element_name))
        if self.step_tracker:
            self.last_action_result = self.step_tracker.on_action(ActionName.IDLE, element_name)
        if self.on_action_callback:
            try:
                self.on_action_callback(ActionName.IDLE, element_name)
            except Exception:
                pass

    def reset(self):
        self.actions.clear()
        self.last_action_result = None
        if self.step_tracker:
            self.step_tracker.reset()

    def calculate_score(self, algorithm: Algorithm) -> dict:
        if self.step_tracker and self.step_tracker.algorithm == algorithm:
            return self.step_tracker.get_score()

        tracker = StepTracker(algorithm)
        for act_name, el_name in self.actions:
            tracker.on_action(act_name, el_name)
        return tracker.get_score()

class HintService:
    def __init__(self):
        self.algorithm: Optional[Algorithm] = None
        self.current_action_index = -1
        self.device = None
        self.is_training_complete = False
        self.hint_level: int = 1
        self.mistakes_on_step: int = 0
        self.total_training_mistakes: int = 0
        self.last_mistake_text: str = ""
        self.mistake_flash_until_ms: int = 0

    def start_training(self, algorithm: Algorithm, device: Any):
        self.algorithm = algorithm
        self.device = device
        self.current_action_index = 0
        self.is_training_complete = False
        self.hint_level = 1
        self.mistakes_on_step = 0
        self.total_training_mistakes = 0
        self.last_mistake_text = ""
        self.mistake_flash_until_ms = 0

        # Enable all elements for exploratory training
        for el in self.device.elements:
            el.is_enabled = True
            el.is_hint_open = False

        self._apply_current_hint()

    def get_current_action(self) -> Optional[Action]:
        if not self.algorithm or self.current_action_index < 0 or self.current_action_index >= len(self.algorithm.actions):
            return None
        return self.algorithm.actions[self.current_action_index]

    def get_current_hint_text(self) -> str:
        action = self.get_current_action()
        if not action:
            return ""
        if self.hint_level == 1:
            return action.hint_indirect
        elif self.hint_level == 2:
            return action.hint_clarify
        else:
            return action.hint_text

    def get_hint_level_badge(self) -> str:
        if self.hint_level == 1:
            return "УРОВЕНЬ 1: ЗАДАЧА"
        elif self.hint_level == 2:
            return "УРОВЕНЬ 2: УТОЧНЕНИЕ"
        else:
            return "УРОВЕНЬ 3: ПРЯМОЕ УКАЗАНИЕ"

    def escalate_hint(self) -> bool:
        """Manually escalate hint level when stuck ('не доходит' or F1 pressed)."""
        if self.hint_level < 3:
            self.hint_level += 1
            self._apply_current_hint()
            return True
        return False

    def on_element_interacted(self, element_name: str, new_value: int):
        action = self.get_current_action()
        if not action:
            return

        is_target = (action.parent_element_name == element_name)
        is_expected_val = (action.expected_value is None or action.expected_value == new_value)

        if is_target and is_expected_val:
            self.advance()
        else:
            # User answered incorrectly: escalate hint level
            self.on_mistake(element_name, new_value)

    def on_mistake(self, element_name: str, new_value: int):
        self.mistakes_on_step += 1
        self.total_training_mistakes += 1
        import pygame
        self.mistake_flash_until_ms = pygame.time.get_ticks() + 3500

        if self.hint_level == 1:
            self.hint_level = 2
            self.last_mistake_text = "Не тот орган управления! Подсказка уточнена:"
        elif self.hint_level == 2:
            self.hint_level = 3
            self.last_mistake_text = "Неверно! Включено прямое указание на орган управления:"
        else:
            self.last_mistake_text = "Внимание: следуйте указанию стрелки и подсветки:"

        self._apply_current_hint()

    def on_idle_completed(self, element_name: str, new_value: int):
        action = self.get_current_action()
        if not action or action.parent_element_name != element_name:
            return

        if action.name == ActionName.IDLE:
            if action.expected_value is None or action.expected_value == new_value:
                self.advance()

    def advance(self):
        action = self.get_current_action()
        if action:
            target = self.device.get_element_by_name(action.parent_element_name)
            if target:
                target.is_hint_open = False

        self.current_action_index += 1
        self.hint_level = 1
        self.mistakes_on_step = 0
        self.last_mistake_text = ""
        self.mistake_flash_until_ms = 0

        if self.current_action_index >= len(self.algorithm.actions):
            self.is_training_complete = True
            for el in self.device.elements:
                el.is_enabled = True
        else:
            self._apply_current_hint()

    def _apply_current_hint(self):
        action = self.get_current_action()
        if not action:
            self.is_training_complete = True
            return

        target = self.device.get_element_by_name(action.parent_element_name)
        if target:
            # Only Level 3 (or INFO steps) opens speech bubble and pinpoint frame on the control
            if self.hint_level == 3 or action.name == ActionName.INFO:
                target.is_hint_open = True
                target.hint_text = action.hint_text
            else:
                target.is_hint_open = False

    def reset(self):
        self.algorithm = None
        self.current_action_index = -1
        self.is_training_complete = False
        self.hint_level = 1
        self.mistakes_on_step = 0
        self.total_training_mistakes = 0
        self.last_mistake_text = ""
        self.mistake_flash_until_ms = 0
