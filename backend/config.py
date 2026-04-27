"""
SurUnplugged Backend Configuration
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.absolute()
STORAGE_DIR = BASE_DIR / "storage"
JOBS_DIR = STORAGE_DIR / "jobs"

# Create directories if they don't exist
STORAGE_DIR.mkdir(exist_ok=True)
JOBS_DIR.mkdir(exist_ok=True)

# Flask settings
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# File upload settings
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file size
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

# Processing settings
PROCESSING_MODES = {
    "fast": {
        "description": "Skip stem separation, chord detect on full mix",
        "use_demucs": False,
        "estimated_time": 30,  # seconds
    },
    "balanced": {
        "description": "Vocal separation only (--two-stems)",
        "use_demucs": True,
        "demucs_mode": "two-stems",
        "estimated_time": 180,  # seconds
    },
    "quality": {
        "description": "Full 4-stem separation",
        "use_demucs": True,
        "demucs_mode": "full",
        "estimated_time": 300,  # seconds
    },
}
DEFAULT_MODE = "balanced"

# Demucs settings
DEMUCS_MODEL = "htdemucs"

# FluidSynth settings
SOUNDFONT_PATH = BASE_DIR / "assets" / "soundfonts" / "guitar.sf2"

# Redis settings (for job queue)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
