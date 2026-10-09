import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional

DEFAULT_SERVER_PORT = 8000
DEFAULT_DISCOVERY_PORT = 50505
DISCOVERY_MAGIC_REQUEST = "SMALTA_EXAM_DISCOVER"
DISCOVERY_MAGIC_RESPONSE = "SMALTA_EXAM_OFFER"

class StudentStatus(str, Enum):
    WAITING = "WAITING"           # Зарегистрирован, ожидает команды старта от преподавателя
    ACTIVE = "ACTIVE"             # Экзамен идет в штатном режиме
    FOCUS_LOST = "FOCUS_LOST"     # Окно свернуто или активно другое приложение
    FINISHED = "FINISHED"         # Студент завершил экзамен
    TIMEOUT = "TIMEOUT"           # Время вышло
    STOPPED = "STOPPED"           # Принудительно остановлен преподавателем

class EventType(str, Enum):
    INFO = "INFO"
    ACTION = "ACTION"
    MISTAKE = "MISTAKE"
    FOCUS_LOST = "FOCUS_LOST"
    FOCUS_GAINED = "FOCUS_GAINED"
    FINISH = "FINISH"
    COMMAND = "COMMAND"

def serialize_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)

def deserialize_json(raw: str) -> Any:
    return json.loads(raw)
