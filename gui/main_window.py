import customtkinter as ctk
from tkinter import messagebox
import logging
import webbrowser
import config

logger = logging.getLogger(__name__)

class MainWindow(ctk.CTk):
    """Ana uygulama penceresi"""

    def __init__(self):
        super().__init__()
        
        from database import db_manager
        from pathlib import Path
        
        theme_mode = db_manager.get_setting('theme_mode', config.THEME_MODE)
        config.THEME_MODE = theme_mode
        
        optik_dir = db_manager.get_setting('py_optik_dir')
        if optik_dir:
            config.PY_OPTIK_DIR = Path(optik_dir)
            
        backup_dir = db_manager.get_setting('backup_dir')
        if backup_dir:
            config.BACKUPS_DIR = Path(backup_dir)
            
        self.title(config.APP_NAME)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.minsize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        
        ctk.set_appearance_mode(config.THEME_MODE)
        ctk.set_default_color_theme(config.COLOR_THEME)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.create_statusbar()
        self.create_sidebar()
        self.create_main_content()
        
        self.protocol('WM_DELETE_WINDOW', self.on_closing)
        logger.info('Ana pencere başlatıldı')

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky='nswe', padx=0, pady=0)
        self.sidebar.grid_rowconfigure(8, weight=1)
        
        try:
            from PIL import Image
            logo_img = Image.open(str(config.LOGO_PATH))
            self.logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(56, 56))
            self.logo_label = ctk.CTkLabel(self.sidebar, image=self.logo_ctk, text='')
            self.logo_label.grid(row=0, column=0, padx=20, pady=(18, 0))
        except Exception:
            self.logo_label = ctk.CTkLabel(self.sidebar, text='📝', font=ctk.CTkFont(size=36))
            self.logo_label.grid(row=0, column=0, padx=20, pady=(18, 0))
            
        self.app_name_label = ctk.CTkLabel(self.sidebar, text='ERY Sınav', font=ctk.CTkFont(size=17, weight='bold'))
        self.app_name_label.grid(row=1, column=0, padx=20, pady=(4, 10))
        
        self.btn_dashboard = ctk.CTkButton(
            self.sidebar, text='🏠 Ana Sayfa', command=self.show_dashboard, anchor='w', height=40
        )
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=5, sticky='ew')
        
        self.btn_questions = ctk.CTkButton(
            self.sidebar, text='📝 Sorular', command=self.show_questions, anchor='w', height=40
        )
        self.btn_questions.grid(row=3, column=0, padx=20, pady=5, sticky='ew')
        
        self.btn_exams = ctk.CTkButton(
            self.sidebar, text='📄 Sınavlar', command=self.show_exams, anchor='w', height=40
        )
        self.btn_exams.grid(row=4, column=0, padx=20, pady=5, sticky='ew')
        
        self.btn_courses = ctk.CTkButton(
            self.sidebar, text='📚 Dersler', command=self.show_courses, anchor='w', height=40
        )
        self.btn_courses.grid(row=5, column=0, padx=20, pady=5, sticky='ew')
        
        self.btn_statistics = ctk.CTkButton(
            self.sidebar, text='📊 İstatistikler', command=self.show_statistics, anchor='w', height=40
        )
        self.btn_statistics.grid(row=6, column=0, padx=20, pady=5, sticky='ew')
        
        self.btn_settings = ctk.CTkButton(
            self.sidebar, text='⚙️ Ayarlar', command=self.show_settings, anchor='w', height=40
        )
        self.btn_settings.grid(row=7, column=0, padx=20, pady=5, sticky='ew')
        
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color=('#1a2a4a', '#0f1e35'), corner_radius=10)
        brand_frame.grid(row=9, column=0, padx=12, pady=(15, 12), sticky='ew')
        brand_frame.grid_columnconfigure(0, weight=1)
        
        brand_label = ctk.CTkLabel(
            brand_frame, text='💻 Er Yazılım', font=ctk.CTkFont(size=12, weight='bold'), text_color=('#4a9eff', '#5ba4ff')
        )
        brand_label.grid(row=0, column=0, padx=8, pady=(8, 2))
        
        brand_url = ctk.CTkLabel(
            brand_frame, text='eryazilimci.com', font=ctk.CTkFont(size=10), text_color='gray', cursor='hand2'
        )
        brand_url.grid(row=1, column=0, padx=8, pady=(0, 8))
        
        brand_url.bind('<Button-1>', lambda e: webbrowser.open(config.APP_DEVELOPER_URL))
        brand_frame.bind('<Button-1>', lambda e: webbrowser.open(config.APP_DEVELOPER_URL))
        brand_label.bind('<Button-1>', lambda e: webbrowser.open(config.APP_DEVELOPER_URL))

    def create_main_content(self):
        self.main_content = ctk.CTkFrame(self, corner_radius=0)
        self.main_content.grid(row=0, column=1, sticky='nswe', padx=0, pady=0)
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.show_dashboard()

    def create_statusbar(self):
        self.statusbar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.statusbar.grid(row=1, column=0, columnspan=2, sticky='ew', padx=0, pady=0)
        
        self.status_label = ctk.CTkLabel(self.statusbar, text='Hazır', anchor='w')
        self.status_label.pack(side='left', padx=10)

    def clear_main_content(self):
        for widget in self.main_content.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_main_content()
        self.update_status('Ana Sayfa')
        
        title = ctk.CTkLabel(self.main_content, text='🏠 Hoş Geldiniz', font=config.FONTS['title'])
        title.pack(pady=20)
        
        stats_frame = ctk.CTkFrame(self.main_content)
        stats_frame.pack(pady=20, padx=20, fill='x')
        
        from database import db_manager
        stats = db_manager.get_statistics()
        
        self.create_stat_card(stats_frame, '📝 Toplam Soru', stats.get('total_questions', 0), 0)
        self.create_stat_card(stats_frame, '📄 Toplam Sınav', stats.get('total_exams', 0), 1)
        self.create_stat_card(stats_frame, '📚 Toplam Ders', stats.get('total_courses', 0), 2)
        
        quick_actions = ctk.CTkFrame(self.main_content)
        quick_actions.pack(pady=20, padx=20, fill='both', expand=True)
        
        quick_title = ctk.CTkLabel(quick_actions, text='Hızlı İşlemler', font=config.FONTS['heading'])
        quick_title.pack(pady=10)
        
        btn_new_question = ctk.CTkButton(
            quick_actions, text='➕ Yeni Soru Ekle', command=self.show_questions, height=50, font=config.FONTS['subheading']
        )
        btn_new_question.pack(pady=10, padx=50, fill='x')
        
        btn_create_exam = ctk.CTkButton(
            quick_actions, text='📄 Sınav Oluştur', command=self.show_exams, height=50, font=config.FONTS['subheading']
        )
        btn_create_exam.pack(pady=10, padx=50, fill='x')
        
        btn_new_course = ctk.CTkButton(
            quick_actions, text='📚 Yeni Ders Ekle', command=self.show_courses, height=50, font=config.FONTS['subheading']
        )
        btn_new_course.pack(pady=10, padx=50, fill='x')

    def create_stat_card(self, parent, title, value, column):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=column, padx=10, pady=10, sticky='ew')
        parent.grid_columnconfigure(column, weight=1)
        
        title_label = ctk.CTkLabel(card, text=title, font=config.FONTS['subheading'])
        title_label.pack(pady=(20, 5))
        
        value_label = ctk.CTkLabel(card, text=str(value), font=config.FONTS['title'])
        value_label.pack(pady=(5, 20))

    def show_questions(self):
        self.clear_main_content()
        self.update_status('Sorular')
        
        from gui.questions_page import QuestionsPage
        questions_page = QuestionsPage(self.main_content, self.update_status)
        questions_page.pack(fill='both', expand=True)

    def show_exams(self):
        self.clear_main_content()
        self.update_status('Sınavlar')
        
        from gui.exams_page import ExamsPage
        exams_page = ExamsPage(self.main_content, self.update_status)
        exams_page.pack(fill='both', expand=True)

    def show_courses(self):
        self.clear_main_content()
        self.update_status('Dersler')
        
        from gui.courses_page import CoursesPage
        courses_page = CoursesPage(self.main_content, self.update_status)
        courses_page.pack(fill='both', expand=True)

    def show_statistics(self):
        self.clear_main_content()
        self.update_status('İstatistikler')
        
        from gui.statistics_page import StatisticsPage
        statistics_page = StatisticsPage(self.main_content, self.update_status)
        statistics_page.pack(fill='both', expand=True)

    def show_settings(self):
        self.clear_main_content()
        self.update_status('Ayarlar')
        
        from gui.settings_page import SettingsPage
        settings_page = SettingsPage(self.main_content, self.update_status)
        settings_page.pack(fill='both', expand=True)

    def toggle_theme(self, mode=None):
        if mode is None:
            return
        ctk.set_appearance_mode(mode)
        config.THEME_MODE = mode
        logger.info(f"Tema değiştirildi: {mode}")

    def update_status(self, message):
        self.status_label.configure(text=message)

    def on_closing(self):
        try:
            if config.BACKUP_SETTINGS['backup_on_exit']:
                from database import db_manager
                db_manager.backup_database()
                logger.info('Çıkış öncesi yedekleme tamamlandı')
        except Exception as e:
            logger.error(f"Yedekleme hatası: {e}")
        logger.info('Uygulama kapatılıyor')
        self.destroy()
