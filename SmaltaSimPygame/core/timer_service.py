import pygame
from typing import Callable, List, Optional, Any

class ScheduledTask:
    def __init__(self, execute_at_ms: int, callback: Callable[[], Any], token: Any = None):
        self.execute_at_ms = execute_at_ms
        self.callback = callback
        self.token = token
        self.is_cancelled = False

class TimerService:
    _instance: Optional['TimerService'] = None

    def __init__(self):
        self.tasks: List[ScheduledTask] = []

    @classmethod
    def get_instance(cls) -> 'TimerService':
        if cls._instance is None:
            cls._instance = TimerService()
        return cls._instance

    def schedule(self, delay_seconds: float, callback: Callable[[], Any], token: Any = None) -> ScheduledTask:
        current_time = pygame.time.get_ticks()
        execute_at = current_time + int(delay_seconds * 1000)
        task = ScheduledTask(execute_at, callback, token)
        self.tasks.append(task)
        return task

    def cancel_by_token(self, token: Any):
        if token is None:
            return
        for task in self.tasks:
            if task.token == token:
                task.is_cancelled = True

    def update(self):
        current_time = pygame.time.get_ticks()
        ready_tasks = [t for t in self.tasks if not t.is_cancelled and t.execute_at_ms <= current_time]
        self.tasks = [t for t in self.tasks if not t.is_cancelled and t.execute_at_ms > current_time]

        for task in ready_tasks:
            task.callback()

    def reset(self):
        self.tasks.clear()
