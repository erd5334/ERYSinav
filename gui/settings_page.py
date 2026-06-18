"""
Ayarlar sayfası
"""
import os
import logging
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from database import db_manager
import config

logger = logging.getLogger(__name__)


class SettingsPage(ctk.CTkFrame):
    """Uygulama ayarları sayfası"""

    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback

        # Grid düzeni
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_header()
        self.create_content()
        self.load_settings()

    def create_header(self):
        """Sayfa başlığı"""
        header_frame = ctk.CTkFrame(self, fg_color='transparent')
        header_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=20)
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text='⚙️ Sistem Ayarları',
            font=config.FONTS['title']
        )
        title.grid(row=0, column=0, sticky='w')

    def create_content(self):
        """İçerik alanı - kaydırılabilir ayarlar paneli"""
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky='nsew', padx=20, pady=(0, 20))
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        self.settings_scroll = ctk.CTkScrollableFrame(content_frame)
        self.settings_scroll.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        row = 0
        row = self.create_theme_section(self.settings_scroll, row)
        row = self.create_exam_defaults_section(self.settings_scroll, row)
        row = self.create_layout_section(self.settings_scroll, row)
        row = self.create_institution_section(self.settings_scroll, row)
        row = self.create_backup_section(self.settings_scroll, row)

        # Kaydet butonu
        btn_frame = ctk.CTkFrame(self.settings_scroll, fg_color='transparent')
        btn_frame.grid(row=row, column=0, sticky='ew', padx=20, pady=20)
        row += 1

        self.btn_save = ctk.CTkButton(
            btn_frame,
            text='💾 Değişiklikleri Kaydet',
            command=self.save_settings,
            height=45,
            font=config.FONTS['subheading']
        )
        self.btn_save.pack(fill='x')

    def create_theme_section(self, parent, row):
        """Tema ayarları bölümü"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=0, sticky='ew', padx=20, pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text='🎨 Görünüm ve Tema',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=15, sticky='w')

        ctk.CTkLabel(
            card, text='Uygulama Teması:', anchor='w'
        ).grid(row=1, column=0, sticky='w', pady=15, padx=15)

        theme_frame = ctk.CTkFrame(card, fg_color='transparent')
        theme_frame.grid(row=1, column=1, sticky='w', pady=15, padx=15)

        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text='Karanlık Mod',
            command=self._on_theme_switch,
            onvalue='dark',
            offvalue='light'
        )
        self.theme_switch.pack(side='left')

        if config.THEME_MODE == 'dark':
            self.theme_switch.select()

        return row + 1

    def _on_theme_switch(self):
        """Tema değiştirildiğinde"""
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)
        config.THEME_MODE = mode
        db_manager.set_setting('theme_mode', mode, 'Uygulama tema modu')

    def create_exam_defaults_section(self, parent, row):
        """Sınav varsayılanları bölümü"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=0, sticky='ew', padx=20, pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text='Sınav Varsayılan Parametreleri',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=15, sticky='w')

        # Sınav süresi
        ctk.CTkLabel(
            card, text='Varsayılan Sınav Süresi (Dakika):', anchor='w'
        ).grid(row=1, column=0, sticky='w', pady=10, padx=15)
        self.duration_entry = ctk.CTkEntry(card, placeholder_text='60')
        self.duration_entry.grid(row=1, column=1, sticky='ew', pady=10, padx=15)

        # Soru sayısı
        ctk.CTkLabel(
            card, text='Varsayılan Soru Sayısı:', anchor='w'
        ).grid(row=2, column=0, sticky='w', pady=10, padx=15)
        self.question_count_entry = ctk.CTkEntry(card, placeholder_text='20')
        self.question_count_entry.grid(row=2, column=1, sticky='ew', pady=10, padx=15)

        # Soru puanı
        ctk.CTkLabel(
            card, text='Soru Başına Puan:', anchor='w'
        ).grid(row=3, column=0, sticky='w', pady=10, padx=15)
        self.points_entry = ctk.CTkEntry(card, placeholder_text='5.0')
        self.points_entry.grid(row=3, column=1, sticky='ew', pady=10, padx=15)

        return row + 1

    def create_layout_section(self, parent, row):
        """Sayfa ve sütun düzeni bölümü"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=0, sticky='ew', padx=20, pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text='Sayfa ve Sütun Yerleşim Ayarları',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=15, sticky='w')

        # Sütun düzeni
        ctk.CTkLabel(
            card, text='Sayfa Sütun Düzeni:', anchor='w'
        ).grid(row=1, column=0, sticky='w', pady=10, padx=15)
        self.columns_combo = ctk.CTkComboBox(
            card,
            values=['1 Sütun (Tek Sütun)', '2 Sütun (Çift Sütun)']
        )
        self.columns_combo.grid(row=1, column=1, sticky='ew', pady=10, padx=15)

        # Şık kırılma limiti
        ctk.CTkLabel(
            card, text='Şık Kırılma Karakter Limiti:', anchor='w'
        ).grid(row=2, column=0, sticky='w', pady=10, padx=15)
        self.wrap_limit_entry = ctk.CTkEntry(card, placeholder_text='40')
        self.wrap_limit_entry.grid(row=2, column=1, sticky='ew', pady=10, padx=15)

        return row + 1

    def create_institution_section(self, parent, row):
        """Kurum ve yazar bilgileri bölümü"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=0, sticky='ew', padx=20, pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text='Kurum ve Yazar Bilgileri',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=15, sticky='w')

        # Kurum adı
        ctk.CTkLabel(
            card, text='Kurum Adı:', anchor='w'
        ).grid(row=1, column=0, sticky='w', pady=10, padx=15)
        self.institution_entry = ctk.CTkEntry(
            card, placeholder_text='Recep Tayyip Erdoğan Üniversitesi')
        self.institution_entry.grid(row=1, column=1, sticky='ew', pady=10, padx=15)

        # Ders sorumlusu
        ctk.CTkLabel(
            card, text='Varsayılan Ders Sorumlusu:', anchor='w'
        ).grid(row=2, column=0, sticky='w', pady=10, padx=15)
        self.instructor_entry = ctk.CTkEntry(
            card, placeholder_text='Örn: Dr. Öğr. Üyesi Ahmet Yılmaz')
        self.instructor_entry.grid(row=2, column=1, sticky='ew', pady=10, padx=15)

        return row + 1

    def create_backup_section(self, parent, row):
        """Yedekleme ve sistem işlemleri bölümü"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=0, sticky='ew', padx=20, pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text='Yedekleme ve Sistem İşlemleri',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=15, sticky='w')

        # Yedekleme dizini
        ctk.CTkLabel(
            card, text='Yedekleme Dizini:', anchor='w'
        ).grid(row=1, column=0, sticky='w', pady=10, padx=15)

        backup_dir_frame = ctk.CTkFrame(card, fg_color='transparent')
        backup_dir_frame.grid(row=1, column=1, sticky='ew', pady=10, padx=15)
        backup_dir_frame.grid_columnconfigure(0, weight=1)

        self.backup_dir_label = ctk.CTkLabel(
            backup_dir_frame,
            text=str(config.BACKUPS_DIR),
            anchor='w',
            text_color='gray'
        )
        self.backup_dir_label.grid(row=0, column=0, sticky='ew')

        ctk.CTkButton(
            backup_dir_frame,
            text='📁 Seç',
            command=self.select_backup_dir,
            width=80
        ).grid(row=0, column=1, padx=(5, 0))

        # Eylem butonları
        actions_frame = ctk.CTkFrame(card, fg_color='transparent')
        actions_frame.grid(row=2, column=0, columnspan=2, pady=15, padx=15, sticky='ew')

        btn_backup = ctk.CTkButton(
            actions_frame,
            text='📦 Şimdi Yedekle',
            command=self.backup_now,
            fg_color=config.COLORS['info'],
            hover_color='#0277bd'
        )
        btn_backup.pack(side='left', fill='x', expand=True, padx=(0, 5))

        btn_restore = ctk.CTkButton(
            actions_frame,
            text='🔄 Yedekten Geri Yükle',
            command=self.restore_now,
            fg_color=config.COLORS['warning'],
            hover_color='#e65100'
        )
        btn_restore.pack(side='right', fill='x', expand=True, padx=(5, 0))

        # Fabrika ayarları
        reset_frame = ctk.CTkFrame(card, fg_color='transparent')
        reset_frame.grid(row=3, column=0, columnspan=2, pady=(0, 15), padx=15, sticky='ew')

        btn_reset = ctk.CTkButton(
            reset_frame,
            text='⚠️ Tüm Verileri Sıfırla (Fabrika Ayarlarına Dön)',
            command=self.reset_all_data,
            fg_color='#d32f2f',
            hover_color='#b71c1c'
        )
        btn_reset.pack(fill='x', expand=True)

        return row + 1

    def select_backup_dir(self):
        """Yedekleme klasörü seç"""
        selected_dir = filedialog.askdirectory(
            title='Yedekleme Klasörü Seç',
            initialdir=str(config.BACKUPS_DIR)
        )
        if selected_dir:
            config.BACKUPS_DIR = Path(selected_dir)
            self.backup_dir_label.configure(text=str(config.BACKUPS_DIR))
            logger.info(f'Yeni yedekleme klasörü seçildi: {selected_dir}')



    def backup_now(self):
        """Veritabanını yedekle"""
        try:
            backup_path = db_manager.backup_database()
            messagebox.showinfo(
                'Yedekleme Başarılı',
                f'Veritabanı başarıyla yedeklendi!\n\nYedek dosyası:\n{backup_path}'
            )
        except Exception as e:
            messagebox.showerror('Yedekleme Hatası', f'Yedekleme sırasında hata oluştu:\n{e}')

    def restore_now(self):
        """Yedekten geri yükle"""
        if not messagebox.askyesno(
                'Veritabanı Yükle',
                'Yedek dosyasını geri yüklemek istediğinize emin misiniz? '
                'Bu işlem mevcut veritabanınızın üzerine yazacaktır. '
                '(Mevcut veritabanının bir yedeği otomatik olarak alınacaktır.)'):
            return

        filename = filedialog.askopenfilename(
            title='Geri Yüklenecek Yedek Dosyasını Seç',
            initialdir=str(config.BACKUPS_DIR),
            filetypes=[('Veritabanı Dosyaları', '*.db')]
        )

        if not filename:
            return

        try:
            db_manager.restore_database(filename)
            messagebox.showinfo('Geri Yükleme Başarılı',
                                'Veritabanı başarıyla yedekten yüklendi!')
            if self.status_callback:
                self.status_callback('Veritabanı yedekten yüklendi')
        except Exception as e:
            messagebox.showerror('Geri Yükleme Hatası', f'Geri yükleme hatası:\n{e}')

    def reset_all_data(self):
        """Tüm verileri sıfırla"""
        if not messagebox.askyesno(
                'Verileri Sıfırla',
                'Tüm sorular, sınavlar ve dersler kalıcı olarak silinecektir!\n\n'
                'Bu işlemi gerçekleştirmek istediğinize emin misiniz?',
                icon='warning'):
            return

        if not messagebox.askyesno(
                'Ciddi Misiniz?',
                'Bu işlem geri alınamaz! Devam etmek istediğinize emin misiniz?',
                icon='warning'):
            return

        # Otomatik yedek al
        try:
            backup_path = db_manager.backup_database()
            logger.info(f'Sıfırlama öncesi otomatik yedek alındı: {backup_path}')
        except Exception as e:
            logger.warning(f'Sıfırlama öncesi otomatik yedek alınamadı: {e}')

        try:
            from database.models import Course, Question, Exam, ExamQuestion
            with db_manager.session_scope() as session:
                session.query(ExamQuestion).delete()
                session.query(Exam).delete()
                session.query(Question).delete()
                session.query(Course).delete()

            messagebox.showinfo(
                'Sıfırlandı',
                'Tüm sorular, sınavlar ve dersler başarıyla silindi.\n\n'
                '(Güvenlik amacıyla işlemden hemen önce veritabanının yedeği alınmıştır.)'
            )

            if self.status_callback:
                self.status_callback('Tüm veritabanı sıfırlandı')
            logger.info('Tüm veritabanı sıfırlandı')

        except Exception as e:
            logger.error(f'Sıfırlama hatası: {e}')
            messagebox.showerror('Hata', f'Veriler sıfırlanırken hata oluştu:\n{e}')

    def load_settings(self):
        """Ayarları veritabanından yükle"""
        # Tema
        theme_mode = db_manager.get_setting('theme_mode', config.THEME_MODE)
        if theme_mode == 'dark':
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        ctk.set_appearance_mode(theme_mode)
        config.THEME_MODE = theme_mode

        # Sınav süresi
        duration = db_manager.get_setting('default_exam_duration', '60')
        self.duration_entry.delete(0, 'end')
        self.duration_entry.insert(0, duration)

        # Soru sayısı
        q_count = db_manager.get_setting('default_question_count', '20')
        self.question_count_entry.delete(0, 'end')
        self.question_count_entry.insert(0, q_count)

        # Soru puanı
        points = db_manager.get_setting('default_points_per_question', '5.0')
        self.points_entry.delete(0, 'end')
        self.points_entry.insert(0, points)

        # Sütun düzeni
        columns = db_manager.get_setting('layout_columns', '2')
        if columns == '1':
            self.columns_combo.set('1 Sütun (Tek Sütun)')
        else:
            self.columns_combo.set('2 Sütun (Çift Sütun)')

        # Şık kırılma limiti
        wrap_limit = db_manager.get_setting('option_wrap_limit', '40')
        self.wrap_limit_entry.delete(0, 'end')
        self.wrap_limit_entry.insert(0, wrap_limit)

        # Kurum adı
        institution = db_manager.get_setting('institution_name', config.APP_AUTHOR)
        self.institution_entry.delete(0, 'end')
        self.institution_entry.insert(0, institution)

        # Öğretim görevlisi
        instructor = db_manager.get_setting('default_instructor', '')
        self.instructor_entry.delete(0, 'end')
        self.instructor_entry.insert(0, instructor)

        # Yedekleme dizini
        backup_dir = db_manager.get_setting('backup_dir', str(config.BACKUPS_DIR))
        config.BACKUPS_DIR = Path(backup_dir)
        self.backup_dir_label.configure(text=str(config.BACKUPS_DIR))



    def save_settings(self):
        """Ayarları kaydet ve doğrula"""
        # Sınav süresi doğrulama
        try:
            duration = int(self.duration_entry.get().strip())
            if duration <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning('Uyarı',
                                   'Lütfen geçerli bir varsayılan süre (dakika) girin!')
            return

        # Soru sayısı doğrulama
        try:
            q_count = int(self.question_count_entry.get().strip())
            if q_count <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning('Uyarı',
                                   'Lütfen geçerli bir varsayılan soru sayısı girin!')
            return

        # Puan doğrulama
        try:
            points = float(self.points_entry.get().strip())
            if points <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning('Uyarı', 'Lütfen geçerli bir soru puanı girin!')
            return

        # Şık kırılma limiti doğrulama
        try:
            wrap_limit = int(self.wrap_limit_entry.get().strip())
            if wrap_limit <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning('Uyarı',
                                   'Lütfen geçerli bir şık karakter limiti girin!')
            return

        # Sütun seçimi
        columns = '1' if '1 Sütun' in self.columns_combo.get() else '2'

        try:
            db_manager.set_setting('default_exam_duration', str(duration),
                                   'Varsayılan sınav süresi')
            db_manager.set_setting('default_question_count', str(q_count),
                                   'Varsayılan soru sayısı')
            db_manager.set_setting('default_points_per_question', str(points),
                                   'Soru başına varsayılan puan')
            db_manager.set_setting('layout_columns', columns, 'Belge sütun sayısı')
            db_manager.set_setting('option_wrap_limit', str(wrap_limit),
                                   'Şık karakter wrap limiti')
            db_manager.set_setting('institution_name',
                                   self.institution_entry.get().strip(), 'Kurum adı')
            db_manager.set_setting('default_instructor',
                                   self.instructor_entry.get().strip(),
                                   'Varsayılan ders sorumlusu')
            db_manager.set_setting('backup_dir', str(config.BACKUPS_DIR),
                                   'Veritabanı yedekleme klasörü')


            config.APP_AUTHOR = self.institution_entry.get().strip()

            messagebox.showinfo('Başarılı', 'Sistem ayarları başarıyla kaydedildi!')
            if self.status_callback:
                self.status_callback('Ayarlar kaydedildi')

        except Exception as e:
            logger.error(f'Ayarlar kaydedilemedi: {e}')
            messagebox.showerror('Hata', f'Ayarlar kaydedilirken hata oluştu:\n{e}')
