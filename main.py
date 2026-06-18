"""
Modern Sınav Yönetim Sistemi - Ana Program
"""
import sys
import logging
from pathlib import Path

# Proje dizinini sisteme ekleme
sys.path.insert(0, str(Path(__file__).parent))

import config
from gui import MainWindow

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[logging.FileHandler(config.LOG_FILE, encoding='utf-8')]
    )

def main():
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info('==================================================')
        logger.info(f'{config.APP_NAME} başlatılıyor...')
        logger.info(f'Versiyon: {config.APP_VERSION}')
        logger.info('==================================================')
        
        from database import db_manager
        logger.info('Veritabanı hazır')
        
        app = MainWindow()
        
        try:
            if config.ICON_PATH.exists():
                app.iconbitmap(str(config.ICON_PATH))
        except Exception:
            pass
            
        app.mainloop()
        
    except Exception as e:
        logger.error(f'Kritik hata: {e}', exc_info=True)
        from tkinter import messagebox as mb
        mb.showerror('Hata', f'Uygulama başlatılamadı:\n{str(e)}')
        sys.exit(1)

if __name__ == '__main__':
    main()
