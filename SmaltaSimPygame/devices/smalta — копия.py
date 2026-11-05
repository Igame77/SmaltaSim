from enum import Enum
from typing import List
from devices.device_base import DeviceBase
from core.dependency_action import DependencyAction, DependencyType
from core.algorithm_service import Algorithm, Action, ActionName
from controls.thumbler import Thumbler
from controls.big_button import BigButton
from controls.lamp import Lamp
from controls.lightbox import Lightbox
from controls.gauge_arrow import GaugeArrow
from controls.knobs import RotateStepWheel
from config import Assets

class SmaltaPage(Enum):
    LO01P = "ЛО01-П"
    LO01R = "ЛО01-Р"
    LO01I_LO01K = "ЛО01-И + ЛО01-К"

def create_smalta_device() -> DeviceBase:
    pages = [SmaltaPage.LO01P, SmaltaPage.LO01R, SmaltaPage.LO01I_LO01K]
    device = DeviceBase("LO01_Smalta", "ЛО01 Смальта", pages, SmaltaPage.LO01P)

    device.set_background(SmaltaPage.LO01P, Assets.SMALTA_LO01P)
    device.set_background(SmaltaPage.LO01R, Assets.SMALTA_LO01R)
    device.set_background(SmaltaPage.LO01I_LO01K, Assets.SMALTA_LO01I_LO01K)

    # ---------------- PAGE LO01P ----------------
    # Thumblers in center (horizontal, startup_rotation=90)
    device.add_element(Thumbler("lo01p_thumbler_1channel", 299, 409, SmaltaPage.LO01P, startup_rotation=90))
    device.add_element(Thumbler("lo01p_thumbler_2channel", 343, 409, SmaltaPage.LO01P, startup_rotation=90))
    device.add_element(Thumbler("lo01p_thumbler_3channel", 386, 409, SmaltaPage.LO01P, startup_rotation=90))
    device.add_element(Thumbler("lo01p_thumbler_4channel", 429, 409, SmaltaPage.LO01P, startup_rotation=90))

    # Lightboxes (Receivers)
    device.add_element(Lightbox("lo01p_reciever_1channel", 309, 540, SmaltaPage.LO01P, "ПРИЕМНИК\nI КАНАЛ"))
    device.add_element(Lightbox("lo01p_reciever_2channel", 353, 540, SmaltaPage.LO01P, "ПРИЕМНИК\nII КАНАЛ"))
    device.add_element(Lightbox("lo01p_reciever_3channel", 396, 540, SmaltaPage.LO01P, "ПРИЕМНИК\nIII КАНАЛ"))
    device.add_element(Lightbox("lo01p_reciever_4channel", 441, 541, SmaltaPage.LO01P, "ПРИЕМНИК\nIV КАНАЛ"))
    device.add_element(Lightbox("lo01p_antenna_leftside", 483, 540, SmaltaPage.LO01P, "АНТЕННА\nЛЕВЫЙ БОРТ"))

    # Lightboxes (Transmitters)
    device.add_element(Lightbox("lo01p_transmitter_1channel", 309, 628, SmaltaPage.LO01P, "ПЕРЕДАТЧИК\nI КАНАЛ"))
    device.add_element(Lightbox("lo01p_transmitter_2channel", 353, 628, SmaltaPage.LO01P, "ПЕРЕДАТЧИК\nII КАНАЛ"))
    device.add_element(Lightbox("lo01p_transmitter_3channel", 396, 628, SmaltaPage.LO01P, "ПЕРЕДАТЧИК\nIII КАНАЛ"))
    device.add_element(Lightbox("lo01p_transmitter_4channel", 441, 627, SmaltaPage.LO01P, "ПЕРЕДАТЧИК\nIV КАНАЛ"))
    device.add_element(Lightbox("lo01p_antenna_rightside", 484, 627, SmaltaPage.LO01P, "АНТЕННА\nПРАВЫЙ БОРТ"))

    # Lightboxes (Defects - Orange)
    defect_color = (255, 140, 0)
    device.add_element(Lightbox("lo01p_defect_1channel", 311, 715, SmaltaPage.LO01P, "НЕИСПРАВНОСТЬ\nI КАНАЛ", bg_color=defect_color))
    device.add_element(Lightbox("lo01p_defect_2channel", 354, 715, SmaltaPage.LO01P, "НЕИСПРАВНОСТЬ\nII КАНАЛ", bg_color=defect_color))
    device.add_element(Lightbox("lo01p_defect_3channel", 396, 714, SmaltaPage.LO01P, "НЕИСПРАВНОСТЬ\nIII КАНАЛ", bg_color=defect_color))
    device.add_element(Lightbox("lo01p_defect_4channel", 441, 714, SmaltaPage.LO01P, "НЕИСПРАВНОСТЬ\nIV КАНАЛ", bg_color=defect_color))
    device.add_element(Lightbox("lo01p_1cooler", 484, 714, SmaltaPage.LO01P, "ВЕНТИЛЯТОР I"))

    # Lightboxes (Status)
    device.add_element(Lightbox("lo01p_glow_on", 310, 802, SmaltaPage.LO01P, "НАКАЛ\nВКЛЮЧЕН"))
    device.add_element(Lightbox("lo01p_simulator", 353, 802, SmaltaPage.LO01P, "ИМИТАТОР"))
    device.add_element(Lightbox("lo01p_modulation", 441, 801, SmaltaPage.LO01P, "МОДУЛЯЦИЯ"))
    device.add_element(Lightbox("lo01p_2cooler", 484, 801, SmaltaPage.LO01P, "ВЕНТИЛЯТОР II"))

    # Thumblers at bottom
    device.add_element(Thumbler(
        "lo01p_thumbler_simulator", 582, 385, SmaltaPage.LO01P,
        dependency_actions=[DependencyAction(DependencyType.REPLACE, "lo01p_simulator", {0: 0, 1: 1})]
    ))
    device.add_element(Thumbler("lo01p_thumbler_antenna_leftside", 584, 662, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_antenna_rightside", 586, 752, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_light", 656, 753, SmaltaPage.LO01P))

    # BigButtons at bottom
    btn_glow_on_deps = [
        DependencyAction(DependencyType.REPLACE, "lo01p_glow_on", {1: 1}),
        DependencyAction(DependencyType.REPLACE, "lo01r_lamp_heating", {1: 1}),
        DependencyAction(DependencyType.REPLACE, "lo01r_lamp_heating", {1: 0}, delayed_time_seconds=5),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_1channel", {1: 1}, delayed_time_seconds=10),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_2channel", {1: 1}, delayed_time_seconds=10),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_3channel", {1: 1}, delayed_time_seconds=10),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_4channel", {1: 1}, delayed_time_seconds=10),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_1channel_arrow", {1: 1}, delayed_time_seconds=10),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_2channel_arrow", {1: 1}, delayed_time_seconds=10),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_3channel_arrow", {1: 1}, delayed_time_seconds=10),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_4channel_arrow", {1: 1}, delayed_time_seconds=10),
    ]
    device.add_element(BigButton(
        "lo01p_button_reciever_glow_on", 581, 463, SmaltaPage.LO01P,
        dependency_actions=btn_glow_on_deps,
        dependency_secure_element_name="lo01p_button_reciever_glow_off"
    ))

    btn_glow_off_deps = [
        DependencyAction(DependencyType.REPLACE, "lo01p_glow_on", {1: 0}, delayed_time_seconds=8),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_1channel_arrow", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_2channel_arrow", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_3channel_arrow", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_4channel_arrow", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_1channel", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_2channel", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_3channel", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_reciever_4channel", {1: 0}),
    ]
    device.add_element(BigButton(
        "lo01p_button_reciever_glow_off", 655, 462, SmaltaPage.LO01P,
        dependency_actions=btn_glow_off_deps,
        dependency_secure_element_name="lo01p_button_reciever_glow_on"
    ))

    btn_tx_on_deps = [
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_1channel", {1: 1}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_2channel", {1: 1}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_3channel", {1: 1}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_4channel", {1: 1}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_1channel_arrow", {1: 5}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_2channel_arrow", {1: 5}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_3channel_arrow", {1: 5}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_4channel_arrow", {1: 5}),
    ]
    device.add_element(BigButton(
        "lo01p_button_transmitter_on", 580, 554, SmaltaPage.LO01P,
        dependency_actions=btn_tx_on_deps,
        dependency_secure_element_name="lo01p_button_transmitter_off"
    ))

    btn_tx_off_deps = [
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_1channel", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_2channel", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_3channel", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_4channel", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_1channel_arrow", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_2channel_arrow", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_3channel_arrow", {1: 0}),
        DependencyAction(DependencyType.REPLACE, "lo01p_transmitter_4channel_arrow", {1: 0}),
    ]
    device.add_element(BigButton(
        "lo01p_button_transmitter_off", 655, 554, SmaltaPage.LO01P,
        dependency_actions=btn_tx_off_deps,
        dependency_secure_element_name="lo01p_button_transmitter_on"
    ))

    device.add_element(BigButton("lo01p_button_control", 656, 371, SmaltaPage.LO01P))
    device.add_element(BigButton("lo01p_button_eject", 655, 645, SmaltaPage.LO01P))

    # Top right thumblers
    device.add_element(Thumbler("lo01p_thumbler_power", 68, 1178, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_cold", 67, 1226, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_autosarpp", 69, 1278, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_aircontrol", 70, 1329, SmaltaPage.LO01P))

    # Bottom right thumblers
    device.add_element(Thumbler("lo01p_thumbler_cooler", 636, 1170, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_light_maintance", 637, 1217, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_light_advanced", 635, 1262, SmaltaPage.LO01P))
    device.add_element(Thumbler("lo01p_thumbler_light_table", 636, 1308, SmaltaPage.LO01P))

    # Gauge arrows (Left - Receiver current)
    device.add_element(GaugeArrow("lo01p_reciever_1channel_arrow", 96, 127, SmaltaPage.LO01P, startup_rotation=35))
    device.add_element(GaugeArrow("lo01p_reciever_2channel_arrow", 288, 127, SmaltaPage.LO01P, startup_rotation=35))
    device.add_element(GaugeArrow("lo01p_reciever_3channel_arrow", 478, 128, SmaltaPage.LO01P, startup_rotation=35))
    device.add_element(GaugeArrow("lo01p_reciever_4channel_arrow", 665, 128, SmaltaPage.LO01P, startup_rotation=35))

    # Gauge arrows (Right - Transmitter current)
    device.add_element(GaugeArrow("lo01p_transmitter_1channel_arrow", 103, 1004, SmaltaPage.LO01P, startup_rotation=35))
    device.add_element(GaugeArrow("lo01p_transmitter_2channel_arrow", 294, 1004, SmaltaPage.LO01P, startup_rotation=35))
    device.add_element(GaugeArrow("lo01p_transmitter_3channel_arrow", 479, 1003, SmaltaPage.LO01P, startup_rotation=35))
    device.add_element(GaugeArrow("lo01p_transmitter_4channel_arrow", 667, 999, SmaltaPage.LO01P, startup_rotation=35))

    # ---------------- PAGE LO01R ----------------
    device.add_element(Thumbler("lo01r_reciever_1channel", 400, 104, SmaltaPage.LO01R))
    device.add_element(Thumbler("lo01r_reciever_2channel", 400, 168, SmaltaPage.LO01R))
    device.add_element(Thumbler("lo01r_reciever_3channel", 398, 236, SmaltaPage.LO01R))
    device.add_element(Thumbler("lo01r_reciever_4channel", 395, 303, SmaltaPage.LO01R))

    device.add_element(Thumbler("lo01r_transmitter_1channel", 394, 366, SmaltaPage.LO01R))
    device.add_element(Thumbler("lo01r_transmitter_2channel", 396, 435, SmaltaPage.LO01R))
    device.add_element(Thumbler("lo01r_transmitter_3channel", 394, 507, SmaltaPage.LO01R))
    device.add_element(Thumbler("lo01r_transmitter_4channel", 393, 576, SmaltaPage.LO01R))

    device.add_element(Lamp("lo01r_lamp_network_27v", 109, 829, SmaltaPage.LO01R))
    device.add_element(Lamp("lo01r_lamp_equal", 258, 786, SmaltaPage.LO01R))
    device.add_element(Lamp("lo01r_lamp_+10v", 257, 878, SmaltaPage.LO01R))
    device.add_element(Lamp("lo01r_lamp_heating", 575, 836, SmaltaPage.LO01R))

    device.add_element(Thumbler("lo01r_antenna_equal", 309, 788, SmaltaPage.LO01R))
    device.add_element(RotateStepWheel("lo01r_modulation", 430, 806, SmaltaPage.LO01R, startup_rotation=30, rotation_step_degrees=30, max_value=5))

    # ---------------- PAGE LO01I_LO01K ----------------
    device.add_element(Thumbler("lo01i_thumbler_1generator", 301, 369, SmaltaPage.LO01I_LO01K))

    def make_gen_deps():
        return [
            DependencyAction(DependencyType.ADD, "lo01p_reciever_1channel_arrow", {0: -5, 1: 5}),
            DependencyAction(DependencyType.ADD, "lo01p_reciever_2channel_arrow", {0: -5, 1: 5}),
            DependencyAction(DependencyType.ADD, "lo01p_reciever_3channel_arrow", {0: -5, 1: 5}),
            DependencyAction(DependencyType.ADD, "lo01p_reciever_4channel_arrow", {0: -5, 1: 5}),
            DependencyAction(DependencyType.ADD, "lo01p_transmitter_1channel_arrow", {0: 2, 1: -2}),
            DependencyAction(DependencyType.ADD, "lo01p_transmitter_2channel_arrow", {0: 2, 1: -2}),
            DependencyAction(DependencyType.ADD, "lo01p_transmitter_3channel_arrow", {0: 2, 1: -2}),
            DependencyAction(DependencyType.ADD, "lo01p_transmitter_4channel_arrow", {0: 2, 1: -2}),
        ]

    device.add_element(Thumbler("lo01i_thumbler_2generator", 302, 523, SmaltaPage.LO01I_LO01K, dependency_actions=make_gen_deps()))
    device.add_element(Thumbler("lo01i_thumbler_3generator", 443, 364, SmaltaPage.LO01I_LO01K, dependency_actions=make_gen_deps()))
    device.add_element(Thumbler("lo01i_thumbler_4generator", 439, 524, SmaltaPage.LO01I_LO01K, dependency_actions=make_gen_deps()))

    device.add_element(Thumbler("lo01k_modulation_13channel", 262, 1140, SmaltaPage.LO01I_LO01K))
    device.add_element(Thumbler("lo01k_modulation_24channel", 264, 1237, SmaltaPage.LO01I_LO01K))

    return device


def get_smalta_algorithms() -> List[Algorithm]:
    # 1. Подготовка к включению
    prep_start = {
        "lo01p_thumbler_simulator": 1,
        "lo01p_simulator": 1,
        "lo01r_modulation": 4
    }
    prep_end = {
        "lo01p_thumbler_light": 1,
        "lo01p_thumbler_1channel": 1,
        "lo01p_thumbler_2channel": 1,
        "lo01p_thumbler_3channel": 1,
        "lo01p_thumbler_4channel": 1,
        "lo01p_thumbler_simulator": 0,
        "lo01r_reciever_1channel": 1,
        "lo01r_reciever_2channel": 1,
        "lo01r_reciever_3channel": 1,
        "lo01r_reciever_4channel": 1,
        "lo01r_transmitter_1channel": 1,
        "lo01r_transmitter_2channel": 1,
        "lo01r_transmitter_3channel": 1,
        "lo01r_transmitter_4channel": 1,
        "lo01r_antenna_equal": 1,
        "lo01r_modulation": 0,
        "lo01k_modulation_13channel": 1,
        "lo01k_modulation_24channel": 1
    }
    prep_actions = [
        Action(ActionName.CLICK, "lo01p_thumbler_light", "Установите данный тумблер в положение ПОДСВЕТ", 1),
        Action(ActionName.CLICK, "lo01p_thumbler_1channel", "Установите данный тумблер в положение I КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01p_thumbler_2channel", "Установите данный тумблер в положение II КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01p_thumbler_3channel", "Установите данный тумблер в положение III КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01p_thumbler_4channel", "Установите данный тумблер в положение IV КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01p_thumbler_simulator", "Установите данный тумблер в положение ОТКЛ.", 0),
        Action(ActionName.CLICK, "lo01r_reciever_1channel", "Установите данный тумблер в положение I КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_reciever_2channel", "Установите данный тумблер в положение II КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_reciever_3channel", "Установите данный тумблер в положение III КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_reciever_4channel", "Установите данный тумблер в положение IV КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_transmitter_1channel", "Установите данный тумблер в положение I КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_transmitter_2channel", "Установите данный тумблер в положение II КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_transmitter_3channel", "Установите данный тумблер в положение III КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_transmitter_4channel", "Установите данный тумблер в положение IV КАНАЛ", 1),
        Action(ActionName.CLICK, "lo01r_antenna_equal", "Установите данный тумблер в положение Эквивалент", 1),
        Action(ActionName.CLICK, "lo01r_modulation", "Установите данный переключатель в положение ОТКЛ. (0)", 0),
        Action(ActionName.CLICK, "lo01k_modulation_13channel", "Установите данный тумблер в положение ВКЛ.", 1),
        Action(ActionName.CLICK, "lo01k_modulation_24channel", "Установите данный тумблер в положение ВКЛ.", 1),
    ]
    algo_prep = Algorithm("Подготовка изделия ЛО01 к включению", prep_start, prep_end, prep_actions)

    # 2. Включение изделия ЛО01
    launch_start = {
        "lo01p_1cooler": 1,
        "lo01p_2cooler": 1,
        "lo01r_lamp_network_27v": 1,
        "lo01r_lamp_equal": 1,
        "lo01r_lamp_+10v": 1,
        "lo01p_thumbler_light": 1,
        "lo01p_thumbler_1channel": 1,
        "lo01p_thumbler_2channel": 1,
        "lo01p_thumbler_3channel": 1,
        "lo01p_thumbler_4channel": 1,
        "lo01p_thumbler_simulator": 0,
        "lo01r_reciever_1channel": 1,
        "lo01r_reciever_2channel": 1,
        "lo01r_reciever_3channel": 1,
        "lo01r_reciever_4channel": 1,
        "lo01r_transmitter_1channel": 1,
        "lo01r_transmitter_2channel": 1,
        "lo01r_transmitter_3channel": 1,
        "lo01r_transmitter_4channel": 1,
        "lo01r_antenna_equal": 1,
        "lo01r_modulation": 0,
        "lo01k_modulation_13channel": 1,
        "lo01k_modulation_24channel": 1,
    }
    launch_actions = [
        Action(ActionName.CLICK, "lo01p_button_reciever_glow_on", "Включите ПРОГРЕВ", 1),
        Action(ActionName.IDLE, "lo01r_lamp_heating", "Дождитесь окончания прогрева (лампа погаснет)", 0, use_in_examine_check=True),
        Action(ActionName.IDLE, "lo01p_reciever_1channel", "Дождитесь включения высокого напряжения (загорятся табло)", 1),
        Action(ActionName.INFO, "lo01p_reciever_1channel_arrow", "Заметьте: стрелки приборов 'ПРИЕМ' показывают значение менее 20 мкА"),
        Action(ActionName.CLICK, "lo01p_button_transmitter_on", "Теперь включите передатчик", 1),
        Action(ActionName.INFO, "lo01p_transmitter_1channel_arrow", "Заметьте: стрелки приборов 'ПЕРЕДАЧА' показывают более 10 мкА"),
        Action(ActionName.CLICK, "lo01p_thumbler_simulator", "Включите имитатор", 1),
        Action(ActionName.CLICK, "lo01i_thumbler_2generator", "Включите генератор 2", 1),
        Action(ActionName.INFO, "lo01p_reciever_1channel_arrow", "Заметьте: стрелки приборов 'ПРИЕМ' показывают завышенные значения"),
        Action(ActionName.INFO, "lo01p_transmitter_1channel_arrow", "А стрелки 'ПЕРЕДАЧА' отклонились от первоначального значения"),
    ]
    algo_launch = Algorithm("Включение изделия ЛО01", launch_start, {}, launch_actions)

    # 3. Выключение изделия ЛО01
    stop_start = dict(launch_start)
    stop_start.update({
        "lo01p_button_reciever_glow_on": 1,
        "lo01p_glow_on": 1,
        "lo01r_lamp_heating": 0,
        "lo01p_reciever_1channel": 1,
        "lo01p_reciever_2channel": 1,
        "lo01p_reciever_3channel": 1,
        "lo01p_reciever_4channel": 1,
        "lo01p_transmitter_1channel": 1,
        "lo01p_transmitter_2channel": 1,
        "lo01p_transmitter_3channel": 1,
        "lo01p_transmitter_4channel": 1,
        "lo01p_reciever_1channel_arrow": 6,
        "lo01p_reciever_2channel_arrow": 6,
        "lo01p_reciever_3channel_arrow": 6,
        "lo01p_reciever_4channel_arrow": 6,
        "lo01p_button_transmitter_on": 1,
        "lo01p_transmitter_1channel_arrow": 3,
        "lo01p_transmitter_2channel_arrow": 3,
        "lo01p_transmitter_3channel_arrow": 3,
        "lo01p_transmitter_4channel_arrow": 3,
        "lo01p_thumbler_simulator": 1,
        "lo01p_simulator": 1,
        "lo01i_thumbler_2generator": 1,
    })
    stop_actions = [
        Action(ActionName.CLICK, "lo01p_thumbler_simulator", "Отключите имитатор", 0),
        Action(ActionName.CLICK, "lo01p_button_transmitter_off", "Отключите передатчик", 1),
        Action(ActionName.CLICK, "lo01p_button_reciever_glow_off", "Отключите приемник", 1),
        Action(ActionName.IDLE, "lo01p_glow_on", "Дождитесь выключения накала", 0, use_in_examine_check=True),
        Action(ActionName.CLICK, "lo01i_thumbler_2generator", "Выключите генератор 2", 0),
    ]
    algo_stop = Algorithm("Выключение изделия ЛО01", stop_start, {}, stop_actions)

    return [algo_prep, algo_launch, algo_stop]
