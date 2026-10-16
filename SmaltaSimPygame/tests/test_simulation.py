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

    # 3. Sequence with immediate revert: wrong click followed immediately by returning it
    history.reset()
    history.record_click("el_1")
    history.record_click("wrong_element")
    history.record_click("wrong_element")  # immediate revert
    history.record_click("el_2")
    history.record_click("el_3")
    res = history.calculate_score(algo)
    # 5 - 1 wrong (revert deduplicated) = 4
    assert res["score"] == 4
    assert res["wrong_actions"] == 1

def test_training_mode_step_advancing():
    dev = create_smalta_device()
    algos = get_smalta_algorithms()
    algo = algos[0]  # Подготовка к включению

    dev.hint_service.start_training(algo, dev)
    assert not dev.hint_service.is_training_complete
    first_action = dev.hint_service.get_current_action()
    assert first_action is not None
    assert first_action.parent_element_name == "lo01p_thumbler_light"

    # All elements are enabled in exploratory training mode
    el = dev.get_element_by_name("lo01p_thumbler_light")
    assert el.is_enabled

    # Simulate interacting with it correctly
    el.set_value(1)
    dev.hint_service.on_element_interacted("lo01p_thumbler_light", 1)

    # Next action should be second step
    second_action = dev.hint_service.get_current_action()
    assert second_action is not None
    assert second_action.parent_element_name == "lo01p_thumbler_1channel"

def test_training_mode_adaptive_hint_tiers():
    dev = create_smalta_device()
    algo = get_smalta_algorithms()[0]
    dev.hint_service.start_training(algo, dev)

    # 1. Level 1: Indirect hint initially
    assert dev.hint_service.hint_level == 1
    assert "Обеспечьте визуальный контроль" in dev.hint_service.get_current_hint_text()
    target_el = dev.get_element_by_name("lo01p_thumbler_light")
    assert not target_el.is_hint_open

    # 2. Mistake 1 -> Escalates to Level 2 (Clarifying)
    dev.hint_service.on_element_interacted("lo01p_thumbler_1channel", 1)
    assert dev.hint_service.hint_level == 2
    assert "Блок ЛО01П" in dev.hint_service.get_current_hint_text()
    assert not target_el.is_hint_open

    # 3. Mistake 2 -> Escalates to Level 3 (Direct hint with popup & glow)
    dev.hint_service.on_element_interacted("wrong_control", 1)
    assert dev.hint_service.hint_level == 3
    assert "Установите данный тумблер в положение ПОДСВЕТ" in dev.hint_service.get_current_hint_text()
    assert target_el.is_hint_open

    # 4. Correct interaction -> Advances to Step 2, resets hint_level to 1
    dev.hint_service.on_element_interacted("lo01p_thumbler_light", 1)
    assert dev.hint_service.current_action_index == 1
    assert dev.hint_service.hint_level == 1
    next_action = dev.hint_service.get_current_action()
    assert next_action.parent_element_name == "lo01p_thumbler_1channel"
    assert "Подготовьте первый" in dev.hint_service.get_current_hint_text()

def test_training_mode_manual_escalation():
    dev = create_smalta_device()
    algo = get_smalta_algorithms()[0]
    dev.hint_service.start_training(algo, dev)

    assert dev.hint_service.hint_level == 1
    # User doesn't know what to do -> presses F1 / requests help
    assert dev.hint_service.escalate_hint() is True
    assert dev.hint_service.hint_level == 2
    assert dev.hint_service.escalate_hint() is True
    assert dev.hint_service.hint_level == 3
    assert dev.hint_service.escalate_hint() is False  # Already at max level

def test_full_prep_algorithm_execution():
    dev = create_smalta_device()
    algo = get_smalta_algorithms()[0]
    dev.apply_algorithm(algo)

    # Perform all actions in exact sequence
    for action in algo.actions:
        el = dev.get_element_by_name(action.parent_element_name)
        assert el is not None
        if action.expected_value is not None:
            el.set_value(action.expected_value)
        dev.history_service.record_click(action.parent_element_name)

    res = dev.history_service.calculate_score(algo)
    assert res["score"] == 5
    assert res["wrong_actions"] == 0
    assert res["pct_ethalon"] == 1.0
    assert res["pct_order"] == 1.0

