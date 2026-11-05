from enum import Enum
from typing import List
from devices.device_base import DeviceBase
from core.dependency_action import DependencyAction, DependencyType
from core.algorithm_service import Algorithm, Action, ActionName
from controls.thumbler import Thumbler
from controls.big_button import BigButton
from controls.lamp import Lamp
from controls.knobs import RotateStepWheel, PotWheel
from config import Assets

class AzaliaPage(Enum):
    CONTROL = "Пульт управления оператора"
    TRANSMITTER = "Блок передатчиков ВЧ"

def create_azalia_device() -> DeviceBase:
    pages = [
        AzaliaPage.CONTROL,
        AzaliaPage.TRANSMITTER,
    ]
    device = DeviceBase("Azalia", "Станция помех «Азалия»", pages, AzaliaPage.CONTROL)

    device.set_background(AzaliaPage.CONTROL, Assets.AZALIA_CONTROL)
    device.set_background(AzaliaPage.TRANSMITTER, Assets.AZALIA_TX)

    # ---------------- PAGE 1: CONTROL (Пульт управления) ----------------
    azalia_power_deps = [
        DependencyAction(DependencyType.REPLACE, "azalia_lamp_power", {1: 1, 0: 0}),
    ]
    device.add_element(Thumbler("azalia_thumbler_power", 450, 290, AzaliaPage.CONTROL, dependency_actions=azalia_power_deps))
    device.add_element(Lamp("azalia_lamp_power", 380, 295, AzaliaPage.CONTROL))

    azalia_heat_deps = [
        DependencyAction(DependencyType.REPLACE, "azalia_lamp_heat", {1: 1, 0: 0}),
        DependencyAction(DependencyType.REPLACE, "azalia_lamp_ready", {1: 1, 0: 0}, delayed_time_seconds=2),
    ]
    device.add_element(Thumbler("azalia_thumbler_heat", 450, 410, AzaliaPage.CONTROL, dependency_actions=azalia_heat_deps))
    device.add_element(Lamp("azalia_lamp_heat", 380, 415, AzaliaPage.CONTROL))
    device.add_element(Lamp("azalia_lamp_ready", 380, 535, AzaliaPage.CONTROL))

    azalia_high_deps = [
        DependencyAction(DependencyType.REPLACE, "azalia_lamp_emission", {1: 1, 0: 0}),
        DependencyAction(DependencyType.REPLACE, "azalia_tx_lamp_active", {1: 1, 0: 0}, delayed_time_seconds=1),
    ]
    device.add_element(Thumbler("azalia_thumbler_high", 450, 650, AzaliaPage.CONTROL, dependency_actions=azalia_high_deps))
    device.add_element(Lamp("azalia_lamp_emission", 380, 655, AzaliaPage.CONTROL))

    device.add_element(RotateStepWheel("azalia_switch_freq", 450, 800, AzaliaPage.CONTROL, value=1, max_value=5))
    device.add_element(RotateStepWheel("azalia_switch_mode", 450, 950, AzaliaPage.CONTROL, value=0, max_value=2))

    # ---------------- PAGE 2: TRANSMITTER (Блок передатчиков) ----------------
    device.add_element(RotateStepWheel("azalia_tx_knob_tuning", 440, 550, AzaliaPage.TRANSMITTER, value=2, max_value=6))
    device.add_element(Lamp("azalia_tx_lamp_active", 360, 555, AzaliaPage.TRANSMITTER))
    device.add_element(Thumbler("azalia_tx_thumbler_cooling", 440, 750, AzaliaPage.TRANSMITTER))
    device.add_element(Lamp("azalia_tx_lamp_cooling", 360, 755, AzaliaPage.TRANSMITTER))

    return device


def get_azalia_algorithms() -> List[Algorithm]:
    return [
        Algorithm(
            name="1. Включение и настройка станции помех «Азалия» в автоматическом режиме",
            actions=[
                Action(
                    ActionName.CLICK,
                    "azalia_thumbler_power",
                    hint_text="Нажмите на тумблер 'СЕТЬ' на пульте управления",
                    expected_value=1,
                    hint_indirect="Включить первичное электропитание станции",
                    hint_clarify="На пульте управления переведите тумблер 'СЕТЬ' в положение 'ВКЛ'. Загорится лампа 'СЕТЬ'."
                ),
                Action(
                    ActionName.CLICK,
                    "azalia_thumbler_heat",
                    hint_text="Нажмите на тумблер 'НАКАЛ'",
                    expected_value=1,
                    hint_indirect="Включить накал передающих ламп",
                    hint_clarify="Переведите тумблер 'НАКАЛ' в положение 'ВКЛ'. Дождитесь зажигания лампы 'ГОТОВ'."
                ),
                Action(
                    ActionName.CLICK,
                    "azalia_switch_freq",
                    hint_text="Кликните переключатель частотного поддиапазона (положение 2)",
                    expected_value=2,
                    hint_indirect="Установить заданный диапазон подавления",
                    hint_clarify="Поверните переключатель частотного поддиапазона в положение 2."
                ),
                Action(
                    ActionName.CLICK,
                    "azalia_thumbler_high",
                    hint_text="Нажмите на тумблер 'ВЫСОКОЕ'",
                    expected_value=1,
                    hint_indirect="Подать высокое напряжение излучения",
                    hint_clarify="После готовности переведите тумблер 'ВЫСОКОЕ' в положение 'ВКЛ'. Загорится лампа 'ИЗЛУЧЕНИЕ'."
                ),
            ]
        )
    ]
