from enum import Enum, auto
from typing import List, Dict, Optional, Callable, Any

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

class HistoryService:
    def __init__(self):
        self.actions: List[tuple[ActionName, str]] = []
        self.on_action_callback: Optional[Callable[[ActionName, str], None]] = None

    def record_click(self, element_name: str):
        self.actions.append((ActionName.CLICK, element_name))
        if self.on_action_callback:
            try:
                self.on_action_callback(ActionName.CLICK, element_name)
            except Exception:
                pass

    def record_idle(self, element_name: str):
        self.actions.append((ActionName.IDLE, element_name))
        if self.on_action_callback:
            try:
                self.on_action_callback(ActionName.IDLE, element_name)
            except Exception:
                pass

    def reset(self):
        self.actions.clear()

    def calculate_score(self, algorithm: Algorithm) -> dict:
        """
        Exact formula from ExamineResultProperties.cs and HistoryService.cs:
        PercentageOfEthalonActionsInUserActions = ethalonActionsInUserActionsCount / ethalonActionsCount
        PercentageOfEthalonActionsRightOrderInUserActions = rightOrderOfUserActionsCount / ethalonActionsInUserActionsCount
        Value = round(PercentageOfEthalon * PercentageOfRightOrder * 5 - WrongActionsCount)
        """
        ethalon_actions = [a for a in algorithm.actions if a.use_in_examine_check]
        ethalon_count = len(ethalon_actions)
        if ethalon_count == 0:
            return {"score": 5, "details": "Нет эталонных действий для проверки"}

        previous_right_action_index = 0
        ethalon_in_user_count = 0
        right_order_count = 0
        wrong_actions_count = 0
        last_wrong_element: Optional[str] = None
        is_revert = False

        for user_action_name, user_el_name in self.actions:
            action_is_right = False
            for j, ethalon_action in enumerate(algorithm.actions):
                if (
                    ethalon_action.name == user_action_name
                    and ethalon_action.parent_element_name == user_el_name
                    and ethalon_action.use_in_examine_check
                ):
                    ethalon_in_user_count += 1
                    action_is_right = True
                    if j >= previous_right_action_index:
                        previous_right_action_index = j
                        right_order_count += 1
                    break

            if action_is_right:
                last_wrong_element = None
                is_revert = False
            elif user_action_name == ActionName.CLICK:
                # Если курсант нажал не на тот элемент, но не совершал других действий
                # и сразу вернул его в исходное положение (повторное нажатие на тот же неверный элемент),
                # засчитывается только 1 ошибка, а не 2!
                if last_wrong_element == user_el_name and not is_revert:
                    is_revert = True
                else:
                    wrong_actions_count += 1
                    last_wrong_element = user_el_name
                    is_revert = False

        if ethalon_in_user_count > ethalon_count:
            ethalon_in_user_count = ethalon_count

        if right_order_count > ethalon_in_user_count:
            right_order_count = ethalon_in_user_count

        pct_ethalon = (ethalon_in_user_count / ethalon_count) if ethalon_count > 0 else 1.0
        pct_order = (right_order_count / ethalon_in_user_count) if ethalon_in_user_count > 0 else 0.0

        raw_score = pct_ethalon * pct_order * 5.0 - wrong_actions_count
        score = max(1, min(5, int(round(raw_score))))

        return {
            "score": score,
            "raw_score": raw_score,
            "pct_ethalon": pct_ethalon,
            "pct_order": pct_order,
            "wrong_actions": wrong_actions_count,
            "total_user_actions": len(self.actions),
            "ethalon_count": ethalon_count,
        }

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
