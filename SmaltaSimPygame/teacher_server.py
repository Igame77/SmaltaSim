import os
import sys
import io
import time
import json
import uuid
import socket
import queue
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, List, Optional

from network.exam_protocol import (
    DEFAULT_SERVER_PORT, DEFAULT_DISCOVERY_PORT,
    DISCOVERY_MAGIC_REQUEST, DISCOVERY_MAGIC_RESPONSE,
    StudentStatus, EventType, serialize_json, deserialize_json
)
from network.network_utils import (
    get_local_interfaces, get_best_ip_for_peer, get_primary_lan_ip
)

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exam_data", "screenshots")
ARCHIVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exam_data", "exam_archive.json")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

class StudentSession:
    def __init__(self, data: Dict[str, Any], client_ip: str):
        self.student_id = data.get("student_id") or str(uuid.uuid4())[:8]
        self.full_name = data.get("full_name", "Неизвестный")
        self.group = data.get("group", "-")
        self.pc_name = data.get("pc_name", "ПК")
        self.client_ip = client_ip
        self.device_name = data.get("device_name", "Устройство")
        self.algorithm_name = data.get("algorithm_name", "Алгоритм")
        self.max_time_seconds = float(data.get("max_time_seconds", 600))
        self.total_steps = int(data.get("total_steps", 10))

        self.status = StudentStatus.WAITING
        self.start_time: Optional[float] = None
        self.elapsed_sec: float = 0.0
        self.completed_steps: int = 0
        self.progress_pct: float = 0.0
        self.mistakes_count: int = 0
        self.score: Optional[int] = None
        self.current_action_desc: str = ""

        # Контроль активности и окон
        self.is_focused: bool = True
        self.active_window: str = ""
        self.focus_lost_count: int = 0
        self.total_focus_lost_sec: float = 0.0

        self.last_heartbeat: float = time.time()
        self.last_screenshot_url: Optional[str] = None
        self.last_screenshot_time: Optional[float] = None
        self.screenshots: List[Dict[str, Any]] = []

        self.events: List[Dict[str, Any]] = []
        self.pending_commands: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "full_name": self.full_name,
            "group": self.group,
            "pc_name": self.pc_name,
            "client_ip": self.client_ip,
            "device_name": self.device_name,
            "algorithm_name": self.algorithm_name,
            "max_time_seconds": self.max_time_seconds,
            "total_steps": self.total_steps,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "start_time": self.start_time,
            "elapsed_sec": self.elapsed_sec,
            "completed_steps": self.completed_steps,
            "progress_pct": self.progress_pct,
            "mistakes_count": self.mistakes_count,
            "score": self.score,
            "current_action_desc": self.current_action_desc,
            "is_focused": self.is_focused,
            "active_window": self.active_window,
            "focus_lost_count": self.focus_lost_count,
            "total_focus_lost_sec": self.total_focus_lost_sec,
            "last_heartbeat": self.last_heartbeat,
            "last_screenshot_url": self.last_screenshot_url,
            "last_screenshot_time": self.last_screenshot_time,
            "screenshots_count": len(self.screenshots),
            "events_count": len(self.events)
        }

