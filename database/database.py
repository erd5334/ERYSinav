import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import config
from database.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Veritabanı işlemlerini yöneten singleton sınıf"""
    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            db_url = f"sqlite:///{config.DATABASE_PATH}"
            self._engine = create_engine(
                db_url,
                echo=config.DB_ECHO,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
            
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            self._session_factory = sessionmaker(bind=self._engine)
            self.create_tables()
            logger.info(f"Veritabanı başarıyla başlatıldı: {config.DATABASE_PATH}")
        except Exception as e:
            logger.error(f"Veritabanı başlatma hatası: {e}")
            raise

    def create_tables(self):
        try:
            Base.metadata.create_all(self._engine)
            logger.info("Veritabanı tabloları oluşturuldu")
        except Exception as e:
            logger.error(f"Tablo oluşturma hatası: {e}")
            raise

    def drop_tables(self):
        try:
            Base.metadata.drop_all(self._engine)
            logger.warning("Tüm veritabanı tabloları silindi")
        except Exception as e:
            logger.error(f"Tablo silme hatası: {e}")
            raise

    def get_session(self) -> Session:
        return self._session_factory()

    @contextmanager
    def session_scope(self):
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Veritabanı işlem hatası: {e}")
            raise
        finally:
            session.close()

    def backup_database(self, backup_path=None):
        try:
            import shutil
            from datetime import datetime
            
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = config.BACKUPS_DIR / f"backup_{timestamp}.db"
            
            shutil.copy2(config.DATABASE_PATH, backup_path)
            logger.info(f"Veritabanı yedeklendi: {backup_path}")
            self._cleanup_old_backups()
            return backup_path
        except Exception as e:
            logger.error(f"Yedekleme hatası: {e}")
            raise

    def _cleanup_old_backups(self):
        try:
            backups = sorted(config.BACKUPS_DIR.glob("backup_*.db"), reverse=True)
            for backup in backups[config.BACKUP_SETTINGS['backup_count']:]:
                backup.unlink()
                logger.info(f"Eski yedek silindi: {backup}")
        except Exception as e:
            logger.warning(f"Yedek temizleme hatası: {e}")

    def restore_database(self, backup_path):
        try:
            import shutil
            self.backup_database()
            shutil.copy2(backup_path, config.DATABASE_PATH)
            self._engine.dispose()
            self._initialize()
            logger.info(f"Veritabanı geri yüklendi: {backup_path}")
        except Exception as e:
            logger.error(f"Geri yükleme hatası: {e}")
            raise

    def get_statistics(self):
        from database.models import Question, Exam, Course
        try:
            with self.session_scope() as session:
                stats = {
                    "total_questions": session.query(Question).filter_by(is_active=True).count(),
                    "total_exams": session.query(Exam).count(),
                    "total_courses": session.query(Course).filter_by(is_active=True).count(),
                    "database_size": config.DATABASE_PATH.stat().st_size / (1024 * 1024)
                }
                return stats
        except Exception as e:
            logger.error(f"İstatistik hatası: {e}")
            return {}

    def get_setting(self, key, default=None):
        from database.models import Settings
        try:
            with self.session_scope() as session:
                setting = session.query(Settings).filter_by(key=key).first()
                if setting:
                    return setting.value
                return default
        except Exception as e:
            logger.error(f"Ayar okuma hatası ({key}): {e}")
            return default

    def set_setting(self, key, value, description=None):
        from database.models import Settings
        try:
            with self.session_scope() as session:
                setting = session.query(Settings).filter_by(key=key).first()
                if setting:
                    setting.value = str(value)
                    if description:
                        setting.description = description
                else:
                    setting = Settings(key=key, value=str(value), description=description)
                    session.add(setting)
        except Exception as e:
            logger.error(f"Ayar kaydetme hatası ({key}): {e}")

db_manager = DatabaseManager()

def get_db_session():
    return db_manager.get_session()
