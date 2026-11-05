import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "core" / "algorithm_service.py"
spec = importlib.util.spec_from_file_location("algorithm_service_under_test", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HintService = module.HintService


def test_hint_level_badge_matches_current_level():
    service = HintService()
    assert service.get_hint_level_badge() == "УРОВЕНЬ 1: ЗАДАЧА"
    service.hint_level = 2
    assert service.get_hint_level_badge() == "УРОВЕНЬ 2: УТОЧНЕНИЕ"
    service.hint_level = 3
    assert service.get_hint_level_badge() == "УРОВЕНЬ 3: ПРЯМОЕ УКАЗАНИЕ"