def test_out_of_order_action_counts_as_mistake():
    dev = create_smalta_device()
    algo = get_smalta_algorithms()[0]
    dev.apply_algorithm(algo)
    tracker = dev.step_tracker
    assert tracker is not None
    assert tracker.current_step_idx == 0

    # Expected step 0: lo01p_thumbler_light
    # Student clicks step 4 out-of-order: lo01p_thumbler_4channel
    el4 = dev.get_element_by_name("lo01p_thumbler_4channel")
    el4.set_value(1)
    res = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_4channel", 1)

    assert res.is_mistake is True
    assert tracker.wrong_actions_count == 1
    assert tracker.current_step_idx == 0  # Did not jump forward!

    # Immediate revert
    el4.set_value(0)
    res_revert = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_4channel", 0)
    assert res_revert.is_revert is True
    assert tracker.wrong_actions_count == 1  # Deduplicated!

def test_breaking_earlier_step_drops_progress_and_restores():
    dev = create_smalta_device()
    algo = get_smalta_algorithms()[0]
    dev.apply_algorithm(algo)
    tracker = dev.step_tracker
    assert tracker is not None

    # Complete first 5 steps (0..4)
    for i in range(5):
        act = tracker.examine_actions[i]
        el = dev.get_element_by_name(act.parent_element_name)
        el.set_value(act.expected_value)
        res = tracker.on_action(ActionName.CLICK, act.parent_element_name, act.expected_value)
        assert res.is_valid_step is True

    assert tracker.current_step_idx == 5
    assert tracker.max_reached_step_idx == 5
    assert tracker.wrong_actions_count == 0

    # Student returns to step 0 and turns off lo01p_thumbler_light (1 -> 0)
    el0 = dev.get_element_by_name("lo01p_thumbler_light")
    el0.set_value(0)
    res_break = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_light", 0)

    # Must be counted as an error and progress dropped to step 0!
    assert res_break.is_mistake is True
    assert tracker.wrong_actions_count == 1
    assert tracker.current_step_idx == 0
    assert tracker.max_reached_step_idx == 5

    # Student returns lo01p_thumbler_light back to 1
    el0.set_value(1)
    res_restore = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_light", 1)

    # Must be restored to step 5 without adding a new error!
    assert res_restore.is_mistake is False
    assert res_restore.is_restoration is True
    assert tracker.wrong_actions_count == 1
    assert tracker.current_step_idx == 5

def test_multiple_broken_steps_sequential_restoration():
    dev = create_smalta_device()
    algo = get_smalta_algorithms()[0]
    dev.apply_algorithm(algo)
    tracker = dev.step_tracker
    assert tracker is not None

    # Complete first 5 steps (0..4)
    for i in range(5):
        act = tracker.examine_actions[i]
        el = dev.get_element_by_name(act.parent_element_name)
        el.set_value(act.expected_value)
        tracker.on_action(ActionName.CLICK, act.parent_element_name, act.expected_value)

    assert tracker.current_step_idx == 5

    # Break step 2 (lo01p_thumbler_2channel -> 0)
    el2 = dev.get_element_by_name("lo01p_thumbler_2channel")
    el2.set_value(0)
    res1 = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_2channel", 0)
    assert res1.is_mistake is True
    assert tracker.current_step_idx == 2
    assert tracker.wrong_actions_count == 1

    # Break step 0 (lo01p_thumbler_light -> 0)
    el0 = dev.get_element_by_name("lo01p_thumbler_light")
    el0.set_value(0)
    res2 = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_light", 0)
    assert res2.is_mistake is True
    assert tracker.current_step_idx == 0
    assert tracker.wrong_actions_count == 2

    # Fix step 0 (lo01p_thumbler_light -> 1)
    el0.set_value(1)
    res3 = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_light", 1)
    assert res3.is_mistake is False
    # Step 0 is fixed, but step 2 is still broken!
    assert tracker.current_step_idx == 2
    assert tracker.wrong_actions_count == 2

    # Fix step 2 (lo01p_thumbler_2channel -> 1)
    el2.set_value(1)
    res4 = tracker.on_action(ActionName.CLICK, "lo01p_thumbler_2channel", 1)
    assert res4.is_mistake is False
    assert res4.is_restoration is True
    # All earlier steps are now restored! Returns to step 5!
    assert tracker.current_step_idx == 5
    assert tracker.wrong_actions_count == 2


