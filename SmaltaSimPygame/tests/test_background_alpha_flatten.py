"""Backgrounds must be opaque: transparent pixels are filled with a neutral matte."""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from devices.device_base import DeviceBase


def test_set_background_flattens_alpha_to_neutral_matte(tmp_path):
    pygame.init()
    try:
        pygame.display.set_mode((100, 100))
        source = pygame.Surface((4, 2), pygame.SRCALPHA)
        source.fill((0, 255, 0, 0))
        source.fill((220, 30, 30, 255), pygame.Rect(2, 0, 2, 2))
        path = tmp_path / "transparent_background.png"
        pygame.image.save(source, path)

        device = DeviceBase("test", "test", ["page"], "page")
        device.set_background("page", path)
        rendered = device.page_backgrounds["page"]

        assert not (rendered.get_flags() & pygame.SRCALPHA)
        # The fully transparent left side is now the neutral matte, not green.
        assert rendered.get_at((100, 400))[:3] == (20, 24, 28)
    finally:
        pygame.quit()
