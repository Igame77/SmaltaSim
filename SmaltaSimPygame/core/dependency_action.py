from enum import Enum, auto
from typing import Dict, Optional, Callable, Any
from core.timer_service import TimerService

class DependencyType(Enum):
    REPLACE = auto()
    ADD = auto()
    COEFFICIENT_REPLACE = auto()
    COEFFICIENT_ADD = auto()

class DependencyAction:
    def __init__(
        self,
        dep_type: DependencyType,
        target_element_name: str,
        dependency_values: Optional[Dict[int, int]] = None,
        dependency_coefficient: Optional[int] = None,
        delayed_time_seconds: int = 0
    ):
        self.dep_type = dep_type
        self.target_element_name = target_element_name
        self.dependency_values = dependency_values or {}
        self.dependency_coefficient = dependency_coefficient
        self.delayed_time_seconds = delayed_time_seconds
        self.is_cancelled = False

    def execute(self, source_value: int, element_lookup: Callable[[str], Any], callback: Optional[Callable[[str], None]] = None):
        if self.is_cancelled:
            return

        def apply():
            if self.is_cancelled:
                return
            target = element_lookup(self.target_element_name)
            if target is None:
                return

            if self.dep_type == DependencyType.REPLACE:
                if source_value in self.dependency_values:
                    target.set_value(self.dependency_values[source_value])
            elif self.dep_type == DependencyType.ADD:
                if source_value in self.dependency_values:
                    target.set_value(target.value + self.dependency_values[source_value])
            elif self.dep_type == DependencyType.COEFFICIENT_REPLACE:
                if self.dependency_coefficient is not None:
                    target.set_value(source_value * self.dependency_coefficient)
            elif self.dep_type == DependencyType.COEFFICIENT_ADD:
                if self.dependency_coefficient is not None:
                    target.set_value(target.value + (source_value * self.dependency_coefficient))

            if callback:
                callback(self.target_element_name)

        if self.delayed_time_seconds > 0:
            TimerService.get_instance().schedule(self.delayed_time_seconds, apply, token=self)
        else:
            apply()

    def cancel(self):
        self.is_cancelled = True
        TimerService.get_instance().cancel_by_token(self)
