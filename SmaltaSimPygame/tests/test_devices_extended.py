import os
import pygame
import pytest

# Initialize headless pygame for testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1600, 870))

from config import CANVAS_WIDTH, CANVAS_HEIGHT, Assets
from devices.sorbtia import create_sorbtia_device, get_sorbtia_algorithms, SorbtiaPage
from devices.fasol import create_fasol_device, get_fasol_algorithms, FasolPage
from devices.bereza import create_bereza_device, get_bereza_algorithms, BerezaPage
from devices.azalia import create_azalia_device, get_azalia_algorithms, AzaliaPage
from core.algorithm_service import StepTracker, ActionName

def test_sorbtia_device_and_algorithms():
    dev = create_sorbtia_device()
    assert dev.name == "Sorbtia"
    assert len(dev.pages) == 5
    assert len(dev.elements) >= 15

    # Check key elements
    assert dev.get_element_by_name("kpa_thumbler_power") is not None
    assert dev.get_element_by_name("omega_thumbler_15") is not None
    assert dev.get_element_by_name("omega_thumbler_power") is not None
    assert dev.get_element_by_name("pnpv_thumbler_rtu") is not None
    assert dev.get_element_by_name("ubp_btn_on") is not None
    assert dev.get_element_by_name("pnpv_thumbler_emission") is not None

    # Check backgrounds
    for page in dev.pages:
        assert page in dev.page_backgrounds
        surf = dev.page_backgrounds[page]
        assert surf.get_size() == (CANVAS_WIDTH, CANVAS_HEIGHT)

    # Algorithms
    algos = get_sorbtia_algorithms()
    assert len(algos) >= 3
    a1 = algos[0]
    assert len(a1.actions) == 6
    # Each action must have 3 levels of hints
    for action in a1.actions:
        assert action.hint_text != ""
        assert action.hint_indirect != ""
        assert action.hint_clarify != ""

    # Test executing full algorithm on Sorbtia
    dev.reset_all_elements(a1)
    tracker = StepTracker(a1, dev)
    dev.step_tracker = tracker

    for action in a1.actions:
        el = dev.get_element_by_name(action.parent_element_name)
        el.set_value(action.expected_value)
        res = tracker.on_action(ActionName.CLICK, action.parent_element_name, action.expected_value)
        assert res.is_valid_step is True

    assert tracker.current_step_idx == tracker.total_steps
    score = tracker.get_score()
    assert score["pct_ethalon"] == 1.0


def test_fasol_device_and_algorithms():
    dev = create_fasol_device()
    assert dev.name == "Fasol"
    assert len(dev.pages) == 4
    assert len(dev.elements) >= 12

    assert dev.get_element_by_name("fasol_pu_thumbler_power") is not None
    assert dev.get_element_by_name("fasol_pu_thumbler_heating") is not None
    assert dev.get_element_by_name("fasol_pu_switch_subband") is not None
    assert dev.get_element_by_name("fasol_pu_thumbler_high_voltage") is not None
    assert dev.get_element_by_name("fasol_b2_switch_load") is not None
    assert dev.get_element_by_name("fasol_c460_thumbler_power") is not None

    algos = get_fasol_algorithms()
    assert len(algos) >= 3
    a1 = algos[0]
    assert len(a1.actions) == 6

    # Execute algorithm
    dev.reset_all_elements(a1)
    tracker = StepTracker(a1, dev)
    dev.step_tracker = tracker

    for action in a1.actions:
        el = dev.get_element_by_name(action.parent_element_name)
        el.set_value(action.expected_value)
        res = tracker.on_action(ActionName.CLICK, action.parent_element_name, action.expected_value)
        assert res.is_valid_step is True

    assert tracker.current_step_idx == tracker.total_steps
    score = tracker.get_score()
    assert score["pct_ethalon"] == 1.0


def test_bereza_device_and_algorithms():
    dev = create_bereza_device()
    assert dev.name == "Bereza"
    assert len(dev.pages) == 2
    assert len(dev.elements) >= 12

    assert dev.get_element_by_name("bereza_lamp_azimuth_0") is not None
    assert dev.get_element_by_name("bereza_lamp_type_p") is not None
    assert dev.get_element_by_name("bereza_thumbler_power") is not None
    assert dev.get_element_by_name("bereza_btn_test") is not None

    algos = get_bereza_algorithms()
    assert len(algos) >= 2
    a1 = algos[0]
    assert len(a1.actions) == 3


def test_azalia_device_and_algorithms():
    dev = create_azalia_device()
    assert dev.name == "Azalia"
    assert len(dev.pages) == 2
    assert len(dev.elements) >= 8

    assert dev.get_element_by_name("azalia_thumbler_power") is not None
    assert dev.get_element_by_name("azalia_thumbler_heat") is not None
    assert dev.get_element_by_name("azalia_thumbler_high") is not None
    assert dev.get_element_by_name("azalia_switch_freq") is not None

    algos = get_azalia_algorithms()
    assert len(algos) >= 1
    a1 = algos[0]
    assert len(a1.actions) == 4