class ExamServerState:
    def __init__(self):
        self.lock = threading.Lock()
        self.students: Dict[str, StudentSession] = {}
        self.sse_clients: List[queue.Queue] = []

    def broadcast_sse(self, event_type: str, data: Any):
        msg = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        with self.lock:
            dead_clients = []
            for q in self.sse_clients:
                try:
                    q.put_nowait(msg)
                except Exception:
                    dead_clients.append(q)
            for d in dead_clients:
                if d in self.sse_clients:
                    self.sse_clients.remove(d)

    def get_all_students_list(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [s.to_dict() for s in self.students.values()]

    def get_student(self, student_id: str) -> Optional[StudentSession]:
        with self.lock:
            return self.students.get(student_id)

    def add_or_update_student(self, session: StudentSession):
        with self.lock:
            self.students[session.student_id] = session
        self.broadcast_sse("student_update", session.to_dict())

server_state = ExamServerState()

def get_local_ip() -> str:
    return get_primary_lan_ip()

class TeacherHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        # Отключаем спам в консоль
        pass

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_dashboard_html()
        elif path == "/api/ping":
            self._send_json({"status": "ok", "app": "VkmExamServer", "version": "2.2.0"})
        elif path == "/api/stream":
            self._serve_sse_stream()
        elif path == "/api/students":
            self._send_json({"students": server_state.get_all_students_list()})
        elif path.startswith("/api/students/") and path.endswith("/events"):
            sid = path.split("/")[3]
            st = server_state.get_student(sid)
            if st:
                with server_state.lock:
                    self._send_json({"events": st.events})
            else:
                self._send_json({"error": "Student not found"}, 404)
        elif path.startswith("/api/students/") and path.endswith("/screenshots"):
            sid = path.split("/")[3]
            st = server_state.get_student(sid)
            if st:
                with server_state.lock:
                    self._send_json({"screenshots": st.screenshots})
            else:
                self._send_json({"error": "Student not found"}, 404)
        elif path.startswith("/api/screenshots/"):
            # /api/screenshots/<student_id>/<filename>
            parts = path.strip("/").split("/")
            if len(parts) >= 4:
                sid, fname = parts[2], parts[3]
                file_path = os.path.join(SCREENSHOTS_DIR, sid, fname)
                if os.path.isfile(file_path):
                    with open(file_path, "rb") as f:
                        img_data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(img_data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(img_data)
                    return
            self.send_response(404)
            self.end_headers()
        elif path == "/api/export/csv":
            self._serve_csv_export()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))

        if path == "/api/students/login":
            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            st = StudentSession(data, self.client_address[0])
            server_state.add_or_update_student(st)
            self._send_json({
                "status": "ok",
                "student_id": st.student_id,
                "exam_started": st.status == StudentStatus.ACTIVE
            })

        elif path.startswith("/api/students/") and path.endswith("/heartbeat"):
            sid = path.split("/")[3]
            st = server_state.get_student(sid)
            if not st:
                self._send_json({"error": "Unknown student"}, 404)
                return

            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)

            with server_state.lock:
                st.last_heartbeat = time.time()
                st.progress_pct = float(data.get("progress_pct", st.progress_pct))
                st.completed_steps = int(data.get("completed_steps", st.completed_steps))
                st.mistakes_count = int(data.get("mistakes_count", st.mistakes_count))
                st.is_focused = bool(data.get("is_focused", True))
                st.active_window = str(data.get("active_window", ""))
                st.elapsed_sec = float(data.get("elapsed_sec", st.elapsed_sec))
                st.current_action_desc = str(data.get("current_action_desc", st.current_action_desc))
                if data.get("score") is not None:
                    st.score = int(data["score"])

                if not st.is_focused and st.status == StudentStatus.ACTIVE:
                    st.status = StudentStatus.FOCUS_LOST
                elif st.is_focused and st.status == StudentStatus.FOCUS_LOST:
                    st.status = StudentStatus.ACTIVE

                cmds_to_send = list(st.pending_commands)
                st.pending_commands.clear()

            server_state.broadcast_sse("student_update", st.to_dict())
            self._send_json({"status": "ok", "commands": cmds_to_send})

        elif path.startswith("/api/students/") and path.endswith("/event"):
            sid = path.split("/")[3]
            st = server_state.get_student(sid)
            if not st:
                self._send_json({"error": "Unknown student"}, 404)
                return

            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)

            with server_state.lock:
                evt = {
                    "id": str(uuid.uuid4())[:6],
                    "timestamp": data.get("timestamp", time.time()),
                    "event_type": data.get("event_type", "INFO"),
                    "message": data.get("message", ""),
                    "details": data.get("details", {}),
                    "is_mistake": bool(data.get("is_mistake", False))
                }
                st.events.append(evt)

                if evt["event_type"] == "FOCUS_LOST":
                    st.status = StudentStatus.FOCUS_LOST
                    st.focus_lost_count += 1
                elif evt["event_type"] == "FOCUS_GAINED":
                    if st.status == StudentStatus.FOCUS_LOST:
                        st.status = StudentStatus.ACTIVE
                elif evt["event_type"] == "FINISH":
                    st.status = StudentStatus.FINISHED
                    details = data.get("details", {})
                    if details.get("score") is not None:
                        st.score = int(details["score"])
                    if details.get("wrong_actions") is not None:
                        st.mistakes_count = int(details["wrong_actions"])

            server_state.broadcast_sse("student_event", {"student_id": sid, "event": evt})
            server_state.broadcast_sse("student_update", st.to_dict())
            self._send_json({"status": "ok"})

        elif path.startswith("/api/students/") and path.endswith("/screenshot"):
            sid = path.split("/")[3]
            st = server_state.get_student(sid)
            if not st:
                self._send_json({"error": "Unknown student"}, 404)
                return

            img_bytes = self.rfile.read(length)
            ts = int(time.time() * 1000)
            fname = f"shot_{ts}.jpg"
            student_dir = os.path.join(SCREENSHOTS_DIR, sid)
            os.makedirs(student_dir, exist_ok=True)
            fpath = os.path.join(student_dir, fname)

            with open(fpath, "wb") as f:
                f.write(img_bytes)

            shot_url = f"/api/screenshots/{sid}/{fname}"
            with server_state.lock:
                st.last_screenshot_url = shot_url
                st.last_screenshot_time = time.time()
                shot_meta = {
                    "url": shot_url,
                    "timestamp": time.time(),
                    "active_window": st.active_window,
                    "is_focused": st.is_focused
                }
                st.screenshots.append(shot_meta)
                # Храним до 50 последних скриншотов на студента
                if len(st.screenshots) > 50:
                    st.screenshots.pop(0)

            server_state.broadcast_sse("screenshot_update", {
                "student_id": sid,
                "screenshot": shot_meta
            })
            server_state.broadcast_sse("student_update", st.to_dict())
            self._send_json({"status": "ok", "url": shot_url})

        elif path.startswith("/api/students/") and path.endswith("/command"):
            sid = path.split("/")[3]
            st = server_state.get_student(sid)
            if not st:
                self._send_json({"error": "Unknown student"}, 404)
                return

            body = self.rfile.read(length).decode('utf-8')
            data = json.loads(body)
            cmd_type = data.get("command")

            with server_state.lock:
                if cmd_type == "START_EXAM":
                    st.status = StudentStatus.ACTIVE
                    st.start_time = time.time()
                elif cmd_type == "STOP_EXAM":
                    st.status = StudentStatus.STOPPED
                st.pending_commands.append({"type": cmd_type, "payload": data.get("payload")})

            server_state.broadcast_sse("student_update", st.to_dict())
            self._send_json({"status": "ok"})

        elif path == "/api/exam/start_all":
            with server_state.lock:
                for st in server_state.students.values():
                    if st.status == StudentStatus.WAITING:
                        st.status = StudentStatus.ACTIVE
                        st.start_time = time.time()
                        st.pending_commands.append({"type": "START_EXAM"})
            for st in server_state.students.values():
                server_state.broadcast_sse("student_update", st.to_dict())
            self._send_json({"status": "ok"})

        elif path == "/api/exam/stop_all":
            with server_state.lock:
                for st in server_state.students.values():
                    if st.status in (StudentStatus.ACTIVE, StudentStatus.WAITING, StudentStatus.FOCUS_LOST):
                        st.status = StudentStatus.STOPPED
                        st.pending_commands.append({"type": "STOP_EXAM"})
            for st in server_state.students.values():
                server_state.broadcast_sse("student_update", st.to_dict())
            self._send_json({"status": "ok"})

        elif path == "/api/exam/clear":
            with server_state.lock:
                server_state.students.clear()
            server_state.broadcast_sse("reset", {})
            self._send_json({"status": "ok"})

        else:
            self.send_response(404)
            self.end_headers()

    def _serve_sse_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Стартовое заполнение буфера для принудительного сброса в браузерах Chromium/Edge и через прокси
        try:
            self.wfile.write(b": " + b" " * 2048 + b"\n\n")
            self.wfile.write(b": ping\n\n")
            self.wfile.flush()
        except Exception:
            return

        q = queue.Queue()
        with server_state.lock:
            server_state.sse_clients.append(q)

        # Отправляем начальное состояние
        init_data = f"event: init\ndata: {json.dumps({'students': server_state.get_all_students_list()}, ensure_ascii=False)}\n\n"
        try:
            self.wfile.write(init_data.encode('utf-8'))
            self.wfile.flush()
        except Exception:
            with server_state.lock:
                if q in server_state.sse_clients:
                    server_state.sse_clients.remove(q)
            return

        try:
            while True:
                try:
                    msg = q.get(timeout=15.0)
                    self.wfile.write(msg.encode('utf-8'))
                    self.wfile.flush()
                except queue.Empty:
                    # Регулярный keep-alive пинг для исключения таймаута TCP
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with server_state.lock:
                if q in server_state.sse_clients:
                    server_state.sse_clients.remove(q)

    def _serve_csv_export(self):
        output = io.StringIO()
        output.write("\ufeff") # UTF-8 BOM для корректного открытия в Excel
        output.write("ФИО;Группа;Рабочее место;Устройство;Задание;Статус;Оценка;Ошибок;Время (сек);Отвлечений;Секунд вне симулятора\n")

        with server_state.lock:
            for st in server_state.students.values():
                score_str = str(st.score) if st.score is not None else "-"
                output.write(
                    f"{st.full_name};{st.group};{st.pc_name};{st.device_name};"
                    f"{st.algorithm_name};{st.status};{score_str};{st.mistakes_count};"
                    f"{int(st.elapsed_sec)};{st.focus_lost_count};{int(st.total_focus_lost_sec)}\n"
                )

        csv_bytes = output.getvalue().encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f"attachment; filename=exam_results_{int(time.time())}.csv")
        self.send_header("Content-Length", str(len(csv_bytes)))
        self.end_headers()
        self.wfile.write(csv_bytes)

    def _serve_dashboard_html(self):
        ifaces = get_local_interfaces()
        lan_badges = []
        for iface in ifaces:
            if not iface["is_virtual"]:
                desc_l = iface["desc"].lower()
                label = "Ethernet" if ("ethernet" in desc_l or "usb" in desc_l) else ("Wi-Fi" if ("wi-fi" in desc_l or "wireless" in desc_l) else "LAN")
                lan_badges.append(f'<span class="badge-ip" title="{iface["desc"]}">IP ({label}): {iface["ip"]}:{DEFAULT_SERVER_PORT}</span>')
        if not lan_badges:
            lan_badges.append(f'<span class="badge-ip">IP: {get_primary_lan_ip()}:{DEFAULT_SERVER_PORT}</span>')
        ip_badges_html = " ".join(lan_badges)
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vkm.ComplexSim — Экзаменационный мониторинг</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0b0f17;
      --card-bg: rgba(18, 24, 38, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(26, 35, 54, 0.95);
      --primary: #3b82f6;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-dim: #9ca3af;
      --badge-bg: rgba(255, 255, 255, 0.06);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 10% 10%, #111827 0%, #0b0f17 100%);
      color: var(--text);
      min-height: 100vh;
      padding-bottom: 60px;
    }}
    header {{
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 16px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .brand-logo {{
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, #3b82f6, #1d4ed8);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      box-shadow: 0 0 15px rgba(59,130,246,0.5);
    }}
    .brand-text h1 {{
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .brand-text p {{
      font-size: 12px;
      color: var(--text-dim);
    }}
    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .badge-ip {{
      font-family: 'JetBrains Mono', monospace;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #93c5fd;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 13px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
      text-decoration: none;
    }}
    .btn-primary {{
      background: #2563eb;
      color: white;
    }}
    .btn-primary:hover {{ background: #1d4ed8; transform: translateY(-1px); }}
    .btn-success {{
      background: #059669;
      color: white;
    }}
    .btn-success:hover {{ background: #047857; transform: translateY(-1px); }}
    .btn-outline {{
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.15);
      color: var(--text);
    }}
    .btn-outline:hover {{ background: rgba(255,255,255,0.1); }}
    .btn-danger {{
      background: rgba(239, 68, 68, 0.2);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #fca5a5;
    }}
    .btn-danger:hover {{ background: rgba(239, 68, 68, 0.3); }}

    .stats-bar {{
      max-width: 1440px;
      margin: 24px auto 0;
      padding: 0 32px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }}
    .stat-card {{
      background: var(--card-bg);
      backdrop-filter: blur(8px);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .stat-card .label {{
      font-size: 12px;
      color: var(--text-dim);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.05em;
    }}
    .stat-card .value {{
      font-size: 26px;
      font-weight: 800;
    }}

    .container {{
      max-width: 1440px;
      margin: 24px auto;
      padding: 0 32px;
    }}
    .grid-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .grid-header h2 {{
      font-size: 18px;
      font-weight: 700;
    }}

    .students-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 20px;
    }}

    .student-card {{
      background: var(--card-bg);
      backdrop-filter: blur(10px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: all 0.2s ease;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      position: relative;
    }}
    .student-card:hover {{
      transform: translateY(-2px);
      border-color: rgba(255,255,255,0.18);
    }}
    .student-card.focus-lost {{
      border: 2px solid var(--danger);
      box-shadow: 0 0 25px rgba(239, 68, 68, 0.4);
      animation: pulse-danger 2s infinite;
    }}
    @keyframes pulse-danger {{
      0%, 100% {{ box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); }}
      50% {{ box-shadow: 0 0 35px rgba(239, 68, 68, 0.8); }}
    }}

    .card-top {{
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid var(--card-border);
      background: rgba(255,255,255,0.02);
    }}
    .card-user {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .card-user .name {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }}
    .card-user .sub {{
      font-size: 12px;
      color: var(--text-dim);
    }}

    .badge-status {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 4px 8px;
      border-radius: 6px;
      letter-spacing: 0.04em;
    }}
    .status-waiting {{ background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }}
    .status-active {{ background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .status-focus-lost {{ background: rgba(239, 68, 68, 0.25); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.6); }}
    .status-finished {{ background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.4); }}
    .status-stopped {{ background: rgba(107, 114, 128, 0.25); color: #d1d5db; border: 1px solid rgba(107, 114, 128, 0.4); }}

    .card-preview {{
      height: 180px;
      background: #000;
      position: relative;
      cursor: pointer;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .card-preview img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.2s;
    }}
    .card-preview:hover img {{
      transform: scale(1.02);
    }}
    .preview-overlay-info {{
      position: absolute;
      bottom: 8px;
      left: 8px;
      right: 8px;
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      background: rgba(0,0,0,0.7);
      padding: 4px 8px;
      border-radius: 6px;
      backdrop-filter: blur(4px);
    }}
    .alert-window-name {{
      position: absolute;
      top: 8px;
      left: 8px;
      right: 8px;
      background: rgba(239, 68, 68, 0.9);
      color: white;
      font-size: 11px;
      font-weight: 700;
      padding: 6px 10px;
      border-radius: 6px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.5);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .card-body {{
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      flex: 1;
    }}
    .progress-box {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .progress-meta {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--text-dim);
    }}
    .progress-track {{
      height: 8px;
      background: rgba(255,255,255,0.08);
      border-radius: 4px;
      overflow: hidden;
    }}
    .progress-fill {{
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #10b981);
      border-radius: 4px;
      transition: width 0.3s ease;
    }}

    .metrics-row {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      background: rgba(0,0,0,0.25);
      border-radius: 8px;
      padding: 8px 10px;
      text-align: center;
    }}
    .metric-item .val {{
      font-weight: 700;
      font-size: 14px;
    }}
    .metric-item .lbl {{
      font-size: 10px;
      color: var(--text-dim);
      text-transform: uppercase;
    }}

    .card-actions {{
      padding: 12px 16px;
      background: rgba(0,0,0,0.2);
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }}
    .btn-sm {{
      padding: 6px 10px;
      font-size: 12px;
    }}

    /* Modal styles */
    .modal-backdrop {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.85);
      backdrop-filter: blur(10px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}
    .modal-backdrop.active {{
      display: flex;
    }}
    .modal-dialog {{
      background: #111827;
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 16px;
      width: 100%;
      max-width: 900px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 50px rgba(0,0,0,0.7);
      overflow: hidden;
    }}
    .modal-header {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .modal-title {{
      font-size: 18px;
      font-weight: 700;
    }}
    .modal-close {{
      background: transparent;
      border: none;
      color: var(--text-dim);
      font-size: 24px;
      cursor: pointer;
      line-height: 1;
    }}
    .modal-close:hover {{ color: #fff; }}
    .modal-tabs {{
      display: flex;
      background: rgba(0,0,0,0.3);
      border-bottom: 1px solid var(--card-border);
      padding: 0 24px;
      gap: 16px;
    }}
    .modal-tab {{
      padding: 12px 16px;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-dim);
      cursor: pointer;
      border-bottom: 2px solid transparent;
    }}
    .modal-tab.active {{
      color: #3b82f6;
      border-color: #3b82f6;
    }}
    .modal-body {{
      padding: 24px;
      overflow-y: auto;
      flex: 1;
    }}

    .log-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
    }}
    .log-item {{
      background: rgba(255,255,255,0.03);
      padding: 8px 12px;
      border-radius: 6px;
      border-left: 3px solid #3b82f6;
      display: flex;
      justify-content: space-between;
    }}
    .log-item.mistake {{
      border-left-color: var(--danger);
      background: rgba(239,68,68,0.08);
    }}
    .log-item.focus-lost {{
      border-left-color: var(--warning);
      background: rgba(245,158,11,0.08);
    }}

    .shots-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }}
    .shot-card {{
      background: #000;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
    }}
    .shot-card img {{
      width: 100%;
      height: 140px;
      object-fit: cover;
      display: block;
    }}
    .shot-info {{
      padding: 8px;
      font-size: 11px;
      background: rgba(255,255,255,0.03);
      color: var(--text-dim);
    }}

    .empty-state {{
      text-align: center;
      padding: 80px 20px;
      color: var(--text-dim);
    }}
    .empty-state h3 {{
      font-size: 18px;
      margin-bottom: 8px;
      color: #fff;
    }}
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-logo">ВКМ</div>
      <div class="brand-text">
        <h1>Пульт экзаменатора: Комплекс РЭБ / РЛС</h1>
        <p>Мониторинг курсантов в реальном времени • Детализация ошибок • Аннотированные снимки (BBox)</p>
      </div>
    </div>
    <div class="header-actions">
      {ip_badges_html}
      <button id="btn-toggle-all" class="btn btn-success" onclick="toggleAllExams()">▶ Общий старт</button>
      <a href="/api/export/csv" class="btn btn-outline" download>📥 Скачать ведомость (CSV)</a>
      <button class="btn btn-danger" onclick="clearExamData()">Очистить список</button>
    </div>
  </header>

  <section class="stats-bar">
    <div class="stat-card">
      <span class="label">Всего курсантов</span>
      <span class="value" id="stat-total">0</span>
    </div>
    <div class="stat-card">
      <span class="label">Сдают сейчас</span>
      <span class="value" style="color: #6ee7b7;" id="stat-active">0</span>
    </div>
    <div class="stat-card">
      <span class="label">Ошибок зафиксировано</span>
      <span class="value" style="color: #fca5a5;" id="stat-mistakes">0</span>
    </div>
    <div class="stat-card">
      <span class="label">Завершили экзамен</span>
      <span class="value" style="color: #93c5fd;" id="stat-finished">0</span>
    </div>
  </section>

  <main class="container">
    <div class="grid-header">
      <h2>Рабочие места курсантов</h2>
      <span style="font-size: 13px; color: var(--text-dim);" id="grid-meta">Подключение к серверу...</span>
    </div>
    <div class="students-grid" id="students-grid">
      <!-- Сюда вставляются карточки курсантов -->
    </div>
    <div class="empty-state" id="empty-state" style="display: none;">
      <h3>Ожидание подключения курсантов</h3>
      <p>Когда курсанты запустят симулятор и выберут режим «Экзамен», их рабочие места появятся здесь автоматически.</p>
    </div>
  </main>

  <!-- Модальное окно деталей студента -->
  <div class="modal-backdrop" id="modal-backdrop" onclick="closeModal(event)">
    <div class="modal-dialog" onclick="event.stopPropagation()">
      <div class="modal-header">
        <div>
          <div class="modal-title" id="modal-title">Иванов И.И. (Гр. 401)</div>
          <div style="font-size: 12px; color: var(--text-dim);" id="modal-sub">ПК-01 • Смальта</div>
        </div>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-tabs">
        <div class="modal-tab active" id="tab-log" onclick="switchModalTab('log')">📋 Общий лог</div>
        <div class="modal-tab" id="tab-mistakes" onclick="switchModalTab('mistakes')">⚠️ Лог ошибок</div>
        <div class="modal-tab" id="tab-shots" onclick="switchModalTab('shots')">📸 Галерея снимков (BBox)</div>
      </div>
      <div class="modal-body" id="modal-body">
        <!-- Контент таба -->
      </div>
    </div>
  </div>

  <!-- Модальное окно просмотра полноразмерного скриншота -->
  <div class="modal-backdrop" id="shot-modal-backdrop" onclick="closeShotModal()">
    <div style="max-width: 95vw; max-height: 95vh; display: flex; flex-direction: column; gap: 8px;">
      <img id="shot-full-img" src="" style="max-width: 95vw; max-height: 85vh; object-fit: contain; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.9);">
      <div style="display: flex; justify-content: space-between; color: #fff; font-size: 14px;">
        <span id="shot-full-title"></span>
        <button class="btn btn-outline btn-sm" onclick="closeShotModal()">Закрыть (Esc)</button>
      </div>
    </div>
  </div>

  <script>
    let studentsMap = {{}};
    let currentModalStudentId = null;
    let currentModalTab = 'log';
    let sseActive = false;

    // 1. Мгновенная синхронизация через REST (не ждет SSE-рукопожатия)
    async function syncStudentsREST() {{
      try {{
        const resp = await fetch('/api/students');
        if (resp.ok) {{
          const data = await resp.json();
          if (data && Array.isArray(data.students)) {{
            studentsMap = {{}};
            data.students.forEach(s => studentsMap[s.student_id] = s);
            renderStudents();
            if (!sseActive) {{
              const meta = document.getElementById('grid-meta');
              if (meta) meta.innerText = 'Связь активна (REST опрос)';
            }}
          }}
        }}
      }} catch (err) {{
        if (!sseActive) {{
          const meta = document.getElementById('grid-meta');
          if (meta) meta.innerText = 'Сервер недоступен (повтор...)';
        }}
      }}
    }}

    // 2. Подключение к Server-Sent Events (SSE)
    function initSSE() {{
      // Сразу подгружаем текущих студентов
      syncStudentsREST();

      try {{
        if (window.evtSource) {{
          try {{ window.evtSource.close(); }} catch(e) {{}}
        }}

        const evtSource = new EventSource('/api/stream');
        window.evtSource = evtSource;

        evtSource.onopen = function() {{
          sseActive = true;
          const meta = document.getElementById('grid-meta');
          if (meta) meta.innerText = 'Связь активна (Live SSE)';
        }};

        evtSource.onmessage = function(e) {{}};

        evtSource.addEventListener('init', function(e) {{
          sseActive = true;
          try {{
            const data = JSON.parse(e.data);
            studentsMap = {{}};
            data.students.forEach(s => studentsMap[s.student_id] = s);
            renderStudents();
            const meta = document.getElementById('grid-meta');
            if (meta) meta.innerText = 'Связь активна (Live SSE)';
          }} catch(err) {{
            console.error('SSE init error:', err);
          }}
        }});

        evtSource.addEventListener('student_update', function(e) {{
          sseActive = true;
          try {{
            const s = JSON.parse(e.data);
            studentsMap[s.student_id] = s;
            renderStudents();
            if (currentModalStudentId === s.student_id) {{
              updateModalContent();
            }}
          }} catch(err) {{}}
        }});

        evtSource.addEventListener('screenshot_update', function(e) {{
          try {{
            const data = JSON.parse(e.data);
            if (studentsMap[data.student_id]) {{
              studentsMap[data.student_id].last_screenshot_url = data.screenshot.url;
              studentsMap[data.student_id].last_screenshot_time = data.screenshot.timestamp;
              renderStudents();
              if (currentModalStudentId === data.student_id && currentModalTab === 'shots') {{
                loadStudentScreenshots(data.student_id);
              }}
            }}
          }} catch(err) {{}}
        }});

        evtSource.addEventListener('student_event', function(e) {{
          try {{
            const data = JSON.parse(e.data);
            if (studentsMap[data.student_id]) {{
              if (currentModalStudentId === data.student_id && currentModalTab === 'log') {{
                loadStudentEvents(data.student_id);
              }}
            }}
          }} catch(err) {{}}
        }});

        evtSource.addEventListener('reset', function() {{
          studentsMap = {{}};
          renderStudents();
        }});

        evtSource.onerror = function() {{
          sseActive = false;
          const meta = document.getElementById('grid-meta');
          if (meta) meta.innerText = 'Связь активна (резервный опрос)...';
          syncStudentsREST();
        }};
      }} catch (err) {{
        console.warn('SSE creation error:', err);
        sseActive = false;
      }}
    }}

    function renderStudents() {{
      const grid = document.getElementById('students-grid');
      const empty = document.getElementById('empty-state');
      const list = Object.values(studentsMap);

      let total = list.length;
      let active = 0;
      let finished = 0;
      let totalMistakes = 0;

      list.forEach(s => {{
        if (s.status === 'ACTIVE' || s.status === 'FOCUS_LOST') active++;
        else if (s.status === 'FINISHED' || s.status === 'STOPPED') finished++;
        totalMistakes += (s.mistakes_count || 0);
      }});

      document.getElementById('stat-total').innerText = total;
      document.getElementById('stat-active').innerText = active;
      const elMistakes = document.getElementById('stat-mistakes');
      if (elMistakes) elMistakes.innerText = totalMistakes;
      document.getElementById('stat-finished').innerText = finished;

      // Динамическое переключение кнопки Общий старт / Общий стоп
      const btnToggle = document.getElementById('btn-toggle-all');
      if (btnToggle) {{
        if (active > 0) {{
          btnToggle.className = 'btn btn-danger';
          btnToggle.innerText = '⏹ Общий стоп';
        }} else {{
          btnToggle.className = 'btn btn-success';
          btnToggle.innerText = '▶ Общий старт';
        }}
      }}

      if (total === 0) {{
        grid.style.display = 'none';
        empty.style.display = 'block';
        return;
      }} else {{
        grid.style.display = 'grid';
        empty.style.display = 'none';
      }}

      grid.innerHTML = '';
      list.forEach(s => {{
        const card = createStudentCard(s);
        grid.appendChild(card);
      }});
    }}

    function createStudentCard(s) {{
      const card = document.createElement('div');
      card.className = 'student-card';

      let statusClass = 'status-waiting';
      let statusText = 'Ожидает';
      if (s.status === 'ACTIVE') {{ statusClass = 'status-active'; statusText = 'Сдает'; }}
      else if (s.status === 'FINISHED') {{ statusClass = 'status-finished'; statusText = 'Завершил'; }}
      else if (s.status === 'STOPPED') {{ statusClass = 'status-stopped'; statusText = 'Остановлен'; }}

      const shotUrl = s.last_screenshot_url || '';
      const shotHtml = shotUrl
        ? `<img src="${{shotUrl}}" alt="Экран студента" onclick="openShotModal('${{shotUrl}}', '${{s.full_name}}')">`
        : `<div style="color: var(--text-dim); font-size: 13px;">Ожидание первого действия</div>`;

      const elapsedMin = Math.floor(s.elapsed_sec / 60);
      const elapsedSec = Math.floor(s.elapsed_sec % 60);
      const timeStr = `${{String(elapsedMin).padStart(2, '0')}}:${{String(elapsedSec).padStart(2, '0')}}`;

      const scoreHtml = (s.score !== null && s.score !== undefined)
        ? `<span style="color: ${{s.score >= 4 ? '#34d399' : (s.score === 3 ? '#fbbf24' : '#f87171')}}">Оценка: ${{s.score}}</span>`
        : `Шаг ${{s.completed_steps}}/${{s.total_steps}}`;

      card.innerHTML = `
        <div class="card-top">
          <div class="card-user">
            <span class="name">${{s.full_name}}</span>
            <span class="sub">${{s.group}} • ${{s.pc_name}} (${{s.client_ip}})</span>
          </div>
          <span class="badge-status ${{statusClass}}">${{statusText}}</span>
        </div>

        <div class="card-preview">
          ${{shotHtml}}
          <div class="preview-overlay-info">
            <span>${{s.device_name}}</span>
            <span>${{s.last_screenshot_time ? Math.round(Date.now()/1000 - s.last_screenshot_time) + ' сек назад' : 'Ожидание'}}</span>
          </div>
        </div>

        <div class="card-body">
          <div class="progress-box">
            <div class="progress-meta">
              <span>Прогресс: ${{Math.round(s.progress_pct * 100)}}%</span>
              <span>${{scoreHtml}}</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" style="width: ${{Math.round(s.progress_pct * 100)}}%"></div>
            </div>
          </div>

          <div class="metrics-row">
            <div class="metric-item">
              <div class="val" style="color: ${{s.mistakes_count > 0 ? '#fca5a5' : '#fff'}}">${{s.mistakes_count}}</div>
              <div class="lbl">Ошибок</div>
            </div>
            <div class="metric-item">
              <div class="val">${{timeStr}}</div>
              <div class="lbl">Время</div>
            </div>
            <div class="metric-item">
              <div class="val" style="color: #93c5fd;">${{s.completed_steps}}/${{s.total_steps}}</div>
              <div class="lbl">Шагов</div>
            </div>
          </div>
        </div>

        <div class="card-actions">
          ${{s.status === 'WAITING' ? `<button class="btn btn-success btn-sm" onclick="sendStudentCommand('${{s.student_id}}', 'START_EXAM')">▶ Начать</button>` : ''}}
          <button class="btn btn-outline btn-sm" onclick="sendStudentCommand('${{s.student_id}}', 'REQUEST_SCREENSHOT')">📸 Снимок</button>
          <button class="btn btn-primary btn-sm" onclick="openStudentModal('${{s.student_id}}')">📋 Журнал</button>
          ${{s.status === 'ACTIVE' || s.status === 'FOCUS_LOST' ? `<button class="btn btn-danger btn-sm" onclick="stopStudentExam('${{s.student_id}}', '${{s.full_name}}')">⏹ Стоп</button>` : ''}}
        </div>
      `;
      return card;
    }}

    function sendStudentCommand(studentId, command) {{
      fetch(`/api/students/${{studentId}}/command`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ command: command }})
      }});
    }}

    function stopStudentExam(studentId, studentName) {{
      if (confirm(`Принудительно завершить экзамен для курсанта ${{studentName}}?\nТекущий прогресс и оценка будут сохранены.`)) {{
        sendStudentCommand(studentId, 'STOP_EXAM');
      }}
    }}

    function toggleAllExams() {{
      const list = Object.values(studentsMap);
      const hasActive = list.some(s => s.status === 'ACTIVE' || s.status === 'FOCUS_LOST');
      if (hasActive) {{
        if (confirm('Принудительно завершить экзамен для всех сдающих курсантов?\nТекущий прогресс и оценки будут сохранены.')) {{
          fetch('/api/exam/stop_all', {{ method: 'POST' }});
        }}
      }} else {{
        if (confirm('Начать экзамен для всех ожидающих курсантов?')) {{
          fetch('/api/exam/start_all', {{ method: 'POST' }});
        }}
      }}
    }}

    function clearExamData() {{
      if (confirm('Очистить список курсантов на сервере?')) {{
        fetch('/api/exam/clear', {{ method: 'POST' }});
      }}
    }}

    function openStudentModal(studentId) {{
      currentModalStudentId = studentId;
      const s = studentsMap[studentId];
      if (!s) return;

      document.getElementById('modal-title').innerText = `${{s.full_name}} (${{s.group}})`;
      document.getElementById('modal-sub').innerText = `Рабочее место: ${{s.pc_name}} • Изделие: ${{s.device_name}} • Билет: ${{s.algorithm_name}}`;
      document.getElementById('modal-backdrop').classList.add('active');

      switchModalTab('log');
    }}

    function closeModal(e) {{
      if (!e || e.target.id === 'modal-backdrop') {{
        document.getElementById('modal-backdrop').classList.remove('active');
        currentModalStudentId = null;
      }}
    }}

    function switchModalTab(tab) {{
      currentModalTab = tab;
      document.getElementById('tab-log').classList.toggle('active', tab === 'log');
      document.getElementById('tab-mistakes').classList.toggle('active', tab === 'mistakes');
      document.getElementById('tab-shots').classList.toggle('active', tab === 'shots');

      if (tab === 'shots') {{
        loadStudentScreenshots(currentModalStudentId);
      }} else {{
        loadStudentEvents(currentModalStudentId, tab === 'mistakes');
      }}
    }}

    function updateModalContent() {{
      if (currentModalTab === 'shots') {{
        loadStudentScreenshots(currentModalStudentId);
      }} else {{
        loadStudentEvents(currentModalStudentId, currentModalTab === 'mistakes');
      }}
    }}

    function loadStudentEvents(studentId, filterMistakes = false) {{
      fetch(`/api/students/${{studentId}}/events`)
        .then(r => r.json())
        .then(data => {{
          const body = document.getElementById('modal-body');
          let events = data.events || [];
          if (filterMistakes) {{
            events = events.filter(e => e.is_mistake);
          }}
          if (events.length === 0) {{
            const emptyTxt = filterMistakes
              ? 'Ошибок не зафиксировано (отличная работа)'
              : 'Журнал пуст';
            body.innerHTML = `<div style="color: var(--text-dim); text-align: center; padding: 40px;">${{emptyTxt}}</div>`;
            return;
          }}
          let html = '<div class="log-list">';
          events.slice().reverse().forEach(evt => {{
            const d = new Date(evt.timestamp * 1000);
            const timeStr = d.toLocaleTimeString();
            let cls = 'log-item';
            let badge = evt.event_type;
            if (evt.is_mistake) {{
              cls += ' mistake';
              badge = 'ОШИБКА';
            }}
            html += `
              <div class="${{cls}}">
                <div>
                  <strong>[${{badge}}]</strong> ${{evt.message}}
                </div>
                <span style="color: var(--text-dim); margin-left: 16px;">${{timeStr}}</span>
              </div>
            `;
          }});
          html += '</div>';
          body.innerHTML = html;
        }});
    }}

    function loadStudentScreenshots(studentId) {{
      fetch(`/api/students/${{studentId}}/screenshots`)
        .then(r => r.json())
        .then(data => {{
          const body = document.getElementById('modal-body');
          const shots = data.screenshots || [];
          if (shots.length === 0) {{
            body.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 40px;">Скриншотов пока нет</div>';
            return;
          }}
          let html = '<div class="shots-grid">';
          shots.slice().reverse().forEach(shot => {{
            const d = new Date(shot.timestamp * 1000);
            const timeStr = d.toLocaleTimeString();
            const winTitle = shot.active_window ? ` • ${{shot.active_window}}` : '';
            html += `
              <div class="shot-card" onclick="openShotModal('${{shot.url}}', '${{timeStr}}${{winTitle}}')">
                <img src="${{shot.url}}">
                <div class="shot-info">${{timeStr}}${{winTitle}}</div>
              </div>
            `;
          }});
          html += '</div>';
          body.innerHTML = html;
        }});
    }}

    function openShotModal(url, title) {{
      document.getElementById('shot-full-img').src = url;
      document.getElementById('shot-full-title').innerText = title;
      document.getElementById('shot-modal-backdrop').classList.add('active');
    }}

    function closeShotModal() {{
      document.getElementById('shot-modal-backdrop').classList.remove('active');
    }}

    window.addEventListener('keydown', function(e) {{
      if (e.key === 'Escape') {{
        closeShotModal();
        closeModal();
      }}
    }});

    function startDashboard() {{
      initSSE();
      setInterval(syncStudentsREST, 2500);
    }}

    if (document.readyState === 'loading') {{
      document.addEventListener('DOMContentLoaded', startDashboard);
    }} else {{
      startDashboard();
    }}
  </script>
