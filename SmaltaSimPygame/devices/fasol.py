from enum import Enum
from typing import List
from devices.device_base import DeviceBase
from core.dependency_action import DependencyAction, DependencyType
from core.algorithm_service import Algorithm, Action, ActionName
from controls.thumbler import Thumbler
from controls.big_button import BigButton
from controls.lamp import Lamp
from controls.lightbox import Lightbox
from controls.knobs import RotateStepWheel, PotWheel
from controls.oscilloscope import Oscilloscope
from config import Assets

class FasolPage(Enum):
    PU = "Пульт управления (ПУ)"
    B2 = "Передающий блок Б2"
    C4_60 = "Анализатор спектра С4-60"
    M3_1A = "Измеритель мощности М3-1А"

def create_fasol_device() -> DeviceBase:
    pages = [
        FasolPage.PU,
        FasolPage.B2,
        FasolPage.C4_60,
        FasolPage.M3_1A,
    ]
    device = DeviceBase("Fasol", "Станция СПС-5М «Фасоль»", pages, FasolPage.PU)

    device.set_background(FasolPage.PU, Assets.FASOL_PU)
    device.set_background(FasolPage.B2, Assets.FASOL_B2)
    device.set_background(FasolPage.C4_60, Assets.FASOL_C4_60)
    device.set_background(FasolPage.M3_1A, Assets.FASOL_M3_1A)

    # ---------------- PAGE 1: PU (Пульт управления) ----------------
    pu_power_deps = [
        DependencyAction(DependencyType.REPLACE, "fasol_pu_lamp_power", {1: 1, 0: 0}),
    ]
    device.add_element(Thumbler("fasol_pu_thumbler_power", 450, 480, FasolPage.PU, dependency_actions=pu_power_deps))
    device.add_element(Lamp("fasol_pu_lamp_power", 380, 485, FasolPage.PU))

    pu_heating_deps = [
        DependencyAction(DependencyType.REPLACE, "fasol_pu_lamp_heating", {1: 1, 0: 0}),
    ]
    device.add_element(Thumbler("fasol_pu_thumbler_heating", 450, 600, FasolPage.PU, dependency_actions=pu_heating_deps))
    device.add_element(Lamp("fasol_pu_lamp_heating", 380, 605, FasolPage.PU))

    pu_high_deps = [
        DependencyAction(DependencyType.REPLACE, "fasol_pu_lamp_high_voltage", {1: 1, 0: 0}),
        DependencyAction(DependencyType.REPLACE, "fasol_b2_lamp_resonance", {1: 1, 0: 0}, delayed_time_seconds=1),
    ]
    device.add_element(Thumbler("fasol_pu_thumbler_high_voltage", 450, 720, FasolPage.PU, dependency_actions=pu_high_deps))
    device.add_element(Lamp("fasol_pu_lamp_high_voltage", 380, 725, FasolPage.PU))

    # Subband selector
    device.add_element(RotateStepWheel("fasol_pu_switch_subband", 450, 850, FasolPage.PU, value=1, max_value=4))
    device.add_element(Lamp("fasol_pu_lamp_alarm", 380, 855, FasolPage.PU))

    # ---------------- PAGE 2: B2 (Передающий блок Б2) ----------------
    device.add_element(RotateStepWheel("fasol_b2_knob_tuning", 420, 560, FasolPage.B2, value=0, max_value=8))
    device.add_element(Thumbler("fasol_b2_switch_load", 420, 720, FasolPage.B2))
    device.add_element(Lamp("fasol_b2_lamp_resonance", 340, 640, FasolPage.B2))

    # ---------------- PAGE 3: C4_60 (Анализатор спектра С4-60) ----------------
    c460_power_deps = [
        DependencyAction(DependencyType.REPLACE, "fasol_c460_lamp_power", {1: 1, 0: 0}),
    ]
    device.add_element(Thumbler("fasol_c460_thumbler_power", 480, 480, FasolPage.C4_60, dependency_actions=c460_power_deps))
    device.add_element(Lamp("fasol_c460_lamp_power", 410, 485, FasolPage.C4_60))

    device.add_element(PotWheel("fasol_c460_knob_gain", 480, 620, FasolPage.C4_60, value=5, min_value=0, max_value=10, width=60, height=60, image_type="Flat"))
    device.add_element(PotWheel("fasol_c460_knob_sweep", 480, 760, FasolPage.C4_60, value=5, min_value=0, max_value=10, width=60, height=60, image_type="Flat"))
    device.add_element(Oscilloscope("fasol_c460_scope", 200, 920, FasolPage.C4_60, width=320, height=240))

    # ---------------- PAGE 4: M3_1A (Измеритель мощности М3-1А) ----------------
    m31a_power_deps = [
        DependencyAction(DependencyType.REPLACE, "fasol_m31a_lamp_power", {1: 1, 0: 0}),
    ]
    device.add_element(Thumbler("fasol_m31a_thumbler_power", 460, 520, FasolPage.M3_1A, dependency_actions=m31a_power_deps))
    device.add_element(Lamp("fasol_m31a_lamp_power", 390, 525, FasolPage.M3_1A))
    device.add_element(RotateStepWheel("fasol_m31a_switch_range", 460, 660, FasolPage.M3_1A, value=2, max_value=5))
    device.add_element(PotWheel("fasol_m31a_knob_zero", 460, 800, FasolPage.M3_1A, value=0, min_value=-5, max_value=5, width=60, height=60, image_type="Flat"))

    return device


