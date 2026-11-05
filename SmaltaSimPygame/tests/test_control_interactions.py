"""Regression tests for momentary push buttons and two-position toggles."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from controls.big_button import BigButton
from controls.thumbler import Thumbler
from core.element_base import ElementBase
from core.dependency_action import DependencyAction, DependencyType


class _History:
    def __init__(self):
        self.clicks = []

    def record_click(self, name):
        self.clicks.append(name)


class _Device:
    def __init__(self, elements):
        self.elements = {element.name: element for element in elements}
        self.history_service = _History()
        self.hint_service = None

    def get_element_by_name(self, name):
        return self.elements.get(name)


def test_big_button_returns_and_can_trigger_repeated_presses():
    pygame.init()
    try:
        pygame.display.set_mode((100, 100))
        target = ElementBase("target", 0, 0, None, value=0)
        button = BigButton(
            "test_button", 10, 10, page_key=None,
            dependency_actions=[DependencyAction(DependencyType.REPLACE, "target", {1: 1})],
        )
        device = _Device([target, button])
        target.device = device
        button.device = device

        for expected_click_count in (1, 2):
            if expected_click_count == 2:
                # Simulate the receiver becoming ready for the next command.
                target.value = 0
            assert button.handle_event(
                pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
            )
            assert button.value == 1
            assert button._is_pressed
            assert target.value == 1

            assert button.handle_event(
                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(90, 90))
            )
            assert button.value == 0
            assert not button._is_pressed
            assert len(device.history_service.clicks) == expected_click_count
    finally:
        pygame.quit()


def test_big_button_releases_on_focus_loss():
    pygame.init()
    try:
        pygame.display.set_mode((100, 100))
        button = BigButton("test_button", 10, 10, page_key=None)
        button.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
        )
        if hasattr(pygame, "WINDOWFOCUSLOST"):
            assert button.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
            assert button.value == 0
            assert not button._is_pressed
    finally:
        pygame.quit()


def test_thumbler_toggles_persistently_and_triggers_dependencies():
    pygame.init()
    try:
        pygame.display.set_mode((100, 100))
        target = ElementBase("target", 0, 0, None, value=0)
        switch = Thumbler(
            "test_thumbler", 10, 10, page_key=None, value=0,
            dependency_actions=[DependencyAction(DependencyType.REPLACE, "target", {0: 0, 1: 1})],
        )
        device = _Device([target, switch])
        target.device = device
        switch.device = device

        assert switch.rendered_off.get_size() == (25, 43)
        assert switch.rendered_on.get_size() == (25, 43)

        assert switch.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
        )
        assert switch.value == 1
        assert target.value == 1

        # The toggle keeps its state after the mouse is no longer held.
        assert switch.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(90, 90))
        ) is False
        assert switch.value == 1

        assert switch.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20))
        )
        assert switch.value == 0
        assert target.value == 0
        assert device.history_service.clicks == ["test_thumbler", "test_thumbler"]
    finally:
        pygame.quit()
