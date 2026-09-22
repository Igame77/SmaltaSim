import sys
from pathlib import Path
from enum import Enum

if getattr(sys, "frozen", False):
    # Running in a PyInstaller bundle
    if hasattr(sys, "_MEIPASS"):
        BASE_DIR = Path(sys._MEIPASS)
    else:
        BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

if (BASE_DIR / "assets").exists():
    ASSETS_DIR = BASE_DIR / "assets"
elif (BASE_DIR / "_internal" / "assets").exists():
    ASSETS_DIR = BASE_DIR / "_internal" / "assets"
elif (Path(sys.executable).resolve().parent / "assets").exists():
    ASSETS_DIR = Path(sys.executable).resolve().parent / "assets"
elif (Path(sys.executable).resolve().parent / "_internal" / "assets").exists():
    ASSETS_DIR = Path(sys.executable).resolve().parent / "_internal" / "assets"
else:
    ASSETS_DIR = BASE_DIR / "assets"

# Screen and Canvas Dimensions
CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 800
NAVBAR_HEIGHT = 70

SCREEN_WIDTH = CANVAS_WIDTH
SCREEN_HEIGHT = CANVAS_HEIGHT + NAVBAR_HEIGHT

FPS = 60

# Colors
COLOR_BG = (35, 39, 42)
COLOR_PANEL = (45, 52, 58)
COLOR_NAVBAR = (28, 32, 36)
COLOR_NAVBAR_BORDER = (60, 70, 80)
COLOR_BUTTON = (50, 60, 70)
COLOR_BUTTON_HOVER = (70, 85, 100)
COLOR_BUTTON_ACTIVE = (35, 45, 55)
COLOR_BUTTON_BORDER = (90, 105, 120)

COLOR_TEXT = (235, 240, 245)
COLOR_TEXT_DIM = (160, 170, 180)
COLOR_ACCENT = (0, 180, 216)
COLOR_SUCCESS = (46, 204, 113)
COLOR_WARNING = (243, 156, 18)
COLOR_DANGER = (231, 76, 60)

# Indicator Colors
COLOR_LIME = (50, 220, 50)
COLOR_ORANGE = (255, 140, 0)
COLOR_DARK_GREEN = (20, 80, 20)

class ApplicationMode(Enum):
    TRAINING = "Обучение"
    EXAMINE = "Экзамен"

# Asset Paths
class Assets:
    BG_MAIN = ASSETS_DIR / "Backgrounds" / "background.jpg"
    
    # Smalta backgrounds
    SMALTA_LO01P = ASSETS_DIR / "Smalta" / "Backgrounds" / "LO01P.png"
    SMALTA_LO01R = ASSETS_DIR / "Smalta" / "Backgrounds" / "LO01R.png"
    SMALTA_LO01I_LO01K = ASSETS_DIR / "Smalta" / "Backgrounds" / "LO01I_LO01K.png"
    
    # RLS ONC backgrounds
    RLS_STATION = ASSETS_DIR / "RlsOnc" / "Backgrounds" / "rls_onc_station.jpg"
    RLS_CPS = ASSETS_DIR / "RlsOnc" / "Backgrounds" / "rls_onc_controlpanelsim.jpg"
    RLS_G5_15 = ASSETS_DIR / "RlsOnc" / "Backgrounds" / "rls_onc_g5_15.jpg"
    RLS_RADAR = ASSETS_DIR / "RlsOnc" / "Backgrounds" / "rls_onc_radar.jpg"
    RLS_C1_65 = ASSETS_DIR / "RlsOnc" / "Backgrounds" / "rls_onc_c1_65.jpg"
    
    # Controls
    THUMBLER_ON = ASSETS_DIR / "ThumblerOn.png"
    THUMBLER_OFF = ASSETS_DIR / "ThumblerOff.png"
    BIG_BUTTON_ON = ASSETS_DIR / "BigButtonOn.png"
    BIG_BUTTON_OFF = ASSETS_DIR / "BigButtonOff.png"
    LAMP_ON = ASSETS_DIR / "LampOn.png"
    LAMP_OFF = ASSETS_DIR / "LampOff.png"
    STEP_WHEEL = ASSETS_DIR / "StepWheel.png"
    WHEEL = ASSETS_DIR / "Wheel.png"
    WHEEL_FLAT = ASSETS_DIR / "WheelFlat.png"
    WHEEL_POINT = ASSETS_DIR / "WheelPoint.png"
    TROLL_FACE = ASSETS_DIR / "TrollFace.png"
