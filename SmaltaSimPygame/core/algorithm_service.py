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
        use_in_examine_check: bool = True
    ):
        self.name = name
        self.parent_element_name = parent_element_name
        self.hint_text = hint_text
        self.expected_value = expected_value
        self.use_in_examine_check = use_in_examine_check
        self.is_completed = False

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

    def record_click(self, element_name: str):
        self.actions.append((ActionName.CLICK, element_name))

    def record_idle(self, element_name: str):
        self.actions.append((ActionName.IDLE, element_name))

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

            if not action_is_right and user_action_name == ActionName.CLICK:
                wrong_actions_count += 1

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

    def start_training(self, algorithm: Algorithm, device: Any):
        self.algorithm = algorithm
        self.device = device
        self.current_action_index = 0
        self.is_training_complete = False

        # Disable all elements first
        for el in self.device.elements:
            el.is_enabled = False
            el.is_hint_open = False

        self._apply_current_hint()

    def get_current_action(self) -> Optional[Action]:
        if not self.algorithm or self.current_action_index >= len(self.algorithm.actions):
            return None
        return self.algorithm.actions[self.current_action_index]

    def _apply_current_hint(self):
        action = self.get_current_action()
        if not action:
            self.is_training_complete = True
            return

        target = self.device.get_element_by_name(action.parent_element_name)
        if target:
            target.is_enabled = True
            target.is_hint_open = True
            target.hint_text = action.hint_text

    def on_element_interacted(self, element_name: str, new_value: int):
        action = self.get_current_action()
        if not action or action.parent_element_name != element_name:
            return

        if action.name == ActionName.CLICK:
            if action.expected_value is None or action.expected_value == new_value:
                self.advance()
        elif action.name == ActionName.INFO:
            self.advance()

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
                target.is_enabled = False

        self.current_action_index += 1
        if self.current_action_index >= len(self.algorithm.actions):
            self.is_training_complete = True
            # Re-enable elements
            for el in self.device.elements:
                el.is_enabled = True
        else:
            self._apply_current_hint()

    def reset(self):
        self.algorithm = None
        self.current_action_index = -1
        self.is_training_complete = False
