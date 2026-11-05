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
from config import Assets

class SorbtiaPage(Enum):
    KPA = "Блок КПА (СВК)"
    PN_OMEGA = "Пульт ПН ОМЕГА-М"
    PN_PV = "Пульт ПН-ПВ"
    UBP = "Пульт ПН УБП"
    MEAS = "Генераторы Г4-82 / Г5-54"

def create_sorbtia_device() -> DeviceBase:
    pages = [
        SorbtiaPage.KPA,
        SorbtiaPage.PN_OMEGA,
        SorbtiaPage.PN_PV,
        SorbtiaPage.UBP,
        SorbtiaPage.MEAS,
    ]
    device = DeviceBase("Sorbtia", "Станция «Сорбция-С» (МРМ-70)", pages, SorbtiaPage.KPA)

    device.set_background(SorbtiaPage.KPA, Assets.SORBTIA_KPA)
    device.set_background(SorbtiaPage.PN_OMEGA, Assets.SORBTIA_PN_OMEGA)
    device.set_background(SorbtiaPage.PN_PV, Assets.SORBTIA_PN_PV)
    device.set_background(SorbtiaPage.UBP, Assets.SORBTIA_UBP)
    device.set_background(SorbtiaPage.MEAS, Assets.SORBTIA_G5_54)

    # ---------------- PAGE 1: KPA (Контрольно-проверочная аппаратура) ----------------
    kpa_power_deps = [
        DependencyAction(DependencyType.REPLACE, "kpa_lamp_power", {1: 1, 0: 0}),
        DependencyAction(DependencyType.REPLACE, "kpa_lamp_kns15", {1: 1, 0: 0}, delayed_time_seconds=1),
        DependencyAction(DependencyType.REPLACE, "kpa_lamp_prd15", {1: 1, 0: 0}, delayed_time_seconds=1),
        DependencyAction(DependencyType.REPLACE, "kpa_lamp_prm15", {1: 1, 0: 0}, delayed_time_seconds=1),
        DependencyAction(DependencyType.REPLACE, "kpa_lamp_is15", {1: 1, 0: 0}, delayed_time_seconds=2),
    ]
    device.add_element(Thumbler("kpa_thumbler_power", 380, 480, SorbtiaPage.KPA, dependency_actions=kpa_power_deps))
    device.add_element(Lamp("kpa_lamp_power", 340, 485, SorbtiaPage.KPA))

    # Mode and Channel selection switches
    device.add_element(RotateStepWheel("kpa_switch_cu", 380, 580, SorbtiaPage.KPA, value=1, max_value=3))
    device.add_element(RotateStepWheel("kpa_switch_upg1", 380, 680, SorbtiaPage.KPA, value=0, max_value=4))
    device.add_element(RotateStepWheel("kpa_switch_nchannel", 380, 780, SorbtiaPage.KPA, value=0, max_value=3))

    # Status & SVK test indicators
    device.add_element(Lamp("kpa_lamp_kns15", 480, 520, SorbtiaPage.KPA))
    device.add_element(Lamp("kpa_lamp_prd15", 480, 620, SorbtiaPage.KPA))
    device.add_element(Lamp("kpa_lamp_prm15", 480, 720, SorbtiaPage.KPA))
    device.add_element(Lamp("kpa_lamp_is15", 480, 820, SorbtiaPage.KPA))

    # Check button & side tumbler
    device.add_element(BigButton("kpa_btn_check", 560, 600, SorbtiaPage.KPA))
    device.add_element(Thumbler("kpa_thumbler_side", 560, 720, SorbtiaPage.KPA))

    # ---------------- PAGE 2: PN_OMEGA (Пульт ПН ОМЕГА-М) ----------------
    omega_power_deps = [
        DependencyAction(DependencyType.REPLACE, "omega_lamp_power", {1: 1, 0: 0}),
        DependencyAction(DependencyType.REPLACE, "omega_lamp_ready", {1: 1, 0: 0}, delayed_time_seconds=2),
    ]
    device.add_element(Thumbler("omega_thumbler_15", 420, 550, SorbtiaPage.PN_OMEGA))
    device.add_element(Thumbler("omega_thumbler_power", 420, 700, SorbtiaPage.PN_OMEGA, dependency_actions=omega_power_deps))
    device.add_element(Lamp("omega_lamp_power", 340, 705, SorbtiaPage.PN_OMEGA))
    device.add_element(Lamp("omega_lamp_ready", 340, 555, SorbtiaPage.PN_OMEGA))

    # ---------------- PAGE 3: PN_PV (Пульт ПН-ПВ) ----------------
    pnpv_rtu_deps = [
        DependencyAction(DependencyType.REPLACE, "pnpv_lamp_rtu", {1: 1, 0: 0}),
    ]
    device.add_element(Thumbler("pnpv_thumbler_rtu", 420, 520, SorbtiaPage.PN_PV, dependency_actions=pnpv_rtu_deps))
    device.add_element(Lamp("pnpv_lamp_rtu", 350, 525, SorbtiaPage.PN_PV))

    pnpv_emission_deps = [
        DependencyAction(DependencyType.REPLACE, "pnpv_lamp_high_right", {1: 1, 0: 0}),
    ]
    device.add_element(Thumbler("pnpv_thumbler_emission", 420, 680, SorbtiaPage.PN_PV, dependency_actions=pnpv_emission_deps))
    device.add_element(Lamp("pnpv_lamp_high_right", 350, 685, SorbtiaPage.PN_PV))
    device.add_element(RotateStepWheel("pnpv_switch_inhibit", 540, 600, SorbtiaPage.PN_PV, value=0, max_value=3))

    # ---------------- PAGE 4: UBP (Пульт ПН УБП) ----------------
    ubp_on_deps = [
        DependencyAction(DependencyType.REPLACE, "ubp_lightbox_rtu_on", {1: 1, 0: 0}),
    ]
    device.add_element(BigButton("ubp_btn_on", 450, 580, SorbtiaPage.UBP, dependency_actions=ubp_on_deps))
    device.add_element(BigButton("ubp_btn_off", 450, 720, SorbtiaPage.UBP, dependency_actions=[
        DependencyAction(DependencyType.REPLACE, "ubp_lightbox_rtu_on", {1: 0})
    ]))
    device.add_element(Lightbox("ubp_lightbox_rtu_on", 330, 620, SorbtiaPage.UBP, "ВКЛ РТУ"))

    # ---------------- PAGE 5: MEAS (Измерители Г4-82 / Г5-54) ----------------
    device.add_element(Thumbler("g554_thumbler_power", 400, 500, SorbtiaPage.MEAS, dependency_actions=[
        DependencyAction(DependencyType.REPLACE, "g554_lamp_power", {1: 1, 0: 0})
    ]))
    device.add_element(Lamp("g554_lamp_power", 330, 505, SorbtiaPage.MEAS))

    device.add_element(Thumbler("g482_thumbler_power", 400, 750, SorbtiaPage.MEAS, dependency_actions=[
        DependencyAction(DependencyType.REPLACE, "g482_lamp_power", {1: 1, 0: 0})
    ]))
    device.add_element(Lamp("g482_lamp_power", 330, 755, SorbtiaPage.MEAS))

    return device


