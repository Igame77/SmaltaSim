import os
import pygame
import pytest

# Initialize pygame headless for automated testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1600, 870))

from config import CANVAS_WIDTH, CANVAS_HEIGHT, Assets
from devices.smalta import create_smalta_device, get_smalta_algorithms, SmaltaPage
from devices.rls_onc import create_rls_device, get_rls_algorithms, RlsPage
from core.algorithm_service import HistoryService, Action, ActionName, Algorithm

def test_assets_exist():
    assert Assets.BG_MAIN.exists(), "Missing BG_MAIN"
    assert Assets.SMALTA_LO01P.exists(), "Missing SMALTA_LO01P"
    assert Assets.SMALTA_LO01R.exists(), "Missing SMALTA_LO01R"
    assert Assets.SMALTA_LO01I_LO01K.exists(), "Missing SMALTA_LO01I_LO01K"
    assert Assets.RLS_STATION.exists(), "Missing RLS_STATION"
    assert Assets.RLS_CPS.exists(), "Missing RLS_CPS"
    assert Assets.RLS_G5_15.exists(), "Missing RLS_G5_15"
    assert Assets.RLS_RADAR.exists(), "Missing RLS_RADAR"
    assert Assets.RLS_C1_65.exists(), "Missing RLS_C1_65"
    assert Assets.THUMBLER_ON.exists(), "Missing THUMBLER_ON"
    assert Assets.BIG_BUTTON_ON.exists(), "Missing BIG_BUTTON_ON"
    assert Assets.LAMP_ON.exists(), "Missing LAMP_ON"
    assert Assets.STEP_WHEEL.exists(), "Missing STEP_WHEEL"
    assert Assets.TROLL_FACE.exists(), "Missing TROLL_FACE"

def test_smalta_device_creation():
    dev = create_smalta_device()
    assert dev.name == "LO01_Smalta"
    assert len(dev.pages) == 3
    assert len(dev.elements) >= 30

    # Test key elements presence
    assert dev.get_element_by_name("lo01p_thumbler_1channel") is not None
    assert dev.get_element_by_name("lo01p_button_reciever_glow_on") is not None
    assert dev.get_element_by_name("lo01p_reciever_1channel_arrow") is not None
    assert dev.get_element_by_name("lo01r_lamp_heating") is not None
    assert dev.get_element_by_name("lo01i_thumbler_2generator") is not None

    # Test backgrounds
    for page in dev.pages:
        assert page in dev.page_backgrounds
        surf = dev.page_backgrounds[page]
        assert surf.get_size() == (CANVAS_WIDTH, CANVAS_HEIGHT)

def test_rls_onc_device_creation():
    dev = create_rls_device()
    assert dev.name == "RLS_ONC"
    assert len(dev.pages) == 5
    assert len(dev.elements) >= 15

    # Test key elements presence
    assert dev.get_element_by_name("station_thumbler_speed") is not None
    assert dev.get_element_by_name("cps_wheel_noise") is not None
    assert dev.get_element_by_name("cps_wheel_signal_noise") is not None
    assert dev.get_element_by_name("radar_target_1") is not None
    assert dev.get_element_by_name("radar_noise") is not None
    assert dev.get_element_by_name("c165_oscilloscope") is not None

def test_dependency_actions_smalta():
    dev = create_smalta_device()
    th_sim = dev.get_element_by_name("lo01p_thumbler_simulator")
    lt_sim = dev.get_element_by_name("lo01p_simulator")

    assert th_sim is not None and lt_sim is not None
    th_sim.set_value(0)
    assert lt_sim.value == 0

    th_sim.set_value(1)
    assert lt_sim.value == 1

def test_dependency_actions_rls():
    dev = create_rls_device()
    wheel_noise = dev.get_element_by_name("cps_wheel_noise")
    radar_noise = dev.get_element_by_name("radar_noise")

    assert wheel_noise is not None and radar_noise is not None
    wheel_noise.set_value(0)
    assert radar_noise.value == 0

    wheel_noise.set_value(50)
    assert radar_noise.value == 100

def test_algorithms_integrity():
    smalta_algos = get_smalta_algorithms()
    assert len(smalta_algos) == 3
    assert smalta_algos[0].name == "Подготовка изделия ЛО01 к включению"
    assert smalta_algos[1].name == "Включение изделия ЛО01"
    assert smalta_algos[2].name == "Выключение изделия ЛО01"

    rls_algos = get_rls_algorithms()
    assert len(rls_algos) == 1
    assert "коэффициента подавления" in rls_algos[0].name

def test_history_scoring_math():
    history = HistoryService()
    algo = Algorithm("Test", {}, {}, [
        Action(ActionName.CLICK, "el_1", use_in_examine_check=True),
        Action(ActionName.CLICK, "el_2", use_in_examine_check=True),
        Action(ActionName.CLICK, "el_3", use_in_examine_check=True),
    ])

    # 1. Perfect sequence
    history.record_click("el_1")
    history.record_click("el_2")
    history.record_click("el_3")
    res = history.calculate_score(algo)
    assert res["score"] == 5
    assert res["wrong_actions"] == 0

    # 2. Sequence with wrong clicks
    history.reset()
    history.record_click("el_1")
    history.record_click("wrong_element")
    history.record_click("another_wrong")
    history.record_click("el_2")
    history.record_click("el_3")
    res = history.calculate_score(algo)
    # 5 - 2 wrong = 3
    assert res["score"] == 3
    assert res["wrong_actions"] == 2

def test_training_mode_step_advancing():
    dev = create_smalta_device()
    algos = get_smalta_algorithms()
    algo = algos[0]  # Подготовка к включению

    dev.hint_service.start_training(algo, dev)
    assert not dev.hint_service.is_training_complete
    first_action = dev.hint_service.get_current_action()
    assert first_action is not None
    assert first_action.parent_element_name == "lo01p_thumbler_light"

    # Only first element should be enabled
    el = dev.get_element_by_name("lo01p_thumbler_light")
    assert el.is_enabled
    assert el.is_hint_open

    # Simulate interacting with it
    el.set_value(1)
    dev.hint_service.on_element_interacted("lo01p_thumbler_light", 1)

    # Next action should be second step
    second_action = dev.hint_service.get_current_action()
    assert second_action is not None
    assert second_action.parent_element_name == "lo01p_thumbler_1channel"

def test_full_prep_algorithm_execution():
    dev = create_smalta_device()
    algo = get_smalta_algorithms()[0]
    dev.apply_algorithm(algo)

    # Perform all actions in exact sequence
    for action in algo.actions:
        el = dev.get_element_by_name(action.parent_element_name)
        assert el is not None
        dev.history_service.record_click(action.parent_element_name)
        if action.expected_value is not None:
            el.set_value(action.expected_value)

    res = dev.history_service.calculate_score(algo)
    assert res["score"] == 5
    assert res["wrong_actions"] == 0
    assert res["pct_ethalon"] == 1.0
    assert res["pct_order"] == 1.0

