"""Shared helpers for animated Smalta controls.

Custom control sprites are loaded from assets/Smalta/Controls.  The code
falls back to the project's original icon paths when custom sprites are
not installed, so the application can still start before the new assets are
copied.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
import pygame

from config import ASSETS_DIR

ICON_DIR = Path(ASSETS_DIR) / "Smalta" / "Controls"
ANIMATION_MS = 180

_CACHE: dict[str, pygame.Surface] = {}


def load_icon(filename: str, fallback_path: Optional[Path] = None) -> Optional[pygame.Surface]:
    """Load a custom control sprite, falling back to an existing project icon."""
    cache_key = filename if (ICON_DIR / filename).exists() else f"fallback:{fallback_path}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    candidate = ICON_DIR / filename
    if not candidate.exists() and fallback_path is not None:
        candidate = Path(fallback_path)
    if not candidate.exists():
        return None

    image = pygame.image.load(str(candidate))
    if pygame.display.get_surface() is not None:
        image = image.convert_alpha()
    _CACHE[cache_key] = image
    return image


def fit_inside(image: pygame.Surface, max_size: Tuple[int, int]) -> pygame.Surface:
    """Scale an image to fit within max_size while preserving its aspect ratio."""
    max_w, max_h = max_size
    iw, ih = image.get_size()
    if iw <= 0 or ih <= 0:
        return image.copy()
    scale = min(max_w / iw, max_h / ih)
    size = (max(1, round(iw * scale)), max(1, round(ih * scale)))
    return pygame.transform.smoothscale(image, size)


def normalize_pair(
    image_a: pygame.Surface,
    image_b: pygame.Surface,
    anchor: str = "center",
) -> tuple[pygame.Surface, pygame.Surface]:
    """Place two endpoint sprites onto same-size transparent canvases.

    anchor='bottom' keeps lever pivots at the same y coordinate while the
    lever art changes size/pose.
    """
    width = max(image_a.get_width(), image_b.get_width())
    height = max(image_a.get_height(), image_b.get_height())

    def place(source: pygame.Surface) -> pygame.Surface:
        canvas = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        x = (width - source.get_width()) // 2
        if anchor == "bottom":
            y = height - source.get_height()
        else:
            y = (height - source.get_height()) // 2
        canvas.blit(source, (x, y))
        return canvas

    return place(image_a), place(image_b)


def ease(progress: float) -> float:
    """Smoothstep easing for a soft mechanical transition."""
    t = max(0.0, min(1.0, progress))
    return t * t * (3.0 - 2.0 * t)


def blend_surfaces(
    from_surface: pygame.Surface,
    to_surface: pygame.Surface,
    progress: float,
) -> pygame.Surface:
    """Crossfade equally-sized sprites, preserving their per-pixel alpha."""
    t = ease(progress)
    if t <= 0.0:
        return from_surface.copy()
    if t >= 1.0:
        return to_surface.copy()

    frame = pygame.Surface(from_surface.get_size(), pygame.SRCALPHA, 32)
    a = from_surface.copy()
    b = to_surface.copy()
    a.set_alpha(round(255 * (1.0 - t)))
    b.set_alpha(round(255 * t))
    frame.blit(a, (0, 0))
    frame.blit(b, (0, 0))
    return frame


def progress_since(start_ms: int, duration_ms: int = ANIMATION_MS) -> float:
    if start_ms <= 0:
        return 1.0
    return max(0.0, min(1.0, (pygame.time.get_ticks() - start_ms) / float(duration_ms)))


def press_effect(image: pygame.Surface, pressed: bool) -> tuple[pygame.Surface, tuple[int, int]]:
    """Make a button visibly travel inward while mouse is held."""
    if not pressed:
        return image, (0, 0)
    width, height = image.get_size()
    squeezed = (
        max(1, round(width * 0.96)),
        max(1, round(height * 0.91)),
    )
    compressed = pygame.transform.smoothscale(image, squeezed)
    return compressed, ((width - squeezed[0]) // 2, max(1, height - squeezed[1]))