def get_sorbtia_algorithms() -> List[Algorithm]:
    return [
        Algorithm(
            name="1. Проверка работоспособности станции «Сорбция-С» с помощью СВК",
            actions=[
                Action(
                    ActionName.CLICK,
                    "omega_thumbler_15",
                    hint_text="Нажмите на тумблер '15' на пульте ПН ОМЕГА-М",
                    expected_value=1,
                    hint_indirect="Включить питание 15 канала станции на пульте ПН ОМЕГА-М",
                    hint_clarify="Перейдите на пульт ПН ОМЕГА-М и установите тумблер '15' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "omega_thumbler_power",
                    hint_text="Нажмите на тумблер 'СЕТЬ' на пульте ПН ОМЕГА-М",
                    expected_value=1,
                    hint_indirect="Подать первичное электропитание 200В, 400Гц на пульте ПН ОМЕГА-М",
                    hint_clarify="На пульте ПН ОМЕГА-М переведите тумблер 'СЕТЬ (200В, 400Гц)' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "pnpv_thumbler_rtu",
                    hint_text="Нажмите на тумблер 'РТУ' на пульте ПН-ПВ",
                    expected_value=1,
                    hint_indirect="Включить радиотехническое устройство (РТУ) на пульте ПН-ПВ",
                    hint_clarify="Перейдите на пульт ПН-ПВ и переведите тумблер 'РТУ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "ubp_btn_on",
                    hint_text="Нажмите кнопку 'ВКЛ' на пульте ПН УБП",
                    expected_value=1,
                    hint_indirect="Произвести запуск станции на пульте управления ПН УБП",
                    hint_clarify="Перейдите на пульт ПН УБП и нажмите кнопку 'ВКЛ'. Должно загореться табло 'ВКЛ РТУ'."
                ),
                Action(
                    ActionName.CLICK,
                    "pnpv_thumbler_emission",
                    hint_text="Нажмите на тумблер 'ВКЛ ИЗЛУЧЕНИЕ' на пульте ПН-ПВ",
                    expected_value=1,
                    hint_indirect="Включить высокое напряжение излучения на пульте ПН-ПВ",
                    hint_clarify="На пульте ПН-ПВ установите тумблер 'ВКЛ ИЗЛУЧЕНИЕ' в положение 'ВКЛ'. Должна загореться лампа 'ВЫСОКОЕ ПРАВЫЙ'."
                ),
                Action(
                    ActionName.CLICK,
                    "kpa_thumbler_power",
                    hint_text="Нажмите на тумблер 'СЕТЬ' на блоке КПА",
                    expected_value=1,
                    hint_indirect="Включить аппаратуру КПА и проконтролировать исправность каналов СВК",
                    hint_clarify="Перейдите на блок КПА и включите тумблер 'СЕТЬ'. Убедитесь в свечении индикаторов КНС 15, ПРД 15, ПРМ 15."
                ),
            ]
        ),
        Algorithm(
            name="2. Проверка работоспособности РТУ в импульсном режиме",
            actions=[
                Action(
                    ActionName.CLICK,
                    "omega_thumbler_power",
                    hint_text="Переведите тумблер 'СЕТЬ' на ПН ОМЕГА-М в верхнее положение",
                    expected_value=1,
                    hint_indirect="Подать питание на пульт ПН ОМЕГА-М",
                    hint_clarify="Установите тумблер 'СЕТЬ (200В, 400Гц)' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "omega_thumbler_15",
                    hint_text="Нажмите на тумблер '15' на пульте ПН ОМЕГА-М",
                    expected_value=1,
                    hint_indirect="Включить 15 канал на пульте ПН ОМЕГА-М",
                    hint_clarify="Установите тумблер '15' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "pnpv_thumbler_rtu",
                    hint_text="Нажмите тумблер 'РТУ' на пульте ПН-ПВ",
                    expected_value=1,
                    hint_indirect="Включить РТУ на пульте ПН-ПВ",
                    hint_clarify="На пульте ПН-ПВ переведите тумблер 'РТУ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "ubp_btn_on",
                    hint_text="Нажмите кнопку 'ВКЛ' на панели УБП",
                    expected_value=1,
                    hint_indirect="Нажать кнопку 'ВКЛ' на пульте ПН УБП",
                    hint_clarify="На пульте ПН УБП нажмите кнопку запуска РТУ."
                ),
                Action(
                    ActionName.CLICK,
                    "pnpv_thumbler_emission",
                    hint_text="Нажмите тумблер 'ВКЛ ИЗЛУЧЕНИЕ' на ПН-ПВ",
                    expected_value=1,
                    hint_indirect="Включить излучение станции",
                    hint_clarify="На пульте ПН-ПВ переведите тумблер 'ВКЛ ИЗЛУЧЕНИЕ' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "kpa_thumbler_power",
                    hint_text="Нажмите тумблер 'СЕТЬ' на блоке КПА",
                    expected_value=1,
                    hint_indirect="Включить блок КПА для проверки импульсного режима",
                    hint_clarify="На блоке КПА включите тумблер 'СЕТЬ' и проконтролируйте свечение индикатора 'ИС 15'."
                )
            ]
        ),
        Algorithm(
            name="3. Подготовка станции к боевому применению",
            actions=[
                Action(
                    ActionName.CLICK,
                    "omega_thumbler_15",
                    hint_text="Нажмите тумблер '15'",
                    expected_value=1,
                    hint_indirect="Включить литерный канал на ПН ОМЕГА-М",
                    hint_clarify="Переведите тумблер '15' в положение 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "omega_thumbler_power",
                    hint_text="Нажмите тумблер 'СЕТЬ' на Омега-М",
                    expected_value=1,
                    hint_indirect="Подать бортсеть 200В 400Гц",
                    hint_clarify="Включите тумблер питания 'СЕТЬ' на ПН ОМЕГА-М."
                ),
                Action(
                    ActionName.CLICK,
                    "pnpv_thumbler_rtu",
                    hint_text="Нажмите тумблер 'РТУ'",
                    expected_value=1,
                    hint_indirect="Включить тумблер РТУ",
                    hint_clarify="На пульте ПН-ПВ включите тумблер 'РТУ'."
                ),
                Action(
                    ActionName.CLICK,
                    "ubp_btn_on",
                    hint_text="Нажмите кнопку 'ВКЛ'",
                    expected_value=1,
                    hint_indirect="Запустить станцию кнопкой ВКЛ на УБП",
                    hint_clarify="На пульте ПН УБП нажмите 'ВКЛ'."
                ),
                Action(
                    ActionName.CLICK,
                    "pnpv_thumbler_emission",
                    hint_text="Нажмите тумблер 'ВКЛ ИЗЛУЧЕНИЕ'",
                    expected_value=1,
                    hint_indirect="Подать высокое напряжение излучения",
                    hint_clarify="На пульте ПН-ПВ установите тумблер 'ВКЛ ИЗЛУЧЕНИЕ' в положение 'ВКЛ'."
                ),
            ]
        )
    ]
