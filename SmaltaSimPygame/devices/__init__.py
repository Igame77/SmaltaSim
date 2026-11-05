from devices.device_base import DeviceBase
from devices.smalta import create_smalta_device, get_smalta_algorithms, SmaltaPage
from devices.rls_onc import create_rls_device, get_rls_algorithms, RlsPage
from devices.sorbtia import create_sorbtia_device, get_sorbtia_algorithms, SorbtiaPage
from devices.fasol import create_fasol_device, get_fasol_algorithms, FasolPage
from devices.bereza import create_bereza_device, get_bereza_algorithms, BerezaPage
from devices.azalia import create_azalia_device, get_azalia_algorithms, AzaliaPage

__all__ = [
    "DeviceBase",
    "create_smalta_device",
    "get_smalta_algorithms",
    "SmaltaPage",
    "create_rls_device",
    "get_rls_algorithms",
    "RlsPage",
    "create_sorbtia_device",
    "get_sorbtia_algorithms",
    "SorbtiaPage",
    "create_fasol_device",
    "get_fasol_algorithms",
    "FasolPage",
    "create_bereza_device",
    "get_bereza_algorithms",
    "BerezaPage",
    "create_azalia_device",
    "get_azalia_algorithms",
    "AzaliaPage",
]
