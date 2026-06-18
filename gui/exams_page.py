"""
Sınav oluşturma sayfası
"""
import os
import random
import logging
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import pandas as pd
from database import db_manager, Course, Question, Exam, ExamQuestion
from services.word_generator import WordGenerator
import config

logger = logging.getLogger(__name__)


class ExamsPage(ctk.CTkFrame):
    """Sınav oluşturma sayfası"""

    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.courses = []
        self.questions = []
        self.selected_questions = []
        self.selected_exam = None
        self.past_exams = []

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_header()
        self.create_content()
        self.load_data()

    def create_header(self):
        """Sayfa başlığı"""
        header_frame = ctk.CTkFrame(self, fg_color='transparent')
        header_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=20)
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text='📄 Sınav Oluşturma',
            font=config.FONTS['title']
        ).grid(row=0, column=0, sticky='w')

    def create_content(self):
        """İki sekme: Yeni Sınav ve Geçmiş Sınavlar"""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky='nsew', padx=20, pady=(0, 20))

        self.tab_new = self.tabview.add('➕ Yeni Sınav Oluştur')
        self.tab_list = self.tabview.add('📁 Geçmiş Sınavlar')

        # Yeni sınav sekmesi
        self.tab_new.grid_rowconfigure(0, weight=1)
        self.tab_new.grid_columnconfigure(0, weight=1)
        self.create_settings_panel(self.tab_new)

        # Geçmiş sınavlar sekmesi
        self.tab_list.grid_rowconfigure(0, weight=1)
        self.tab_list.grid_columnconfigure(0, weight=1)
        self.tab_list.grid_columnconfigure(1, weight=2)
        self.create_exams_list_panel(self.tab_list)
        self.create_exams_detail_panel(self.tab_list)

    def create_settings_panel(self, parent):
        """Yeni sınav oluşturma formu"""
        settings_frame = ctk.CTkScrollableFrame(parent)
        settings_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        settings_frame.grid_columnconfigure(0, weight=1)

        # Başlık
        ctk.CTkLabel(
            settings_frame, text='Sınav Bilgileri',
            font=config.FONTS['heading']
        ).grid(row=0, column=0, pady=(20, 20), padx=20, sticky='w')

        # Form
        form_frame = ctk.CTkFrame(settings_frame, fg_color='transparent')
        form_frame.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 20))
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Ders
        ctk.CTkLabel(form_frame, text='Ders:*', anchor='w').grid(
            row=row, column=0, sticky='w', pady=10, padx=(0, 10))
        self.course_combo = ctk.CTkComboBox(
            form_frame, values=['Yükleniyor...'], command=self.on_course_change)
        self.course_combo.grid(row=row, column=1, sticky='ew', pady=10)
        row += 1

        # Sınav türü
        ctk.CTkLabel(form_frame, text='Sınav Türü:*', anchor='w').grid(
            row=row, column=0, sticky='w', pady=10, padx=(0, 10))
        self.exam_type_combo = ctk.CTkComboBox(
            form_frame, values=config.EXAM_TYPES, command=self.on_exam_type_change)
        self.exam_type_combo.grid(row=row, column=1, sticky='ew', pady=10)
        self.exam_type_combo.set(config.EXAM_TYPES[0])
        row += 1

        # Grup
        ctk.CTkLabel(form_frame, text='Grup:*', anchor='w').grid(
            row=row, column=0, sticky='w', pady=10, padx=(0, 10))
        self.exam_group_combo = ctk.CTkComboBox(
            form_frame, values=config.EXAM_GROUPS)
        self.exam_group_combo.grid(row=row, column=1, sticky='ew', pady=10)
        self.exam_group_combo.set(config.EXAM_GROUPS[0])
        row += 1

        # Sınav tarihi
        ctk.CTkLabel(form_frame, text='Sınav Tarihi:', anchor='w').grid(
            row=row, column=0, sticky='w', pady=10, padx=(0, 10))
        self.exam_date_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text=datetime.now().strftime('%d.%m.%Y')
        )
        self.exam_date_entry.grid(row=row, column=1, sticky='ew', pady=10)
        self.exam_date_entry.insert(0, datetime.now().strftime('%d.%m.%Y'))
        row += 1

        # Süre
        ctk.CTkLabel(form_frame, text='Süre (dakika):', anchor='w').grid(
            row=row, column=0, sticky='w', pady=10, padx=(0, 10))
        self.duration_entry = ctk.CTkEntry(form_frame, placeholder_text='60')
        self.duration_entry.grid(row=row, column=1, sticky='ew', pady=10)
        self.duration_entry.insert(0, '60')
        row += 1

        # Soru sayısı
        ctk.CTkLabel(form_frame, text='Soru Sayısı:*', anchor='w').grid(
            row=row, column=0, sticky='w', pady=10, padx=(0, 10))

        q_count_frame = ctk.CTkFrame(form_frame, fg_color='transparent')
        q_count_frame.grid(row=row, column=1, sticky='ew', pady=10)
        q_count_frame.grid_columnconfigure(0, weight=1)

        self.question_count_entry = ctk.CTkEntry(q_count_frame, placeholder_text='20')
        self.question_count_entry.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        self.question_count_entry.insert(0, '20')

        self.available_label = ctk.CTkLabel(
            q_count_frame, text='(Mevcut: -)', text_color='gray')
        self.available_label.grid(row=0, column=1)
        row += 1

        # Manuel Soru Seçimi
        self.manual_select_var = ctk.BooleanVar(value=False)
        self.chk_manual_select = ctk.CTkCheckBox(
            form_frame, text='Manuel Soru Seç',
            variable=self.manual_select_var,
            command=self.toggle_manual_selection
        )
        self.chk_manual_select.grid(row=row, column=0, sticky='w', pady=10)
        
        self.btn_select_questions = ctk.CTkButton(
            form_frame, text='Soruları Seç (0 seçildi)...',
            command=self.open_manual_selection_dialog,
            state='disabled'
        )
        self.btn_select_questions.grid(row=row, column=1, sticky='ew', pady=10)
        
        self.selected_manual_question_ids = []
        row += 1

        # Seçenekler
        options_frame = ctk.CTkFrame(settings_frame)
        options_frame.grid(row=2, column=0, sticky='ew', padx=20, pady=(0, 20))
        options_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            options_frame, text='Seçenekler',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='w')

        self.shuffle_questions_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame, text='Soruları karıştır',
            variable=self.shuffle_questions_var
        ).grid(row=1, column=0, columnspan=2, sticky='w', padx=10, pady=5)

        self.shuffle_answers_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options_frame, text='Şıkları karıştır',
            variable=self.shuffle_answers_var
        ).grid(row=2, column=0, columnspan=2, sticky='w', padx=10, pady=5)

        self.create_answer_key_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame, text='Cevap anahtarı oluştur',
            variable=self.create_answer_key_var
        ).grid(row=3, column=0, columnspan=2, sticky='w', padx=10, pady=5)

        ctk.CTkLabel(options_frame, text='Yazı Tipi Boyutu:').grid(row=4, column=0, sticky='w', padx=10, pady=5)
        self.font_size_combo = ctk.CTkComboBox(options_frame, values=['9', '10', '11', '12'], width=80)
        self.font_size_combo.grid(row=4, column=1, sticky='w', padx=10, pady=5)
        self.font_size_combo.set('11')

        ctk.CTkLabel(options_frame, text='Mükerrer Engelleme:').grid(row=5, column=0, sticky='w', padx=10, pady=5)
        self.anti_collision_combo = ctk.CTkComboBox(
            options_frame,
            values=['Engelleme Yok', 'Son 6 Ay', 'Son 1 Yıl', 'Daha Önce Kullanılanlar'],
            width=170
        )
        self.anti_collision_combo.grid(row=5, column=1, sticky='w', padx=10, pady=5)
        self.anti_collision_combo.set('Engelleme Yok')

        # Zorluk dağılımı
        difficulty_frame = ctk.CTkFrame(settings_frame)
        difficulty_frame.grid(row=3, column=0, sticky='ew', padx=20, pady=(0, 20))

        ctk.CTkLabel(
            difficulty_frame, text='Zorluk Dağılımı (Opsiyonel)',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='w')

        self.easy_percent = ctk.CTkEntry(
            difficulty_frame, placeholder_text='30', width=60)
        self.easy_percent.grid(row=1, column=0, padx=10, pady=5)
        ctk.CTkLabel(difficulty_frame, text='% Kolay').grid(
            row=1, column=1, sticky='w', pady=5)

        self.medium_percent = ctk.CTkEntry(
            difficulty_frame, placeholder_text='50', width=60)
        self.medium_percent.grid(row=2, column=0, padx=10, pady=5)
        ctk.CTkLabel(difficulty_frame, text='% Orta').grid(
            row=2, column=1, sticky='w', pady=5)

        self.hard_percent = ctk.CTkEntry(
            difficulty_frame, placeholder_text='20', width=60)
        self.hard_percent.grid(row=3, column=0, padx=10, pady=5)
        ctk.CTkLabel(difficulty_frame, text='% Zor').grid(
            row=3, column=1, sticky='w', pady=5)

        # Butonlar
        btn_frame = ctk.CTkFrame(settings_frame, fg_color='transparent')
        btn_frame.grid(row=4, column=0, sticky='ew', padx=20, pady=20)

        self.btn_create = ctk.CTkButton(
            btn_frame, text='📄 Sınav Oluştur',
            command=self.create_exam,
            height=50, font=config.FONTS['subheading']
        )
        self.btn_create.pack(fill='x', pady=5)

        self.btn_preview = ctk.CTkButton(
            btn_frame, text='👁 Önizleme',
            command=self.preview_exam,
            height=40,
            fg_color='gray', hover_color='darkgray'
        )
        self.btn_preview.pack(fill='x', pady=5)

    def create_exams_list_panel(self, parent):
        """Geçmiş sınavlar listesi"""
        list_frame = ctk.CTkFrame(parent)
        list_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            list_frame, text='Geçmiş Sınavlar',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, pady=10, padx=10, sticky='w')

        # Treeview
        is_dark = config.THEME_MODE == 'dark'
        bg = '#2b2b2b' if is_dark else '#f0f0f0'
        fg = '#ffffff' if is_dark else '#111111'

        style = ttk.Style()
        style.theme_use('default')
        style.configure('Exams.Treeview', background=bg, foreground=fg,
                        fieldbackground=bg, borderwidth=0, rowheight=40,
                        font=('Segoe UI', 9))
        style.configure('Exams.Treeview.Heading',
                        background='#1a1a1a' if is_dark else '#dcdcdc',
                        foreground=fg, font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Exams.Treeview', background=[('selected', '#1f6aa5')],
                  foreground=[('selected', 'white')])

        cols = ('ders', 'tur', 'grup', 'tarih', 'sorular')
        self.exams_tree = ttk.Treeview(
            list_frame, columns=cols, show='headings',
            style='Exams.Treeview', selectmode='browse'
        )
        self.exams_tree.heading('ders', text='Ders')
        self.exams_tree.heading('tur', text='Tür')
        self.exams_tree.heading('grup', text='Grup')
        self.exams_tree.heading('tarih', text='Tarih')
        self.exams_tree.heading('sorular', text='Soru')

        self.exams_tree.column('ders', width=70)
        self.exams_tree.column('tur', width=80)
        self.exams_tree.column('grup', width=60)
        self.exams_tree.column('tarih', width=90)
        self.exams_tree.column('sorular', width=50)

        tree_scroll = ctk.CTkScrollbar(list_frame, command=self.exams_tree.yview)
        self.exams_tree.configure(yscrollcommand=tree_scroll.set)

        self.exams_tree.grid(row=1, column=0, sticky='nsew',
                              padx=(10, 0), pady=(0, 10))
        tree_scroll.grid(row=1, column=1, sticky='ns', pady=(0, 10), padx=(0, 5))

        self.exams_tree.bind('<<TreeviewSelect>>', self._on_exam_select)

    def create_exams_detail_panel(self, parent):
        """Sınav detay paneli"""
        self.detail_frame = ctk.CTkFrame(parent)
        self.detail_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        self.detail_frame.grid_columnconfigure(0, weight=1)

        self.lbl_detail_title = ctk.CTkLabel(
            self.detail_frame, text='Sınav Detayları',
            font=config.FONTS['subheading']
        )
        self.lbl_detail_title.grid(row=0, column=0, pady=15, padx=15, sticky='w')

        # Alt detay frame (dinamik içerik)
        self.details_sub_frame = ctk.CTkScrollableFrame(self.detail_frame)
        self.details_sub_frame.grid(row=1, column=0, sticky='nsew',
                                     padx=10, pady=(0, 10))
        self.details_sub_frame.grid_columnconfigure(0, weight=1)
        self.detail_frame.grid_rowconfigure(1, weight=1)

        # Bilgi etiketleri
        self.lbl_course = ctk.CTkLabel(
            self.details_sub_frame, text='Ders: -', anchor='w')
        self.lbl_course.grid(row=0, column=0, sticky='w', padx=10, pady=5)

        self.lbl_type_group = ctk.CTkLabel(
            self.details_sub_frame, text='Tür/Grup: -', anchor='w')
        self.lbl_type_group.grid(row=1, column=0, sticky='w', padx=10, pady=5)

        self.lbl_date_duration = ctk.CTkLabel(
            self.details_sub_frame, text='Tarih/Süre: -', anchor='w')
        self.lbl_date_duration.grid(row=2, column=0, sticky='w', padx=10, pady=5)

        # Dosya işlemleri
        self.files_frame = ctk.CTkFrame(self.details_sub_frame, fg_color='transparent')
        self.files_frame.grid(row=3, column=0, sticky='ew', padx=10, pady=10)

        self.btn_open_word = ctk.CTkButton(
            self.files_frame, text='📄 Word Dosyası Aç',
            command=self.open_word_file, state='disabled')
        self.btn_open_word.pack(fill='x', pady=3)

        self.btn_open_key = ctk.CTkButton(
            self.files_frame, text='🔑 Cevap Anahtarı Aç',
            command=self.open_key_file, state='disabled')
        self.btn_open_key.pack(fill='x', pady=3)

    def load_data(self):
        """Dersleri ve geçmiş sınavları yükle"""
        try:
            with db_manager.session_scope() as session:
                # Dersler
                course_objs = session.query(Course).filter_by(
                    is_active=True).order_by(Course.code).all()
                self.courses = [
                    SimpleNamespace(id=c.id, code=c.code, name=c.name, instructor=c.instructor)
                    for c in course_objs
                ]

                course_names = [f'{c.code} - {c.name}' for c in self.courses]
                if course_names:
                    self.course_combo.configure(values=course_names)
                    self.course_combo.set(course_names[0])
                    self.on_course_change()
                else:
                    self.course_combo.configure(values=['Önce ders ekleyin'])
                    self.course_combo.set('Önce ders ekleyin')

                # Geçmiş sınavlar
                exam_objs = session.query(Exam).order_by(
                    Exam.created_at.desc()).all()
                self.past_exams = []
                for e in exam_objs:
                    course = session.query(Course).filter_by(
                        id=e.course_id).first()
                    course_code = course.code if course else '?'
                    q_count = session.query(ExamQuestion).filter_by(
                        exam_id=e.id).count()
                    self.past_exams.append(SimpleNamespace(
                        id=e.id,
                        course_id=e.course_id,
                        course_code=course_code,
                        exam_name=e.exam_name,
                        exam_type=e.exam_type,
                        exam_group=getattr(e, 'exam_group', '-'),
                        exam_date=getattr(e, 'exam_date', ''),
                        duration=getattr(e, 'duration', 60),
                        question_count=q_count,
                        word_file=getattr(e, 'word_file', None),
                        key_file=getattr(e, 'key_file', None),
                        created_at=e.created_at
                    ))

            self.display_past_exams()
            logger.info(f'{len(self.courses)} ders, {len(self.past_exams)} sınav yüklendi')

        except Exception as e:
            logger.error(f'Veri yükleme hatası: {e}')
            messagebox.showerror('Hata', f'Veriler yüklenemedi:\n{e}')

    def on_course_change(self, value=None):
        """Ders değiştiğinde mevcut soru sayısını güncelle"""
        self._update_available_count()

    def on_exam_type_change(self, value=None):
        """Sınav türü değişince mevcut soru sayısını güncelle"""
        self._update_available_count()

    def _get_question_type_filter(self, exam_type: str):
        """
        Sınav türüne göre hangi soru türlerinin dahil edileçeğini döndür.
        - Vize      → ['Vize', 'Genel']
        - Final     → ['Final', 'Genel']
        - Bütünleme → ['Vize', 'Final', 'Genel']  (tümü)
        - Mazeret   → ['Vize', 'Final', 'Genel']  (tümü)
        - Quiz/Diğer→ ['Genel']  (sadece genel)
        """
        et = exam_type.strip() if exam_type else ''
        if et == 'Vize':
            return ['Vize', 'Genel']
        elif et == 'Final':
            return ['Final', 'Genel']
        elif et in ('Bütünleme', 'Mazeret'):
            return ['Vize', 'Final', 'Genel']
        else:
            return ['Vize', 'Final', 'Genel']  # Quiz vb. için hepsini göster

    def _update_available_count(self):
        """Seçili ders + sınav türüne göre mevcut soru sayısını güncelle."""
        course_text = self.course_combo.get()
        if not course_text or ' - ' not in course_text:
            self.available_label.configure(text='(Mevcut: -)')
            return

        course_code = course_text.split(' - ')[0]
        course = next((c for c in self.courses if c.code == course_code), None)
        if not course:
            return

        exam_type = self.exam_type_combo.get()
        allowed_types = self._get_question_type_filter(exam_type)

        try:
            with db_manager.session_scope() as session:
                q_count = session.query(Question).filter(
                    Question.course_id == course.id,
                    Question.is_active == True,
                    Question.question_type.in_(allowed_types)
                ).count()
                self.available_label.configure(text=f'(Mevcut: {q_count})')
        except Exception as e:
            logger.warning(f'Soru sayısı alınamadı: {e}')

    def create_exam(self):
        """Sınav oluştur ve Word dosyası üret"""
        # Validasyon
        course_text = self.course_combo.get()
        if not course_text or course_text in ('Önce ders ekleyin', 'Yükleniyor...'):
            messagebox.showwarning('Uyarı', 'Lütfen bir ders seçin!')
            return

        course_code = course_text.split(' - ')[0]
        course = next((c for c in self.courses if c.code == course_code), None)
        if not course:
            messagebox.showwarning('Uyarı', 'Geçersiz ders seçimi!')
            return

        if self.manual_select_var.get():
            if not self.selected_manual_question_ids:
                messagebox.showwarning('Uyarı', 'Lütfen önce "Soruları Seç..." butonuna tıklayarak sınav sorularını seçin!')
                return
            q_count = len(self.selected_manual_question_ids)
        else:
            try:
                q_count = int(self.question_count_entry.get().strip() or '20')
            except ValueError:
                messagebox.showwarning('Uyarı', 'Geçerli bir soru sayısı girin!')
                return

        try:
            duration = int(self.duration_entry.get().strip() or '60')
        except ValueError:
            duration = 60

        exam_type = self.exam_type_combo.get()
        exam_group = self.exam_group_combo.get()
        exam_date = self.exam_date_entry.get().strip()
        shuffle_q = self.shuffle_questions_var.get()
        shuffle_a = self.shuffle_answers_var.get()
        create_key = self.create_answer_key_var.get()

        # Zorluk dağılımı
        easy_pct = medium_pct = hard_pct = None
        try:
            if self.easy_percent.get().strip():
                easy_pct = int(self.easy_percent.get().strip())
            if self.medium_percent.get().strip():
                medium_pct = int(self.medium_percent.get().strip())
            if self.hard_percent.get().strip():
                hard_pct = int(self.hard_percent.get().strip())
        except ValueError:
            pass

        try:
            # Soruları çek — sınav türüne göre filtrele
            allowed_types = self._get_question_type_filter(exam_type)
            with db_manager.session_scope() as session:
                from sqlalchemy import Column as _Col
                base_query = session.query(Question).filter(
                    Question.course_id == course.id,
                    Question.is_active == True,
                    Question.question_type.in_(allowed_types)
                )

                if self.manual_select_var.get():
                    # Manuel Soru Seçimi Aktifse
                    selected_unsorted = session.query(Question).filter(
                        Question.id.in_(self.selected_manual_question_ids)
                    ).all()
                    # Seçim sırasını koru
                    selected_map = {q.id: q for q in selected_unsorted}
                    selected = [selected_map[qid] for qid in self.selected_manual_question_ids if qid in selected_map]
                else:
                    # Otomatik Soru Seçimi Aktifse - Mükerrer Soru Filtreleri
                    anti_col = self.anti_collision_combo.get()
                    if anti_col == 'Son 6 Ay':
                        from datetime import datetime as dt, timedelta
                        six_months_ago = dt.now() - timedelta(days=180)
                        base_query = base_query.filter(
                            (Question.last_used == None) | (Question.last_used < six_months_ago)
                        )
                    elif anti_col == 'Son 1 Yıl':
                        from datetime import datetime as dt, timedelta
                        one_year_ago = dt.now() - timedelta(days=365)
                        base_query = base_query.filter(
                            (Question.last_used == None) | (Question.last_used < one_year_ago)
                        )
                    elif anti_col == 'Daha Önce Kullanılanlar':
                        base_query = base_query.filter(
                            (Question.usage_count == 0) | (Question.usage_count == None)
                        )

                    if easy_pct is not None and medium_pct is not None and hard_pct is not None:
                        # Zorluk bazlı seçim
                        total = easy_pct + medium_pct + hard_pct
                        n_easy = round(q_count * easy_pct / total)
                        n_medium = round(q_count * medium_pct / total)
                        n_hard = q_count - n_easy - n_medium

                        easy_qs = base_query.filter(Question.difficulty == 'easy').all()
                        med_qs = base_query.filter(Question.difficulty == 'medium').all()
                        hard_qs = base_query.filter(Question.difficulty == 'hard').all()

                        selected = (
                            random.sample(easy_qs, min(n_easy, len(easy_qs))) +
                            random.sample(med_qs, min(n_medium, len(med_qs))) +
                            random.sample(hard_qs, min(n_hard, len(hard_qs)))
                        )
                    else:
                        all_qs = base_query.all()
                        if len(all_qs) < q_count:
                            messagebox.showwarning(
                                'Uyarı',
                                f'Yeterli soru yok! Mevcut: {len(all_qs)}, '
                                f'İstenen: {q_count}\n'
                                f'(Sınav türü: {exam_type} → '
                                f'Soru türleri: {", ".join(allowed_types)})')
                            if not messagebox.askyesno(
                                    'Devam?',
                                    f'Mevcut {len(all_qs)} soruyla devam edilsin mi?'):
                                return
                            q_count = len(all_qs)
                        selected = random.sample(all_qs, min(q_count, len(all_qs)))

                if shuffle_q:
                    random.shuffle(selected)

                # Sınav adı
                exam_name = f'{course.code}_{exam_type}_{exam_group}_{exam_date}'.replace(
                    ' ', '_').replace('.', '')

                # DB kaydı
                exam = Exam(
                    course_id=course.id,
                    exam_name=exam_name,
                    exam_type=exam_type,
                    exam_group=exam_group,
                    exam_date=exam_date,
                    duration=duration,
                    question_count=len(selected),
                    created_at=datetime.now()
                )
                session.add(exam)
                session.flush()

                for order, q in enumerate(selected, 1):
                    eq = ExamQuestion(
                        exam_id=exam.id,
                        question_id=q.id,
                        question_order=order
                    )
                    session.add(eq)
                    
                    # Soru istatistiklerini güncelle
                    q.usage_count = (q.usage_count or 0) + 1
                    q.last_used = datetime.now()

                exam_id = exam.id

                # Word üretimi için veri hazırla — WordGenerator.create_exam formatı
                question_data = []
                for q in selected:
                    opt_details = {
                        'A': {'text': q.option_a or '', 'image': getattr(q, 'option_a_image_path', None)},
                        'B': {'text': q.option_b or '', 'image': getattr(q, 'option_b_image_path', None)},
                        'C': {'text': q.option_c or '', 'image': getattr(q, 'option_c_image_path', None)},
                        'D': {'text': q.option_d or '', 'image': getattr(q, 'option_d_image_path', None)},
                    }
                    if q.option_e or getattr(q, 'option_e_image_path', None):
                        opt_details['E'] = {'text': q.option_e or '', 'image': getattr(q, 'option_e_image_path', None)}

                    if shuffle_a:
                        active_keys = sorted(opt_details.keys())
                        shuffled_keys = active_keys.copy()
                        random.shuffle(shuffled_keys)
                        
                        new_opt_details = {}
                        new_correct = q.correct_answer.upper() if q.correct_answer else 'A'
                        
                        for i, old_key in enumerate(shuffled_keys):
                            new_key = active_keys[i]
                            new_opt_details[new_key] = opt_details[old_key]
                            if old_key == (q.correct_answer.upper() if q.correct_answer else 'A'):
                                new_correct = new_key
                                
                        opt_details = new_opt_details
                    else:
                        new_correct = q.correct_answer.upper() if q.correct_answer else 'A'

                    question_data.append({
                        'question_text': q.question_text,
                        'option_a': opt_details.get('A', {}).get('text', ''),
                        'option_b': opt_details.get('B', {}).get('text', ''),
                        'option_c': opt_details.get('C', {}).get('text', ''),
                        'option_d': opt_details.get('D', {}).get('text', ''),
                        'option_e': opt_details.get('E', {}).get('text', ''),
                        'option_a_image_path': opt_details.get('A', {}).get('image'),
                        'option_b_image_path': opt_details.get('B', {}).get('image'),
                        'option_c_image_path': opt_details.get('C', {}).get('image'),
                        'option_d_image_path': opt_details.get('D', {}).get('image'),
                        'option_e_image_path': opt_details.get('E', {}).get('image'),
                        'correct_answer': new_correct,
                        'question_image_path': getattr(q, 'image_path', None),
                    })

            # Word oluştur (her ders için ayrı klasör altında)
            course_dir_name = f'{course.code} - {course.name}'
            for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
                course_dir_name = course_dir_name.replace(char, '_')
                
            output_dir = Path(config.EXPORTS_DIR) / course_dir_name
            output_dir.mkdir(parents=True, exist_ok=True)

            word_path = output_dir / f'{exam_name}.docx'
            key_path = output_dir / f'{exam_name}_cevap_anahtari.docx' if create_key else None

            institution = db_manager.get_setting('institution_name', config.APP_AUTHOR)
            exam_info = {
                'course_name': course.name,
                'exam_type': exam_type,
                'exam_group': exam_group,
                'exam_date': exam_date,
                'duration': duration,
                'question_count': len(question_data),
                'institution': institution,
                'instructor': getattr(course, 'instructor', '') or '',
                'font_size': int(self.font_size_combo.get() or 11),
            }

            # WordGenerator.create_exam(exam_data, questions, output_path)
            WordGenerator.create_exam(exam_info, question_data, str(word_path))

            if create_key and key_path:
                WordGenerator.create_answer_key(exam_info, question_data, str(key_path))

            # Dosya yollarını kaydet
            with db_manager.session_scope() as session:
                saved_exam = session.query(Exam).filter_by(id=exam_id).first()
                if saved_exam:
                    saved_exam.word_file = str(word_path)
                    if key_path:
                        saved_exam.key_file = str(key_path)

            self.load_data()

            success_msg = (
                f'Sınav başarıyla oluşturuldu!\n\n'
                f'Word dosyası:\n{word_path}'
            )
            if key_path:
                success_msg += f'\n\nCevap anahtarı:\n{key_path}'

            messagebox.showinfo('Sınav Oluşturuldu', success_msg)

            # Sınav oluşturulduktan sonra hedef klasörü aç
            import os
            try:
                os.startfile(str(output_dir.resolve()))
            except Exception as e:
                logger.error(f'Klasör açma hatası: {e}')

            if self.status_callback:
                self.status_callback(f'Sınav oluşturuldu: {exam_name}')

        except Exception as e:
            logger.error(f'Sinav olusturma hatasi: {e}', exc_info=True)
            messagebox.showerror('Hata', f'Sinav olusturulurken hata:\n{e}')

    def toggle_manual_selection(self):
        if self.manual_select_var.get():
            self.question_count_entry.configure(state='disabled')
            self.btn_select_questions.configure(state='normal')
            self.selected_manual_question_ids = []
            self.btn_select_questions.configure(text='Soruları Seç (0 seçildi)...')
        else:
            self.question_count_entry.configure(state='normal')
            self.btn_select_questions.configure(state='disabled')

    def open_manual_selection_dialog(self):
        course_text = self.course_combo.get()
        if not course_text or course_text in ('Önce ders ekleyin', 'Yükleniyor...'):
            messagebox.showwarning('Uyarı', 'Lütfen önce bir ders seçin!')
            return
            
        course_code = course_text.split(' - ')[0]
        course = next((c for c in self.courses if c.code == course_code), None)
        if not course:
            return
            
        exam_type = self.exam_type_combo.get()
        allowed_types = self._get_question_type_filter(exam_type)
        
        from gui.manual_selection_dialog import ManualSelectionDialog
        dialog = ManualSelectionDialog(
            self,
            course_id=course.id,
            allowed_types=allowed_types,
            selected_question_ids=self.selected_manual_question_ids
        )
        if dialog.result is not None:
            self.selected_manual_question_ids = dialog.result
            self.btn_select_questions.configure(text=f'Soruları Seç ({len(self.selected_manual_question_ids)} seçildi)...')

    def preview_exam(self):
        """Sınav önizlemesi"""
        messagebox.showinfo(
            'Önizleme',
            'Sınav oluşturulduğunda Word dosyasını açarak önizleyebilirsiniz.'
        )

    def display_past_exams(self):
        """Geçmiş sınavları Treeview'da göster"""
        self.exams_tree.delete(*self.exams_tree.get_children())
        for exam in self.past_exams:
            date_str = str(exam.exam_date)[:10] if exam.exam_date else '-'
            self.exams_tree.insert('', 'end', iid=str(exam.id), values=(
                exam.course_code,
                exam.exam_type,
                exam.exam_group,
                date_str,
                exam.question_count
            ))

    def _on_exam_select(self, event=None):
        """Sınav seçildiğinde detayları göster"""
        selection = self.exams_tree.selection()
        if not selection:
            return
        try:
            exam_id = int(selection[0])
            exam = next((e for e in self.past_exams if e.id == exam_id), None)
            if exam:
                self.show_exam_details(exam)
        except (ValueError, StopIteration):
            return

    def clear_detail_panel(self):
        """Detay panelini temizle"""
        self.lbl_course.configure(text='Ders: -')
        self.lbl_type_group.configure(text='Tür/Grup: -')
        self.lbl_date_duration.configure(text='Tarih/Süre: -')
        self.btn_open_word.configure(state='disabled')
        self.btn_open_key.configure(state='disabled')
        self.selected_exam = None

    def show_exam_details(self, exam):
        """Seçili sınavın detaylarını göster"""
        self.selected_exam = exam
        self.lbl_detail_title.configure(text=f'📄 {exam.exam_name}')
        self.lbl_course.configure(text=f'Ders: {exam.course_code}')
        self.lbl_type_group.configure(
            text=f'Tür/Grup: {exam.exam_type} / {exam.exam_group}')
        duration = exam.duration if exam.duration else '-'
        self.lbl_date_duration.configure(
            text=f'Tarih: {exam.exam_date} | Süre: {duration} dk')

        # Dosya butonları
        if exam.word_file and Path(exam.word_file).exists():
            self.btn_open_word.configure(state='normal')
        else:
            self.btn_open_word.configure(state='disabled')

        if exam.key_file and Path(exam.key_file).exists():
            self.btn_open_key.configure(state='normal')
        else:
            self.btn_open_key.configure(state='disabled')

    def open_word_file(self):
        """Word dosyasını aç"""
        if not self.selected_exam or not self.selected_exam.word_file:
            messagebox.showwarning('Uyarı', 'Word dosyası bulunamadı!')
            return
        try:
            os.startfile(self.selected_exam.word_file)
        except Exception as e:
            messagebox.showerror('Hata', f'Dosya açılamadı:\n{e}')

    def open_key_file(self):
        """Cevap anahtarı dosyasını aç"""
        if not self.selected_exam or not self.selected_exam.key_file:
            messagebox.showwarning('Uyarı', 'Cevap anahtarı bulunamadı!')
            return
        try:
            os.startfile(self.selected_exam.key_file)
        except Exception as e:
            messagebox.showerror('Hata', f'Dosya açılamadı:\n{e}')
