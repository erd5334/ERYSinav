"""
Uygulama yapılandırma ayarları
"""
import os
from pathlib import Path
import sys
import shutil

APP_NAME = 'ERY Sınav'
APP_VERSION = '1.0.0'
APP_AUTHOR = 'Recep Tayyip Erdoğan Üniversitesi'
APP_DEVELOPER = 'Er Yazılım'
APP_DEVELOPER_URL = 'https://eryazilimci.com/'

# PyInstaller packages the executable.
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
    meipass = Path(getattr(sys, '_MEIPASS', ''))
else:
    BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / 'data'
IMAGES_DIR = DATA_DIR / 'images'
TEMPLATES_DIR = DATA_DIR / 'templates'
EXPORTS_DIR = DATA_DIR / 'exports'
BACKUPS_DIR = DATA_DIR / 'backups'
LOGO_PATH = IMAGES_DIR / 'logo.png'
ICON_PATH = IMAGES_DIR / 'logo.ico'
# Create directories
for directory in [DATA_DIR, IMAGES_DIR, TEMPLATES_DIR, EXPORTS_DIR, BACKUPS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Copy bundled assets from _MEIPASS if they exist
if getattr(sys, 'frozen', False):
    try:
        bundled_logo = meipass / 'logo.png'
        if bundled_logo.exists() and not LOGO_PATH.exists():
            shutil.copy(bundled_logo, LOGO_PATH)
    except Exception:
        pass
        
    try:
        bundled_ico = meipass / 'logo.ico'
        if bundled_ico.exists() and not ICON_PATH.exists():
            shutil.copy(bundled_ico, ICON_PATH)
    except Exception:
        pass

    try:
        bundled_taslak = meipass / 'taslak.docx'
        target_taslak = TEMPLATES_DIR / 'taslak.docx'
        if bundled_taslak.exists() and not target_taslak.exists():
            shutil.copy(bundled_taslak, target_taslak)
    except Exception:
        pass

DATABASE_PATH = DATA_DIR / 'exam_database.db'
BACKUP_INTERVAL_HOURS = 24

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 850
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 700

THEME_MODE = 'dark'
COLOR_THEME = 'blue'

COLORS = {
    'primary': '#1f6aa5',
    'secondary': '#144870',
    'success': '#2fa572',
    'danger': '#d32f2f',
    'warning': '#ed6c02',
    'info': '#0288d1',
    'light': '#f5f5f5',
    'dark': '#212121',
}

FONTS = {
    'title': ('Segoe UI', 24, 'bold'),
    'heading': ('Segoe UI', 18, 'bold'),
    'subheading': ('Segoe UI', 14, 'bold'),
    'body': ('Segoe UI', 12),
    'small': ('Segoe UI', 10),
    'code': ('Consolas', 11),
}

EXAM_SETTINGS = {
    'default_question_font_size': 12,
    'default_answer_font_size': 11,
    'question_image_width': 400,
    'question_image_height': 300,
    'answer_image_width': 200,
    'answer_image_height': 150,
    'page_margin': 2.5,
    'line_spacing': 1.15,
}

IMAGE_SETTINGS = {
    'max_file_size_mb': 5,
    'allowed_formats': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
    'thumbnail_size': (150, 150),
    'compress_quality': 85,
}

EXAM_TYPES = ['Vize', 'Final', 'Bütünleme', 'Mazeret', 'Quiz']
EXAM_GROUPS = ['A', 'B', 'C', 'D', 'E', 'F']
ANSWER_CHOICES = ['A', 'B', 'C', 'D', 'E']

DB_ECHO = False
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10

EXPORT_SETTINGS = {
    'word_template': 'default_template.docx',
    'pdf_template': 'default_pdf_template.py',
    'include_answer_key': True,
    'shuffle_questions': True,
    'shuffle_answers': False,
}

BACKUP_SETTINGS = {
    'auto_backup': True,
    'backup_count': 10,
    'backup_on_exit': True,
}

LOG_LEVEL = 'INFO'
LOG_FILE = DATA_DIR / 'app.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

ENABLE_AUTHENTICATION = False
SESSION_TIMEOUT_MINUTES = 30

CACHE_ENABLED = True
CACHE_SIZE = 100

SEARCH_SETTINGS = {
    'min_search_length': 2,
    'max_results': 100,
    'fuzzy_search': True,
}
