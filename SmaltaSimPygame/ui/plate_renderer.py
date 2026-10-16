from typing import List, Tuple, Optional, Dict
from PIL import Image, ImageDraw, ImageFont
import pygame

_FONT_CACHE: Dict[Tuple[int, bool, bool], ImageFont.FreeTypeFont] = {}
_SURF_CACHE: Dict[str, pygame.Surface] = {}

def get_pil_font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    """Загружает системный сглаженный шрифт Segoe UI для формирования плашек."""
    key = (size, bold, italic)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    if bold and italic:
        candidates = ["segoeulz.ttf", "segoeuiz.ttf", "arialbi.ttf"]
    elif bold:
        candidates = ["segoeuib.ttf", "arialbd.ttf"]
    elif italic:
        candidates = ["segoeuii.ttf", "ariali.ttf"]
    else:
        candidates = ["segoeui.ttf", "arial.ttf"]

    font = None
    for fname in candidates:
        try:
            font = ImageFont.truetype(fname, size)
            break
        except Exception:
            continue

    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            pass

    _FONT_CACHE[key] = font
    return font


def pil_to_surface(img: Image.Image) -> pygame.Surface:
    """Конвертирует изображение Pillow в оптимизированный pygame.Surface."""
    raw = img.tobytes()
    return pygame.image.frombytes(raw, img.size, "RGBA")


def render_dialog_plate(
    title: str,
    lines: List[str],
    width: int,
    height: int,
    border_color: Tuple[int, int, int] = (56, 189, 248)
) -> pygame.Surface:
    """
    Генерирует высокочеткую нейтральную графическую плашку для модального диалога.
    Шрифт: Segoe UI (единый для всей системы).
    Фон: нейтральный темный сланцевый (#111827 / #0f172a).
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Внешняя карточка с плавным скруглением
    bg_fill = (17, 24, 39, 245)
    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=10,
        fill=bg_fill,
        outline=border_color,
        width=2
    )

    # Заголовок
    f_title = get_pil_font(20, bold=True)
    draw.text((25, 20), title, font=f_title, fill=(248, 250, 252))

    # Тонкая разделительная черта
    draw.line([(20, 56), (width - 20, 56)], fill=(51, 65, 85), width=1)

    # Строки содержимого
    f_body = get_pil_font(15, bold=False)
    my = 70
    line_h = 22
    for line in lines:
        if line:
            draw.text((28, my), line, font=f_body, fill=(226, 232, 240))
        my += line_h

    return pil_to_surface(img)


def render_auth_dialog_plate(
    width: int,
    height: int,
    field_labels: List[Tuple[int, int, str]]
) -> pygame.Surface:
    """Генерирует графическую плашку окна авторизации со встроенными подписями полей."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Карточка диалога
    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=14,
        fill=(18, 24, 35, 250),
        outline=(50, 70, 95),
        width=2
    )

    f_title = get_pil_font(20, bold=True)
    f_sub = get_pil_font(13, bold=False)
    f_lbl = get_pil_font(13, bold=True)

    draw.text((40, 24), "Авторизация для сдачи экзамена", font=f_title, fill=(255, 255, 255))
    draw.text((40, 52), "Данные будут переданы на пульт преподавателя и занесены в протокол", font=f_sub, fill=(148, 163, 184))

    # Метки полей
    for lx, ly, label in field_labels:
        draw.text((lx, ly), label, font=f_lbl, fill=(203, 213, 225))

    # Разделитель перед кнопками
    draw.line([(30, 375), (width - 30, 375)], fill=(35, 45, 60), width=1)

    return pil_to_surface(img)


