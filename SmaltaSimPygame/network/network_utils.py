import os
import sys
import socket
import ipaddress
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

def get_local_interfaces() -> List[Dict[str, Any]]:
    """
    Возвращает список всех активных IPv4 сетевых интерфейсов машины
    с разделением на физические (Ethernet/Wi-Fi) и виртуальные (VPN, Hyper-V, Docker).
    """
    interfaces = []

    # 1. Попытка через Windows API (iphlpapi.dll -> GetAdaptersInfo)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class IP_ADDR_STRING(ctypes.Structure):
                pass
            IP_ADDR_STRING._fields_ = [
                ('Next', ctypes.POINTER(IP_ADDR_STRING)),
                ('IpAddress', ctypes.c_char * 16),
                ('IpMask', ctypes.c_char * 16),
                ('Context', wintypes.DWORD)
            ]

            class IP_ADAPTER_INFO(ctypes.Structure):
                pass
            IP_ADAPTER_INFO._fields_ = [
                ('Next', ctypes.POINTER(IP_ADAPTER_INFO)),
                ('ComboIndex', wintypes.DWORD),
                ('AdapterName', ctypes.c_char * 260),
                ('Description', ctypes.c_char * 132),
                ('AddressLength', wintypes.UINT),
                ('Address', ctypes.c_byte * 8),
                ('Index', wintypes.DWORD),
                ('Type', wintypes.UINT),
                ('DhcpEnabled', wintypes.UINT),
                ('CurrentIpAddress', ctypes.c_void_p),
                ('IpAddressList', IP_ADDR_STRING),
                ('GatewayList', IP_ADDR_STRING),
                ('DhcpServer', IP_ADDR_STRING),
                ('HaveWins', wintypes.BOOL),
                ('PrimaryWinsServer', IP_ADDR_STRING),
                ('SecondaryWinsServer', IP_ADDR_STRING),
                ('LeaseObtained', wintypes.LONG),
                ('LeaseExpires', wintypes.LONG),
            ]

            GetAdaptersInfo = ctypes.windll.iphlpapi.GetAdaptersInfo
            buflen = wintypes.ULONG(0)
            GetAdaptersInfo(None, ctypes.byref(buflen))
            if buflen.value > 0:
                buf = ctypes.create_string_buffer(buflen.value)
                pAdapter = ctypes.cast(buf, ctypes.POINTER(IP_ADAPTER_INFO))
                if GetAdaptersInfo(pAdapter, ctypes.byref(buflen)) == 0:
                    curr = pAdapter
                    while curr:
                        a = curr.contents
                        desc = a.Description.decode('utf-8', errors='ignore').strip()
                        ip = a.IpAddressList.IpAddress.decode('utf-8', errors='ignore').strip()
                        mask = a.IpAddressList.IpMask.decode('utf-8', errors='ignore').strip()
                        gw = a.GatewayList.IpAddress.decode('utf-8', errors='ignore').strip()

                        if ip and ip != '0.0.0.0' and not ip.startswith('127.'):
                            desc_lower = desc.lower()
                            # Windows Mobile Hotspot uses "Microsoft Wi-Fi Direct Virtual Adapter"
                            is_hotspot = ('wi-fi direct' in desc_lower) or ('direct' in desc_lower and 'wi-fi' in desc_lower) or ip.startswith('192.168.137.')
                            is_virtual = False
                            if not is_hotspot and any(v in desc_lower for v in [
                                'virtual', 'hyper-v', 'vmware', 'vbox', 'tunnel',
                                'tap', 'happ', 'xray', 'wsl', 'loopback', 'vethernet', 'tailscale', 'zerotier'
                            ]):
                                is_virtual = True
                            if ip.startswith('169.254.'):
                                is_virtual = True

                            has_gateway = (gw != '0.0.0.0' and gw != '')

                            try:
                                net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                                broadcast = str(net.broadcast_address)
                            except Exception:
                                broadcast = "255.255.255.255"

                            interfaces.append({
                                "desc": desc,
                                "ip": ip,
                                "mask": mask,
                                "gw": gw,
                                "broadcast": broadcast,
                                "is_virtual": is_virtual,
                                "has_gateway": has_gateway
                            })
                        curr = a.Next
        except Exception:
            pass

    # 2. Запасной вариант через стандартный socket.gethostbyname_ex
    if not interfaces:
        try:
            hostname = socket.gethostname()
            all_ips = socket.gethostbyname_ex(hostname)[2]
            for ip in all_ips:
                if ip and not ip.startswith('127.') and ip != '0.0.0.0':
                    is_virtual = ip.startswith('169.254.') or ip.startswith('172.19.') or ip.startswith('172.18.')
                    # Примерный broadcast /24
                    parts = ip.split('.')
                    bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255" if len(parts) == 4 else "255.255.255.255"
                    interfaces.append({
                        "desc": "Сетевой интерфейс",
                        "ip": ip,
                        "mask": "255.255.255.0",
                        "gw": "",
                        "broadcast": bcast,
                        "is_virtual": is_virtual,
                        "has_gateway": not is_virtual
                    })
        except Exception:
            pass

    # Сортировка: сначала реальные с шлюзом, потом остальные реальные, в конце виртуальные
    interfaces.sort(key=lambda x: (x["is_virtual"], not x["has_gateway"]))
    return interfaces

