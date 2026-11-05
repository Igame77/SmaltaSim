import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

# Ensure headless pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1600, 870))

from core.vsp_manager import VspManager, get_solution_root
from ui.ui_widgets import ModalDialog, UIButton

def test_vsp_root_resolution():
    root = get_solution_root()
    assert root.exists(), f"Root does not exist: {root}"
    assert (root / "ВСП01").exists(), "Missing ВСП01 directory"
    assert (root / "ВСП02").exists(), "Missing ВСП02 directory"
    assert (root / "ВСП03").exists(), "Missing ВСП03 directory"

def test_vsp_manager_simulators_catalog():
    mgr = VspManager()
    expected_sims = ["fasol", "sorbtia", "azalia", "bereza"]
    for sim_id in expected_sims:
        assert sim_id in mgr.simulators, f"Simulator {sim_id} missing from catalog"
        sim = mgr.simulators[sim_id]
        assert "name" in sim
        assert "rel_path" in sim
        assert "kind" in sim
        assert mgr.exists(sim["rel_path"]), f"File for {sim_id} missing on disk: {sim['rel_path']}"
        assert mgr.exists(sim["linked_test"]), f"Linked test for {sim_id} missing: {sim['linked_test']}"

def test_vsp_manager_tests_catalog():
    mgr = VspManager()
    assert "vsp01" in mgr.tests_by_discipline
    assert "vsp02" in mgr.tests_by_discipline
    assert "vsp03" in mgr.tests_by_discipline

    vsp01 = mgr.tests_by_discipline["vsp01"]["items"]
    vsp02 = mgr.tests_by_discipline["vsp02"]["items"]
    vsp03 = mgr.tests_by_discipline["vsp03"]["items"]

    assert len(vsp01) == 7, f"Expected 7 tests in ВСП.01, got {len(vsp01)}"
    assert len(vsp02) == 11, f"Expected 11 tests in ВСП.02, got {len(vsp02)}"
    assert len(vsp03) == 9, f"Expected 9 tests in ВСП.03, got {len(vsp03)}"

    total = len(vsp01) + len(vsp02) + len(vsp03)
    assert total == 27, f"Expected 27 total tests, got {total}"

    for cat_key, cat_data in mgr.tests_by_discipline.items():
        for test_item in cat_data["items"]:
            assert "title" in test_item
            assert "rel" in test_item
            assert mgr.exists(test_item["rel"]), f"Test file missing: {test_item['rel']}"

def test_vsp_manager_launch_simulator():
    mgr = VspManager()
    # Test HTML interactive launcher
    with patch("webbrowser.open") as mock_web:
        ok, msg = mgr.launch_simulator("sorbtia")
        assert ok
        assert mock_web.called

    # Test Standalone EXE launcher
    with patch("subprocess.Popen") as mock_popen:
        ok, msg = mgr.launch_simulator("fasol")
        assert ok
        assert mock_popen.called

        ok, msg = mgr.launch_simulator("azalia")
        assert ok

        ok, msg = mgr.launch_simulator("bereza")
        assert ok

    # Test unknown simulator
    ok, msg = mgr.launch_simulator("non_existent_sim")
    assert not ok
    assert "Неизвестный" in msg

def test_vsp_manager_launch_test():
    mgr = VspManager()
    test_rel = mgr.tests_by_discipline["vsp01"]["items"][0]["rel"]
    with patch("subprocess.Popen") as mock_popen:
        ok, msg = mgr.launch_test(test_rel)
        assert ok
        assert mock_popen.called

    ok, msg = mgr.launch_test("invalid/path/test.exe")
    assert not ok
    assert "не найден" in msg

def test_modal_dialog_grid_layout():
    buttons = [
        ("Тест 1", lambda: None, (30, 40, 50)),
        ("Тест 2", lambda: None, (30, 40, 50)),
        ("Тест 3", lambda: None, (30, 40, 50)),
        ("Тест 4", lambda: None, (30, 40, 50)),
        ("Отмена", lambda: None, (70, 80, 90)),
    ]
    dlg = ModalDialog("Заголовок", "Сообщение для курсантов", buttons, layout="grid")
    assert dlg.is_open
    assert len(dlg.ui_buttons) == 5

    # Odd last button spans full width
    b_last = dlg.ui_buttons[-1]
    assert b_last.rect.width > dlg.ui_buttons[0].rect.width

    surface = pygame.Surface((1600, 870))
    dlg.draw(surface)

