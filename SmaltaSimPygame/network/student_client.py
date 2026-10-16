import socket
import threading
import time
import json
import urllib.request
import urllib.error
import queue
from typing import Optional, Callable, Dict, Any, List

from network.exam_protocol import (
    DEFAULT_SERVER_PORT, DEFAULT_DISCOVERY_PORT,
    DISCOVERY_MAGIC_REQUEST, DISCOVERY_MAGIC_RESPONSE,
    StudentStatus, EventType, serialize_json, deserialize_json
)
from network.network_utils import get_local_interfaces, ping_server

class StudentClient:
    def __init__(self, server_ip: str = "127.0.0.1", server_port: int = DEFAULT_SERVER_PORT):
        self.server_ip = server_ip
        self.server_port = server_port
        self.base_url = f"http://{server_ip}:{server_port}"
        self.student_id: Optional[str] = None
        self.full_name: str = ""
        self.group: str = ""
        self.pc_name: str = socket.gethostname()
        self.is_connected: bool = False
        self.is_logged_in: bool = False
        self.is_exam_started_by_server: bool = False

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._queue = queue.Queue()
        self.incoming_commands = queue.Queue()
        self._cached_telemetry: Dict[str, Any] = {}
        self._last_heartbeat_time = 0.0
        self._heartbeat_interval = 1.0

        # Callbacks
        self.on_command_callback: Optional[Callable[[str, Any], None]] = None
        self.on_connection_change: Optional[Callable[[bool], None]] = None

    @staticmethod
    def discover_server(timeout: float = 1.2, port: int = DEFAULT_DISCOVERY_PORT) -> Optional[tuple[str, int]]:
        """
        Ищет сервер преподавателя в локальной сети через UDP Broadcast
        по всем активным сетевым интерфейсам.
        """
        sockets = []
        msg = DISCOVERY_MAGIC_REQUEST.encode('utf-8')
        try:
            ifaces = get_local_interfaces()
            for iface in ifaces:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.settimeout(timeout)
                    s.bind((iface['ip'], 0))
                    s.sendto(msg, (iface['broadcast'], port))
                    s.sendto(msg, ('255.255.255.255', port))
                    sockets.append(s)
                except Exception:
                    pass

            # Запасной общий сокет
            try:
                s_def = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s_def.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s_def.settimeout(timeout)
                s_def.sendto(msg, ('<broadcast>', port))
                s_def.sendto(msg, ('255.255.255.255', port))
                sockets.append(s_def)
            except Exception:
                pass

            deadline = time.time() + timeout
            while time.time() < deadline:
                for s in sockets:
                    try:
                        s.settimeout(0.15)
                        data, addr = s.recvfrom(1024)
                        resp = data.decode('utf-8', errors='ignore').strip()
                        if resp.startswith(DISCOVERY_MAGIC_RESPONSE) or resp.startswith("SmaltaSim_TEACHER_BEACON"):
                            parts = resp.split(':')
                            found_ip = addr[0]
                            found_port = DEFAULT_SERVER_PORT
                            if len(parts) >= 3:
                                found_ip = parts[1]
                                found_port = int(parts[2])
                            return (found_ip, found_port)
                    except Exception:
                        continue
        finally:
            for s in sockets:
                try:
                    s.close()
                except Exception:
                    pass
        return None

    def check_connection(self) -> bool:
        """Проверяет доступность сервера через /api/ping."""
        return ping_server(self.server_ip, self.server_port, timeout=1.5)

    def set_server(self, ip: str, port: int = DEFAULT_SERVER_PORT):
        self.server_ip = ip
        self.server_port = port
        self.base_url = f"http://{ip}:{port}"

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _http_post(self, path: str, data: Dict[str, Any], timeout: float = 3.0) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode('utf-8')
                return json.loads(raw)
        except Exception:
            return None

    def _http_post_binary(self, path: str, raw_bytes: bytes, timeout: float = 5.0) -> bool:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url,
            data=raw_bytes,
            headers={'Content-Type': 'image/jpeg'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def login_sync(
        self,
        full_name: str,
        group: str,
        pc_name: str,
        device_name: str,
        algorithm_name: str,
        max_time_seconds: float,
        total_steps: int
    ) -> bool:
        self.full_name = full_name
        self.group = group
        self.pc_name = pc_name

        payload = {
            "full_name": full_name,
            "group": group,
            "pc_name": pc_name,
            "device_name": device_name,
            "algorithm_name": algorithm_name,
            "max_time_seconds": max_time_seconds,
            "total_steps": total_steps
        }
        res = self._http_post("/api/students/login", payload, timeout=3.0)
        if res and res.get("status") == "ok":
            self.student_id = res.get("student_id")
            self.is_logged_in = True
            self.is_connected = True
            self.is_exam_started_by_server = bool(res.get("exam_started", False))
            if self.on_connection_change:
                self.on_connection_change(True)
            self.start()
            return True
        else:
            self.is_connected = False
            if self.on_connection_change:
                self.on_connection_change(False)
            return False

    def send_event(self, event_type: EventType, message: str, details: Optional[Dict[str, Any]] = None, is_mistake: bool = False):
        if not self.student_id:
            return
        self._queue.put(("event", {
            "student_id": self.student_id,
            "timestamp": time.time(),
            "event_type": event_type.value if hasattr(event_type, 'value') else str(event_type),
            "message": message,
            "details": details or {},
            "is_mistake": is_mistake
        }))

    def send_screenshot(self, jpeg_bytes: bytes):
        if not self.student_id or not jpeg_bytes:
            return
        self._queue.put(("screenshot", (self.student_id, jpeg_bytes)))

    def queue_heartbeat(
        self,
        progress_pct: float = 0.0,
        completed_steps: int = 0,
        mistakes_count: int = 0,
        elapsed_sec: float = 0.0,
        current_action_desc: str = "",
        score: Optional[int] = None,
        **kwargs
    ):
        if not self.student_id:
            return
        data = {
            "student_id": self.student_id,
            "progress_pct": progress_pct,
            "completed_steps": completed_steps,
            "mistakes_count": mistakes_count,
            "elapsed_sec": elapsed_sec,
            "current_action_desc": current_action_desc,
            "score": score
        }
        self._cached_telemetry = data
        self._queue.put(("heartbeat", data))

    def _worker_loop(self):
        while self._running:
            try:
                # 1. Обработка очереди исходящих сообщений
                try:
                    task_type, payload = self._queue.get(timeout=0.25)
                    if task_type == "event":
                        res = self._http_post(f"/api/students/{self.student_id}/event", payload)
                        if res and not self.is_connected:
                            self.is_connected = True
                            if self.on_connection_change:
                                self.on_connection_change(True)
                    elif task_type == "heartbeat":
                        self._last_heartbeat_time = time.time()
                        res = self._http_post(f"/api/students/{self.student_id}/heartbeat", payload)
                        if res:
                            self._handle_server_response(res)
                            if not self.is_connected:
                                self.is_connected = True
                                if self.on_connection_change:
                                    self.on_connection_change(True)
                        else:
                            if self.is_connected:
                                self.is_connected = False
                                if self.on_connection_change:
                                    self.on_connection_change(False)
                    elif task_type == "screenshot":
                        sid, data = payload
                        self._http_post_binary(f"/api/students/{sid}/screenshot", data)
                    self._queue.task_done()
                except queue.Empty:
                    pass

                # 2. Автоматический опрос heartbeat и команд каждые 1.0 сек
                now = time.time()
                if self.student_id and (now - self._last_heartbeat_time >= self._heartbeat_interval):
                    self._last_heartbeat_time = now
                    payload = dict(self._cached_telemetry)
                    payload["student_id"] = self.student_id
                    res = self._http_post(f"/api/students/{self.student_id}/heartbeat", payload, timeout=2.0)
                    if res:
                        self._handle_server_response(res)
                        if not self.is_connected:
                            self.is_connected = True
                            if self.on_connection_change:
                                self.on_connection_change(True)

            except Exception:
                time.sleep(0.5)

    def _handle_server_response(self, res: Dict[str, Any]):
        commands = res.get("commands", [])
        for cmd in commands:
            cmd_type = cmd.get("type") if isinstance(cmd, dict) else str(cmd)
            payload = cmd.get("payload") if isinstance(cmd, dict) else None

            if cmd_type == "START_EXAM":
                self.is_exam_started_by_server = True

            self.incoming_commands.put((cmd_type, payload))

            if self.on_command_callback:
                try:
                    self.on_command_callback(cmd_type, payload)
                except Exception:
                    pass
