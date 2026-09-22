import os
import shutil
import subprocess
import sys
from pathlib import Path
import zipfile

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
ASSETS_DIR = BASE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "logo.ico"

def clean():
    print("--- Очистка каталогов сборки ---")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    for spec in BASE_DIR.glob("*.spec"):
        spec.unlink(missing_ok=True)

def build_exe():
    print("--- Сборка исполняемого файла с помощью PyInstaller ---")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", "SmaltaSim",
        "--icon", str(ICON_PATH),
        "--add-data", f"{ASSETS_DIR};assets",
        str(BASE_DIR / "main.py")
    ]
    print("Выполнение команды:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(BASE_DIR), check=True)

def package_zip(version="v1.0.0"):
    print("--- Создание релизного ZIP-архива для GitHub ---")
    out_folder = DIST_DIR / "SmaltaSim"
    if not out_folder.exists():
        raise FileNotFoundError(f"Каталог сборки не найден: {out_folder}")

    # Copy README, assets and run helper to distribution folder
    shutil.copy2(BASE_DIR / "README.md", out_folder / "README.md")
    dest_assets = out_folder / "assets"
    if not dest_assets.exists():
        shutil.copytree(ASSETS_DIR, dest_assets)

    zip_filename = DIST_DIR / f"SmaltaSim-{version}-windows-x64.zip"
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(out_folder):
            for file in files:
                abs_path = Path(root) / file
                rel_path = Path("SmaltaSim") / abs_path.relative_to(out_folder)
                zf.write(abs_path, rel_path)

    print(f"Релизный архив готов: {zip_filename} ({zip_filename.stat().st_size / (1024*1024):.2f} МБ)")
    return zip_filename

if __name__ == "__main__":
    clean()
    build_exe()
    package_zip()
    print("--- Сборка успешно завершена! ---")