def get_fasol_algorithms() -> List[Algorithm]:
    return [
        Algorithm(
            name="1. Подготовка к полетам и включение станции СПС-5М «Фасоль»",
            actions=[
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_power",
                    hint_text="Нажмите на тумблер 'СЕТЬ' на пульте управления",
                    expected_value=1,
                    hint_indirect="Включить первичное напряжение питания станции СПС-5М",
                    hint_clarify="На пульте управления (ПУ) переведите тумблер 'СЕТЬ' в положение 'ВКЛ'. Должна загореться контрольная лампа 'СЕТЬ'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_heating",
                    hint_text="Нажмите на тумблер 'НАКАЛ' на пульте управления",
                    expected_value=1,
                    hint_indirect="Включить накал генераторных ламп передатчика",
                    hint_clarify="На пульте управления установите тумблер 'НАКАЛ' в положение 'ВКЛ'. Загорится лампа 'НАКАЛ' (прогрев 2-3 мин)."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_switch_subband",
                    hint_text="Кликните переключатель поддиапазонов для перевода в положение 2",
                    expected_value=2,
                    hint_indirect="Установить назначенный литерный поддиапазон частот",
                    hint_clarify="Поверните переключатель поддиапазонов на ПУ в заданное положение (поддиапазон 2)."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_high_voltage",
                    hint_text="Нажмите на тумблер 'ВЫСОКОЕ' на пульте управления",
                    expected_value=1,
                    hint_indirect="Включить высокое напряжение передатчика",
                    hint_clarify="После окончания прогрева переведите тумблер 'ВЫСОКОЕ' в положение 'ВКЛ'. Должна загореться лампа 'ВЫСОКОЕ'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_b2_switch_load",
                    hint_text="Нажмите на переключатель нагрузки на блоке Б2",
                    expected_value=1,
                    hint_indirect="Подключить передатчик блока Б2 к передающей антенне",
                    hint_clarify="Перейдите на блок Б2 и переведите переключатель нагрузки в положение 'АНТЕННА'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_c460_thumbler_power",
                    hint_text="Нажмите тумблер 'СЕТЬ' на анализаторе спектра С4-60",
                    expected_value=1,
                    hint_indirect="Включить анализатор спектра С4-60 для контроля излучения",
                    hint_clarify="Перейдите на панель анализатора спектра С4-60 и переведите тумблер 'СЕТЬ' в положение 'ВКЛ'."
                ),
            ]
        ),
        Algorithm(
            name="2. Контроль параметров помехового сигнала на анализаторе С4-60",
            actions=[
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_power",
                    hint_text="Нажмите тумблер 'СЕТЬ'",
                    expected_value=1,
                    hint_indirect="Подать питание на пульт управления",
                    hint_clarify="Переведите тумблер 'СЕТЬ' на ПУ в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_heating",
                    hint_text="Нажмите тумблер 'НАКАЛ'",
                    expected_value=1,
                    hint_indirect="Включить накал передатчика",
                    hint_clarify="Установите тумблер 'НАКАЛ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_high_voltage",
                    hint_text="Нажмите тумблер 'ВЫСОКОЕ'",
                    expected_value=1,
                    hint_indirect="Подать высокое напряжение",
                    hint_clarify="Переведите тумблер 'ВЫСОКОЕ' в верхнее положение."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_c460_thumbler_power",
                    hint_text="Нажмите тумблер 'СЕТЬ' на С4-60",
                    expected_value=1,
                    hint_indirect="Включить прибор С4-60",
                    hint_clarify="На анализаторе спектра включите тумблер 'СЕТЬ'."
                ),
            ]
        ),
        Algorithm(
            name="3. Измерение выходной мощности передатчика прибором М3-1А",
            actions=[
                Action(
                    ActionName.CLICK,
                    "fasol_m31a_thumbler_power",
                    hint_text="Нажмите тумблер 'СЕТЬ' на приборе М3-1А",
                    expected_value=1,
                    hint_indirect="Включить измеритель мощности М3-1А",
                    hint_clarify="Перейдите на панель М3-1А и переведите тумблер 'СЕТЬ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_power",
                    hint_text="Нажмите тумблер 'СЕТЬ' на ПУ",
                    expected_value=1,
                    hint_indirect="Включить питание станции СПС-5М",
                    hint_clarify="На пульте управления переведите тумблер 'СЕТЬ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_heating",
                    hint_text="Нажмите тумблер 'НАКАЛ' на ПУ",
                    expected_value=1,
                    hint_indirect="Включить накал ламп передатчика",
                    hint_clarify="Переведите тумблер 'НАКАЛ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "fasol_pu_thumbler_high_voltage",
                    hint_text="Нажмите тумблер 'ВЫСОКОЕ' на ПУ",
                    expected_value=1,
                    hint_indirect="Включить высокое напряжение передатчика",
                    hint_clarify="Переведите тумблер 'ВЫСОКОЕ' в положение 'ВКЛ'."
                ),
            ]
        )
    ]
