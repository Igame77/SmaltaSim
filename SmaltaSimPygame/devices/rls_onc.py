from enum import Enum
from typing import List
from devices.device_base import DeviceBase
from core.dependency_action import DependencyAction, DependencyType
from core.algorithm_service import Algorithm, Action, ActionName
from controls.thumbler import Thumbler
from controls.lamp import Lamp
from controls.knobs import RotateStepWheel, PotWheel
from controls.radar import RadarTarget, RadarNoise
from controls.oscilloscope import Oscilloscope
from controls.number_display import NumberDisplay
from config import Assets

class RlsPage(Enum):
    Station = "Радиолокационная станция"
    ControlPanelSimulator = "Пульт управления имитатора"
    G5_15 = "Генератор импульсов Г5-15"
    Radar = "Экран индикатора"
    C1_65 = "Осциллограф С1-65"

def create_rls_device() -> DeviceBase:
    pages = [
        RlsPage.Station,
        RlsPage.ControlPanelSimulator,
        RlsPage.G5_15,
        RlsPage.Radar,
        RlsPage.C1_65,
    ]
    device = DeviceBase("RLS_ONC", "Импульсная РЛС ОНЦ", pages, RlsPage.Station)

    device.set_background(RlsPage.Station, Assets.RLS_STATION)
    device.set_background(RlsPage.ControlPanelSimulator, Assets.RLS_CPS)
    device.set_background(RlsPage.G5_15, Assets.RLS_G5_15)
    device.set_background(RlsPage.Radar, Assets.RLS_RADAR)
    device.set_background(RlsPage.C1_65, Assets.RLS_C1_65)

    # ---------------- PAGE: Station ----------------
    device.add_element(RotateStepWheel("station_stepwheel_zoom", 81, 1035, RlsPage.Station, value=2, startup_rotation=20, rotation_step_degrees=32, max_value=5))
    device.add_element(RotateStepWheel("station_stepwheel_secodary_temp", 342, 907, RlsPage.Station, value=0, startup_rotation=5, rotation_step_degrees=33, max_value=6))
    device.add_element(Thumbler("station_thumbler_speed", 528, 671, RlsPage.Station, value=0))
    device.add_element(Thumbler("station_thumbler_direction", 528, 755, RlsPage.Station, value=0))

    # ---------------- PAGE: ControlPanelSimulator ----------------
    device.add_element(RotateStepWheel("cps_stepwheel_noisetype", 319, 454, RlsPage.ControlPanelSimulator, value=4, startup_rotation=-45, rotation_step_degrees=31, max_value=5))
    device.add_element(RotateStepWheel("cps_stepwheel_generator_mode", 259, 742, RlsPage.ControlPanelSimulator, value=0, startup_rotation=-30, rotation_step_degrees=120, max_value=3))
    device.add_element(RotateStepWheel("cps_stepwheel_blocking_generator_mode", 315, 1077, RlsPage.ControlPanelSimulator, value=0, startup_rotation=-55, rotation_step_degrees=30, max_value=5))

    noise_dep_map = {0: 0, 5: 10, 10: 20, 15: 30, 20: 40, 25: 50, 30: 60, 35: 70, 40: 80, 45: 90, 50: 100}
    device.add_element(PotWheel(
        "cps_wheel_noise", 635, 568, RlsPage.ControlPanelSimulator,
        value=0, min_value=0, max_value=50, rotation_coefficient=20, width=100, height=100, image_type="Flat",
        dependency_actions=[DependencyAction(DependencyType.REPLACE, "radar_noise", noise_dep_map)]
    ))

    signal_dep_map = {0: 0, 5: 10, 10: 20, 15: 30, 20: 40, 25: 50, 30: 60, 35: 70, 40: 80, 45: 90, 50: 100}
    device.add_element(PotWheel(
        "cps_wheel_signal_noise", 638, 834, RlsPage.ControlPanelSimulator,
        value=25, min_value=0, max_value=50, rotation_coefficient=20, width=100, height=100, image_type="Flat",
        dependency_actions=[DependencyAction(DependencyType.REPLACE, "radar_target_1", signal_dep_map)]
    ))

    # ---------------- PAGE: G5_15 ----------------
    device.add_element(RotateStepWheel("g515_stepwheel_timeshift", 95, 388, RlsPage.G5_15, value=3, startup_rotation=40, rotation_step_degrees=31, max_value=6))
    device.add_element(RotateStepWheel("g515_stepwheel_duration", 98, 905, RlsPage.G5_15, value=6, startup_rotation=-50, rotation_step_degrees=31, max_value=10))

    device.add_element(NumberDisplay("g515_numberdisplay_timeshift", 246, 435, RlsPage.G5_15, value=5))
    device.add_element(NumberDisplay("g515_numberdisplay_repetition_rate", 246, 699, RlsPage.G5_15, value=400))
    device.add_element(NumberDisplay("g515_numberdisplay_amplitude_measurement", 246, 960, RlsPage.G5_15, value=50))

    device.add_element(PotWheel(
        "g515_wheel_timeshift", 327, 513, RlsPage.G5_15,
        value=1, min_value=1, max_value=11, rotation_coefficient=20, width=50, height=50, image_type="Flat",
        dependency_actions=[DependencyAction(DependencyType.COEFFICIENT_REPLACE, "g515_numberdisplay_timeshift", dependency_coefficient=5)]
    ))

    device.add_element(PotWheel(
        "g515_wheel_repetition_rate", 327, 774, RlsPage.G5_15,
        value=8, min_value=8, max_value=20, rotation_coefficient=20, width=50, height=50, image_type="Flat",
        dependency_actions=[DependencyAction(DependencyType.COEFFICIENT_REPLACE, "g515_numberdisplay_repetition_rate", dependency_coefficient=50)]
    ))

    device.add_element(PotWheel(
        "g515_wheel_amplitude_measurement", 327, 1036, RlsPage.G5_15,
        value=5, min_value=1, max_value=11, rotation_coefficient=20, width=50, height=50, image_type="Flat",
        dependency_actions=[DependencyAction(DependencyType.COEFFICIENT_REPLACE, "g515_numberdisplay_amplitude_measurement", dependency_coefficient=10)]
    ))

    device.add_element(Lamp("g515_lamp_amplitude_indicator", 237, 1244, RlsPage.G5_15, value=1))

    device.add_element(PotWheel(
        "g515_wheel_impulse_amplitude", 396, 1251, RlsPage.G5_15,
        value=6, min_value=1, max_value=10, rotation_coefficient=20, width=50, height=50, image_type="Flat",
        dependency_actions=[DependencyAction(DependencyType.REPLACE, "g515_lamp_amplitude_indicator", {5: 0, 6: 1})]
    ))

    # ---------------- PAGE: Radar ----------------
    device.add_element(RadarTarget("radar_target_1", 239, 649, RlsPage.Radar, value=25))
    device.add_element(RadarNoise("radar_noise", 138, 603, RlsPage.Radar, value=0, startup_rotation=-60))

    # ---------------- PAGE: C1_65 ----------------
    device.add_element(Oscilloscope("c165_oscilloscope", 97, 357, RlsPage.C1_65, width=380, height=300))

    scan_1_deps = [
        DependencyAction(DependencyType.REPLACE, "c165_thumbler_scanmode_0_1", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "c165_thumbler_scanmode_X", {1: 0}),
    ]
    device.add_element(Thumbler("c165_thumbler_scanmode_1", 116, 946, RlsPage.C1_65, value=1, dependency_actions=scan_1_deps))

    scan_01_deps = [
        DependencyAction(DependencyType.REPLACE, "c165_thumbler_scanmode_1", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "c165_thumbler_scanmode_X", {1: 0}),
    ]
    device.add_element(Thumbler("c165_thumbler_scanmode_0_1", 116, 976, RlsPage.C1_65, value=0, dependency_actions=scan_01_deps))

    scan_x_deps = [
        DependencyAction(DependencyType.REPLACE, "c165_thumbler_scanmode_1", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "c165_thumbler_scanmode_0_1", {1: 0}),
    ]
    device.add_element(Thumbler("c165_thumbler_scanmode_X", 116, 1006, RlsPage.C1_65, value=0, dependency_actions=scan_x_deps))

    return device