def get_best_ip_for_peer(peer_ip: str) -> Optional[str]:
    """
    Определяет локальный IP-адрес текущей машины, через который будет
    осуществляться маршрутизация к указанному IP (peer_ip).
    """
    if not peer_ip or peer_ip in ("127.0.0.1", "localhost"):
        return "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((peer_ip, 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def get_primary_lan_ip() -> str:
    """
    Возвращает наиболее вероятный физический локальный IP (Ethernet / Wi-Fi).
    Игнорирует виртуальные адаптеры (VPN, Hyper-V, WSL).
    """
    ifaces = get_local_interfaces()
    for iface in ifaces:
        if not iface["is_virtual"] and iface["has_gateway"]:
            return iface["ip"]
    for iface in ifaces:
        if not iface["is_virtual"]:
            return iface["ip"]
    if ifaces:
        return ifaces[0]["ip"]
    return "127.0.0.1"

def ping_server(ip: str, port: int = 8000, timeout: float = 0.8) -> bool:
    """
    Проверяет доступность сервера преподавателя по TCP/HTTP /api/ping.
    Валидирует, что ответ возвращает именно VkmExamServer.
    """
    if not ip:
        return False
    # Быстрая проверка TCP порта
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
    except Exception:
        return False

    # HTTP проверка заголовка/тела
    try:
        url = f"http://{ip}:{port}/api/ping"
        req = urllib.request.Request(url, headers={"User-Agent": "SmaltaSim-Client"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = resp.read(256).decode('utf-8', errors='ignore')
                return ("VkmExamServer" in body) or ("status" in body)
            return False
    except Exception:
        return False

def get_arp_cached_ips(filter_prefix: Optional[str] = None) -> List[str]:
    """
    Возвращает список актуальных IP-адресов устройств в локальной сети из таблицы ARP Windows.
    Позволяет мгновенно обнаружить сервер преподавателя без длительного сканирования подсети.
    """
    import subprocess
    import re
    found_ips = []
    try:
        res = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=1.5)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                line = line.strip()
                match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                if match:
                    ip = match.group(1)
                    # Исключаем широковещательные, мультикаст и спец-адреса
                    if ip.startswith(('224.', '239.', '255.', '127.', '0.')) or ip.endswith('.255'):
                        continue
                    if filter_prefix and not ip.startswith(filter_prefix):
                        continue
                    if ip not in found_ips:
                        found_ips.append(ip)
    except Exception:
        pass
    return found_ips

def get_subnet_candidate_ips(ip: str, mask: str = "255.255.255.0", max_hosts: int = 512) -> List[str]:
    """
    Генерирует список IP-адресов для сканирования локальной подсети (/24 или /23).
    """
    try:
        net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        if net.num_addresses > max_hosts:
            # Если маска слишком широкая (/16), сужаем до /24 вокруг текущего IP
            parts = ip.split('.')
            if len(parts) == 4:
                net = ipaddress.IPv4Network(f"{parts[0]}.{parts[1]}.{parts[2]}.0/24", strict=False)
        hosts = [str(h) for h in net.hosts() if str(h) != ip]
        return hosts
    except Exception:
        parts = ip.split('.')
        if len(parts) == 4:
            base = f"{parts[0]}.{parts[1]}.{parts[2]}"
            return [f"{base}.{i}" for i in range(1, 255) if f"{base}.{i}" != ip]
        return []
