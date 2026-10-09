import pytest
import time
import json
import threading
import io
import pygame
from network.exam_protocol import StudentStatus, EventType
from network.screen_tracker import ScreenTracker
from network.student_client import StudentClient
import teacher_server

def test_screen_tracker_focus():
    tracker = ScreenTracker("ComplexSim")
    assert tracker.is_focused is True

    # 1. Simulator loses focus
    changed, msg, dur = tracker.update_focus(False)
    assert tracker.is_focused is False
    assert changed is True
    assert "свернул" in msg or "переключился" in msg

    # 2. Simulator regains focus
    time.sleep(0.05)
    changed, msg, dur = tracker.update_focus(True)
    assert tracker.is_focused is True
    assert changed is True
    assert dur is not None and dur > 0
    assert "вернулся" in msg

def test_screen_tracker_capture():
    pygame.init()
    tracker = ScreenTracker("ComplexSim")
    jpeg = tracker.capture_screenshot_jpeg(max_width=400, max_height=300)
    assert jpeg is not None
    assert len(jpeg) > 100
    assert jpeg[:2] == b'\xff\xd8'  # Valid JPEG SOI marker

def test_teacher_server_and_student_client_integration():
    test_port = 8990
    server_thread = threading.Thread(
        target=teacher_server.run_server,
        args=(test_port, False),
        daemon=True
    )
    server_thread.start()
    time.sleep(0.8)

    client = StudentClient(server_ip="127.0.0.1", server_port=test_port)

    # 1. Login
    logged_in = client.login_sync(
        full_name="Курсант Петров",
        group="402",
        pc_name="ПК-07",
        device_name="Станция ЛО01 Смальта",
        algorithm_name="Подготовка к работе",
        max_time_seconds=600.0,
        total_steps=18
    )
    assert logged_in is True
    assert client.student_id is not None
    sid = client.student_id

    # Verify student is in server state
    st = teacher_server.server_state.get_student(sid)
    assert st is not None
    assert st.full_name == "Курсант Петров"
    assert st.status == StudentStatus.WAITING

    # 2. Send events
    client.send_event(EventType.ACTION, "Включен тумблер В1")
    client.send_event(EventType.MISTAKE, "Нажата неверная кнопка", is_mistake=True)
    time.sleep(0.5)

    with teacher_server.server_state.lock:
        assert len(st.events) >= 2
        assert any(e["is_mistake"] for e in st.events)

    # 3. Heartbeat & Command exchange
    # Simulate teacher sending START_EXAM command
    with teacher_server.server_state.lock:
        st.pending_commands.append({"type": "START_EXAM"})

    received_cmds = []
    client.on_command_callback = lambda cmd, payload: received_cmds.append(cmd)

    client.queue_heartbeat(
        progress_pct=0.25,
        completed_steps=4,
        mistakes_count=1,
        is_focused=True,
        active_window="Vkm.ComplexSim",
        elapsed_sec=30.0,
        score=4
    )
    time.sleep(0.6)

    assert "START_EXAM" in received_cmds
    assert client.is_exam_started_by_server is True

    # 4. Upload screenshot
    tracker = ScreenTracker("ComplexSim")
    jpeg = tracker.capture_screenshot_jpeg(max_width=320, max_height=240)
    assert jpeg is not None
    client.send_screenshot(jpeg)
    time.sleep(0.5)

    with teacher_server.server_state.lock:
        assert st.last_screenshot_url is not None
        assert len(st.screenshots) >= 1

    client.stop()

def test_app_examine_flow(monkeypatch):
    import os
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    from main import SimulatorApp, ApplicationMode
    app = SimulatorApp()

    # Test opening auth dialog
    app._open_exam_auth_dialog()
    assert app.active_dialog is not None

    # Test auth confirmed
    app._on_auth_confirmed({
        "full_name": "Тест Студент",
        "group": "401",
        "pc_name": "ПК-ТЕСТ",
        "server_ip": "127.0.0.1"
    }, app.student_client)
    assert app.mode == ApplicationMode.EXAMINE
    assert app.active_dialog is not None  # Device selection dialog

    # Test choosing device and algo
    smalta_dev = app.devices_catalog["smalta"]
    algo = app.algorithms_catalog["smalta"][0]
    app._prepare_examine_session(smalta_dev, algo)
    # Should not raise NameError or any exception!
    assert app.active_device is not None or app.active_dialog is not None

