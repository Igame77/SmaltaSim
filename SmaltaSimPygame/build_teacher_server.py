import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
ROOT_DIR = BASE_DIR.parent

def build_teacher_exe():
    print("--- Сборка автономного TeacherServer.exe ---")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", "TeacherServer",
        str(BASE_DIR / "teacher_server.py")
    ]
    print("Выполнение команды:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(BASE_DIR), check=True)

    src_exe = DIST_DIR / "TeacherServer.exe"
    target_root_exe = ROOT_DIR / "TeacherServer.exe"
    if src_exe.exists():
        shutil.copy2(src_exe, target_root_exe)
        sz_mb = target_root_exe.stat().st_size / (1024 * 1024)
        print(f"[OK] TeacherServer.exe собран и скопирован в: {target_root_exe} ({sz_mb:.2f} МБ)")

if __name__ == "__main__":
    build_teacher_exe()