def get_rls_algorithms() -> List[Algorithm]:
    actions = [
        Action(ActionName.CLICK, "cps_wheel_signal_noise", "Путем поворота колесика мыши добейтесь устойчивого появления цели на экране индикатора", expected_value=50),
        Action(ActionName.INFO, "radar_target_1", "Как можно заметить, цель отчетливо видно на индикаторе"),
        Action(ActionName.CLICK, "cps_stepwheel_noisetype", "Осуществим подавление цели: переключите вид помех на 'Прямошумовая помеха' (положение 3)", expected_value=3),
        Action(ActionName.CLICK, "cps_stepwheel_generator_mode", "Переключите режим работы станции РЛС в положение 'Работа' (положение 2)", expected_value=2),
        Action(ActionName.CLICK, "station_thumbler_speed", "Переключите режим работы РЛС в положение 'Медленно' (1)", expected_value=1),
        Action(ActionName.CLICK, "cps_wheel_noise", "Прокрутите колесо для максимального увеличения помехового сигнала (значение 50)", expected_value=50),
        Action(ActionName.INFO, "radar_target_1", "Как можно видеть, цель полностью засвечена помехой"),
        Action(ActionName.CLICK, "cps_stepwheel_generator_mode", "Поставьте режим работы станции в положение 'Измерение' (0)", expected_value=0),
        Action(ActionName.CLICK, "cps_stepwheel_noisetype", "Переключите вид поставляемой помехи на 'ЧМШ' (1)", expected_value=1),
        Action(ActionName.CLICK, "c165_thumbler_scanmode_X", "Выключите развертку осциллографа, переведя переключатель в положение 'X'", expected_value=1),
    ]
    algo = Algorithm("Снятие зависимости коэффициента подавления от длительности импульсов в пачке", {}, {}, actions)
    return [algo]
