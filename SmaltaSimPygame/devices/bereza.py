from enum import Enum
from typing import List
from devices.device_base import DeviceBase
from core.dependency_action import DependencyAction, DependencyType
from core.algorithm_service import Algorithm, Action, ActionName
from controls.thumbler import Thumbler
from controls.big_button import BigButton
from controls.lamp import Lamp
from controls.knobs import RotateStepWheel
from config import Assets

class BerezaPage(Enum):
    INDICATOR = "Индикатор кабины (СПО-15)"
    CONTROL = "Блок встроенного контроля"

def create_bereza_device() -> DeviceBase:
    pages = [
        BerezaPage.INDICATOR,
        BerezaPage.CONTROL,
    ]
    device = DeviceBase("Bereza", "Станция СПО-15 «Береза»", pages, BerezaPage.INDICATOR)

    device.set_background(BerezaPage.INDICATOR, Assets.BEREZA_INDICATOR)
    device.set_background(BerezaPage.CONTROL, Assets.BEREZA_CONTROL)

    # ---------------- PAGE 1: INDICATOR (Индикатор кабины пилота) ----------------
    device.add_element(Lamp("bereza_lamp_azimuth_0", 250, 800, BerezaPage.INDICATOR))      # Nose
    device.add_element(Lamp("bereza_lamp_azimuth_45", 300, 890, BerezaPage.INDICATOR))     # Front-Right
    device.add_element(Lamp("bereza_lamp_azimuth_90", 390, 930, BerezaPage.INDICATOR))     # Right
    device.add_element(Lamp("bereza_lamp_azimuth_135", 480, 890, BerezaPage.INDICATOR))    # Rear-Right
    device.add_element(Lamp("bereza_lamp_azimuth_180", 530, 800, BerezaPage.INDICATOR))    # Tail
    device.add_element(Lamp("bereza_lamp_azimuth_225", 480, 710, BerezaPage.INDICATOR))    # Rear-Left
    device.add_element(Lamp("bereza_lamp_azimuth_270", 390, 670, BerezaPage.INDICATOR))    # Left
    device.add_element(Lamp("bereza_lamp_azimuth_315", 300, 710, BerezaPage.INDICATOR))    # Front-Left

    # Threat radar type lamps (П, З, О, В)
    device.add_element(Lamp("bereza_lamp_type_p", 620, 720, BerezaPage.INDICATOR))  # Перехватчик
    device.add_element(Lamp("bereza_lamp_type_z", 620, 770, BerezaPage.INDICATOR))  # ЗРК малый
    device.add_element(Lamp("bereza_lamp_type_o", 620, 830, BerezaPage.INDICATOR))  # ЗРК дальний
    device.add_element(Lamp("bereza_lamp_type_h", 620, 880, BerezaPage.INDICATOR))  # Вертолет

    # Signal power level indicator
    device.add_element(Lamp("bereza_lamp_power_level", 390, 800, BerezaPage.INDICATOR))

    # ---------------- PAGE 2: CONTROL (Блок встроенного контроля) ----------------
    test_deps = [
        DependencyAction(DependencyType.REPLACE, "bereza_lamp_ready", {1: 1, 0: 0}),
        DependencyAction(DependencyType.REPLACE, "bereza_lamp_azimuth_0", {1: 1, 0: 0}, delayed_time_seconds=1),
        DependencyAction(DependencyType.REPLACE, "bereza_lamp_azimuth_90", {1: 1, 0: 0}, delayed_time_seconds=1),
        DependencyAction(DependencyType.REPLACE, "bereza_lamp_azimuth_180", {1: 1, 0: 0}, delayed_time_seconds=1),
        DependencyAction(DependencyType.REPLACE, "bereza_lamp_azimuth_270", {1: 1, 0: 0}, delayed_time_seconds=1),
        DependencyAction(DependencyType.REPLACE, "bereza_lamp_type_p", {1: 1, 0: 0}, delayed_time_seconds=2),
    ]

    device.add_element(Thumbler("bereza_thumbler_power", 440, 520, BerezaPage.CONTROL))
    device.add_element(RotateStepWheel("bereza_switch_mode", 440, 660, BerezaPage.CONTROL, value=0, max_value=2))
    device.add_element(BigButton("bereza_btn_test", 440, 800, BerezaPage.CONTROL, dependency_actions=test_deps))
    device.add_element(Lamp("bereza_lamp_ready", 360, 665, BerezaPage.CONTROL))
    device.add_element(Lamp("bereza_lamp_fail", 360, 805, BerezaPage.CONTROL))

    return device


def get_bereza_algorithms() -> List[Algorithm]:
    return [
        Algorithm(
            name="1. Предполетная проверка аппаратуры СПО-15 «Береза» с помощью СВК",
            actions=[
                Action(
                    ActionName.CLICK,
                    "bereza_thumbler_power",
                    hint_text="Нажмите на тумблер питания СПО-15",
                    expected_value=1,
                    hint_indirect="Включить питание станции СПО-15 на пульте контроля",
                    hint_clarify="Перейдите на панель 'Блок встроенного контроля' и установите тумблер 'ПИТАНИЕ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "bereza_switch_mode",
                    hint_text="Кликните переключатель режимов (положение 1)",
                    expected_value=1,
                    hint_indirect="Установить переключатель режимов в положение 'КОНТРОЛЬ'",
                    hint_clarify="На пульте контроля переведите галетный переключатель в режим 'КОНТРОЛЬ'."
                ),
                Action(
                    ActionName.CLICK,
                    "bereza_btn_test",
                    hint_text="Нажмите кнопку 'КОНТРОЛЬ'",
                    expected_value=1,
                    hint_indirect="Нажать кнопку встроенного контроля (КОНТРОЛЬ)",
                    hint_clarify="Нажмите кнопку 'КОНТРОЛЬ'. Запустится тест самоконтроля, загорится лампа 'ГОТОВ' и светодиоды секторов индикатора."
                ),
            ]
        ),
        Algorithm(
            name="2. Отработка оценки радиолокационной обстановки при облучении РЛС",
            actions=[
                Action(
                    ActionName.CLICK,
                    "bereza_thumbler_power",
                    hint_text="Нажмите тумблер 'ПИТАНИЕ'",
                    expected_value=1,
                    hint_indirect="Включить станцию СПО-15",
                    hint_clarify="Установите тумблер 'ПИТАНИЕ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "bereza_switch_mode",
                    hint_text="Кликните переключатель в положение 0",
                    expected_value=0,
                    hint_indirect="Перевести станцию в боевой режим 'ПОЛЕТ'",
                    hint_clarify="Установите переключатель режимов в положение 'ПОЛЕТ' (0)."
                ),
            ]
        )
    ]