def render_waiting_dialog_plate(
    width: int,
    height: int,
    student_name: str,
    group: str,
    pc: str,
    device_name: str,
    algo_name: str
) -> pygame.Surface:
    """Генерирует плашку окна ожидания допуска преподавателя."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=14,
        fill=(18, 24, 35, 250),
        outline=(52, 211, 153),
        width=2
    )

    f_title = get_pil_font(19, bold=True)
    f_body = get_pil_font(14, bold=False)
    f_bold = get_pil_font(14, bold=True)

    draw.text((75, 30), "Ожидание допуска преподавателя...", font=f_title, fill=(255, 255, 255))

    lines = [
        ("Курсант: ", f"{student_name} (Взвод/Группа {group}, {pc})", True),
        ("Изделие: ", device_name, True),
        ("Задание: ", algo_name, True),
        ("", "", False),
        ("", "Ваше рабочее место подключено к серверу преподавателя.", False),
        ("", "Экзамен начнется автоматически, как только преподаватель", False),
        ("", "нажмет «Допустить» или «Общий старт» на своем пульте.", False)
    ]

    ly = 75
    for prefix, text, is_hl in lines:
        if not text and not prefix:
            ly += 8
            continue
        if prefix:
            draw.text((40, ly), prefix, font=f_bold, fill=(148, 163, 184))
            draw.text((40 + 75, ly), text, font=f_bold, fill=(226, 232, 240))
        else:
            draw.text((40, ly), text, font=f_body, fill=(148, 163, 184))
        ly += 22

    return pil_to_surface(img)


def render_hud_banner_plate(
    width: int,
    height: int,
    step_str: str,
    badge_label: str,
    badge_bg: Tuple[int, int, int],
    badge_fg: Tuple[int, int, int],
    border_color: Tuple[int, int, int],
    text_lines: List[str],
    text_color: Tuple[int, int, int]
) -> Tuple[pygame.Surface, int]:
    """
    Генерирует высокочеткую плашку HUD-подсказки (верхний баннер).
    Возвращает (surface, text_x).
    """
    cache_key = f"hud_{width}_{height}_{step_str}_{badge_label}_{badge_bg}_{badge_fg}_{border_color}_{tuple(text_lines)}_{text_color}"
    if cache_key in _SURF_CACHE:
        return _SURF_CACHE[cache_key], _SURF_CACHE[cache_key + "_tx"]

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Основа карточки
    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=8,
        fill=(14, 20, 28, 240),
        outline=border_color,
        width=2
    )

    f_step = get_pil_font(13, bold=True)
    f_badge = get_pil_font(12, bold=True)
    f_text = get_pil_font(14, bold=True)

    # 1. Капсула номера шага
    bbox_s = draw.textbbox((0, 0), step_str, font=f_step)
    sw = (bbox_s[2] - bbox_s[0]) + 18
    draw.rounded_rectangle([10, 11, 10 + sw, 41], radius=6, fill=(28, 38, 50), outline=(50, 70, 90), width=1)
    draw.text((19, 17), step_str, font=f_step, fill=(215, 230, 245))

    # 2. Капсула уровня подсказки
    bx = 10 + sw + 8
    bbox_b = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw = (bbox_b[2] - bbox_b[0]) + 18
    draw.rounded_rectangle([bx, 11, bx + bw, 41], radius=6, fill=badge_bg, outline=border_color, width=1)
    draw.text((bx + 9, 18), badge_label, font=f_badge, fill=badge_fg)

    text_x = bx + bw + 14

    # 3. Текст подсказки
    if len(text_lines) == 1:
        draw.text((text_x, 15), text_lines[0], font=f_text, fill=text_color)
    elif len(text_lines) >= 2:
        draw.text((text_x, 6), text_lines[0], font=f_text, fill=text_color)
        draw.text((text_x, 26), text_lines[1], font=f_text, fill=(220, 235, 250))

    surf = pil_to_surface(img)
    _SURF_CACHE[cache_key] = surf
    _SURF_CACHE[cache_key + "_tx"] = text_x
    return surf, text_x


def render_speech_bubble_plate(
    width: int,
    height: int,
    lines: List[str],
    is_info: bool = False
) -> pygame.Surface:
    """Генерирует высокочеткую плашку речевого облака подсказки (на органе управления)."""
    cache_key = f"bubble_{width}_{height}_{tuple(lines)}_{is_info}"
    if cache_key in _SURF_CACHE:
        return _SURF_CACHE[cache_key]

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=6,
        fill=(18, 28, 38, 245),
        outline=(0, 195, 235),
        width=2
    )

    f_line = get_pil_font(14, bold=True)
    f_info = get_pil_font(12, italic=True)

    curr_ty = 9
    line_h = 20
    for l in lines:
        draw.text((12, curr_ty), l, font=f_line, fill=(255, 255, 255))
        curr_ty += line_h

    if is_info:
        draw.text((12, curr_ty + 2), "(Кликните по органу или нажмите Пробел)", font=f_info, fill=(120, 220, 255))

    surf = pil_to_surface(img)
    _SURF_CACHE[cache_key] = surf
    return surf


def render_nav_banner_plate(width: int, height: int, text: str) -> pygame.Surface:
    """Генерирует плашку навигации между блоками."""
    cache_key = f"nav_{width}_{height}_{text}"
    if cache_key in _SURF_CACHE:
        return _SURF_CACHE[cache_key]

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=6,
        fill=(25, 35, 45, 240),
        outline=(245, 158, 11),
        width=2
    )

    f_font = get_pil_font(14, bold=True)
    bbox = draw.textbbox((0, 0), text, font=f_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (width - tw) // 2
    ty = (height - th) // 2 - 1
    draw.text((tx, ty), text, font=f_font, fill=(255, 235, 130))

    surf = pil_to_surface(img)
    _SURF_CACHE[cache_key] = surf
    return surf