</body>
</html>
"""
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def start_udp_broadcast_responder(port: int = DEFAULT_SERVER_PORT, disc_port: int = DEFAULT_DISCOVERY_PORT):
    # 1. Слушатель запросов на поиск
    def listener():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', disc_port))
            while True:
                data, addr = s.recvfrom(1024)
                text = data.decode('utf-8', errors='ignore').strip()
                if text == DISCOVERY_MAGIC_REQUEST:
                    client_ip = addr[0]
                    reply_ip = get_best_ip_for_peer(client_ip) or get_primary_lan_ip()
                    resp_msg = f"{DISCOVERY_MAGIC_RESPONSE}:{reply_ip}:{port}".encode('utf-8')
                    s.sendto(resp_msg, addr)
        except Exception:
            pass

    t1 = threading.Thread(target=listener, daemon=True)
    t1.start()

    # 2. Периодический маяк (beacon) раз в 3 сек на всех физических адаптерах
    def beacon():
        while True:
            try:
                ifaces = get_local_interfaces()
                for iface in ifaces:
                    if iface["is_virtual"]:
                        continue
                    iface_ip = iface["ip"]
                    broadcast_addr = iface["broadcast"]
                    resp_msg = f"{DISCOVERY_MAGIC_RESPONSE}:{iface_ip}:{port}".encode('utf-8')
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        s.bind((iface_ip, 0))
                        s.sendto(resp_msg, (broadcast_addr, disc_port))
                        s.sendto(resp_msg, ('255.255.255.255', disc_port))
                        s.close()
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(3.0)

    t2 = threading.Thread(target=beacon, daemon=True)
    t2.start()

def run_server(port: int = DEFAULT_SERVER_PORT, auto_open: bool = True):
    server = ThreadingHTTPServer(('0.0.0.0', port), TeacherHTTPRequestHandler)
    ifaces = get_local_interfaces()
    print("=" * 68)
    print(f"  Vkm.ComplexSim — Экзаменационный сервер преподавателя запущен!")
    print(f"  Веб-дашборд доступен:")
    print(f"    * Локально на этом ПК: http://localhost:{port}")
    print(f"    * В локальной сети для подключения курсантов:")
    found_any = False
    for iface in ifaces:
        if not iface["is_virtual"]:
            found_any = True
            desc_l = iface["desc"].lower()
            label = "Ethernet" if ("ethernet" in desc_l or "usb" in desc_l) else ("Wi-Fi" if ("wi-fi" in desc_l or "wireless" in desc_l) else "LAN")
            gw_note = " (шлюз активен)" if iface["has_gateway"] else ""
            print(f"        -> http://{iface['ip']}:{port}  [{label}: {iface['desc']}{gw_note}]")
    if not found_any:
        print(f"        -> http://{get_primary_lan_ip()}:{port}")
    print("=" * 68)

    start_udp_broadcast_responder(port)

    if auto_open:
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка сервера преподавателя...")
        server.server_close()

if __name__ == "__main__":
    port = DEFAULT_SERVER_PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
