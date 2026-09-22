from devices.device_base import DeviceBase
from devices.smalta import create_smalta_device, get_smalta_algorithms, SmaltaPage
from devices.rls_onc import create_rls_device, get_rls_algorithms, RlsPage

__all__ = [
    "DeviceBase",
    "create_smalta_device",
    "get_smalta_algorithms",
    "SmaltaPage",
    "create_rls_device",
    "get_rls_algorithms",
    "RlsPage",
]
