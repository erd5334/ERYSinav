"""
Soru yönetimi sayfası
"""
import os
import re
import logging
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from database import db_manager, Course, Question
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from utils.image_handler import ImageHandler
from gui.crop_dialog import CropDialog
from utils.ocr_helper import OCRHelper
import config
import pandas as pd

logger = logging.getLogger(__name__)


class QuestionsPage(ctk.CTkFrame):
    """Soru yönetim sayfası"""

    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.selected_question = None
        self.questions = []
        self.courses = []
        self.filtered_questions = []
        self.image_paths = {
            'question': None,
            'option_a': None,
            'option_b': None,
            'option_c': None,
            'option_d': None,
            'option_e': None,
        }

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_header()
        self.create_content()
        self.load_data()

    def create_header(self):
        """Sayfa başlığı ve butonlar"""
        header_frame = ctk.CTkFrame(self, fg_color='transparent')
        header_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=20)
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text='📝 Soru Yönetimi',
            font=config.FONTS['title']
        ).grid(row=0, column=0, sticky='w')

        btn_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
        btn_frame.grid(row=0, column=1, sticky='e')

        self.btn_new = ctk.CTkButton(
            btn_frame, text='➕ Yeni Soru', command=self.new_question, width=120)
        self.btn_new.pack(side='left', padx=5)

        self.btn_refresh = ctk.CTkButton(
            btn_frame, text='🔄 Yenile', command=self.load_data, width=100)
        self.btn_refresh.pack(side='left', padx=5)

        self.btn_import = ctk.CTkButton(
            btn_frame, text='📥 Toplu Soru Ekle',
            command=self.import_questions, width=140)
        self.btn_import.pack(side='left', padx=5)

    def create_content(self):
        """İki panel: Sol liste, Sağ detay"""
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky='nsew', padx=20, pady=(0, 20))
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=2)

        self.create_list_panel(content_frame)
        self.create_detail_panel(content_frame)

    def create_list_panel(self, parent):
        """Sol panel: Filtre, arama ve soru listesi"""
        list_frame = ctk.CTkFrame(parent)
        list_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        list_frame.grid_rowconfigure(2, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Ders filtresi
        filter_frame = ctk.CTkFrame(list_frame, fg_color='transparent')
        filter_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        filter_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(filter_frame, text='Ders:').grid(
            row=0, column=0, sticky='w', pady=5)

        self.course_filter = ctk.CTkComboBox(
            filter_frame, values=['Tümü'], command=self.filter_questions)
        self.course_filter.grid(row=0, column=1, sticky='ew', padx=(5, 0), pady=5)
        self.course_filter.set('Tümü')

        # Arama
        search_frame = ctk.CTkFrame(list_frame, fg_color='transparent')
        search_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=10,
                          pady=(0, 6))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text='🔍 Soru ara...')
        self.search_entry.grid(row=0, column=0, sticky='ew')
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_questions())

        # Treeview
        is_dark = config.THEME_MODE == 'dark'
        bg = '#2b2b2b' if is_dark else '#f0f0f0'
        fg = '#ffffff' if is_dark else '#111111'
        sel_bg = '#1f6aa5'
        head_bg = '#1a1a1a' if is_dark else '#dcdcdc'
        row_alt = '#333333' if is_dark else '#e8e8e8'

        style = ttk.Style()
        style.theme_use('default')
        style.configure('Questions.Treeview', background=bg, foreground=fg,
                        fieldbackground=bg, borderwidth=0, rowheight=38,
                        font=('Segoe UI', 9))
        style.configure('Questions.Treeview.Heading',
                        background=head_bg, foreground=fg,
                        font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Questions.Treeview', background=[('selected', sel_bg)],
                  foreground=[('selected', 'white')])

        cols = ('ders', 'soru', 'zorluk', 'gorsel')
        self.questions_tree = ttk.Treeview(
            list_frame, columns=cols, show='headings',
            style='Questions.Treeview', selectmode='browse'
        )

        self.questions_tree.heading('ders', text='Ders',
                                    command=lambda: self._sort_tree('ders'))
        self.questions_tree.heading('soru', text='Soru Metni',
                                    command=lambda: self._sort_tree('soru'))
        self.questions_tree.heading('zorluk', text='Zorluk',
                                    command=lambda: self._sort_tree('zorluk'))
        self.questions_tree.heading('gorsel', text='Görsel',
                                    command=lambda: self._sort_tree('gorsel'))

        self.questions_tree.column('ders', width=70, minwidth=60, stretch=False)
        self.questions_tree.column('soru', width=180, minwidth=100, stretch=True)
        self.questions_tree.column('zorluk', width=60, minwidth=50, stretch=False)
        self.questions_tree.column('gorsel', width=55, minwidth=40, stretch=False)

        self.questions_tree.tag_configure('odd', background=bg)
        self.questions_tree.tag_configure('even', background=row_alt)

        tree_scroll = ctk.CTkScrollbar(list_frame, command=self.questions_tree.yview)
        self.questions_tree.configure(yscrollcommand=tree_scroll.set)

        self.questions_tree.grid(row=2, column=0, sticky='nsew',
                                  padx=(10, 0), pady=(0, 10))
        tree_scroll.grid(row=2, column=1, sticky='ns', pady=(0, 10), padx=(0, 5))

        self.questions_tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self._sort_col = None
        self._sort_rev = False

    def create_detail_panel(self, parent):
        """Sağ panel: Soru ekleme/düzenleme formu"""
        self.detail_frame = ctk.CTkScrollableFrame(parent)
        self.detail_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        self.detail_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.detail_frame, text='Soru Bilgileri',
            font=config.FONTS['heading']
        ).grid(row=0, column=0, pady=(15, 10), padx=15, sticky='w')

        form_frame = ctk.CTkFrame(self.detail_frame, fg_color='transparent')
        form_frame.grid(row=1, column=0, sticky='ew', padx=15)
        form_frame.grid_columnconfigure(1, weight=1)

        # Ders seçimi
        ctk.CTkLabel(form_frame, text='Ders:*', anchor='w').grid(
            row=0, column=0, sticky='w', pady=8, padx=(0, 10))
        self.course_combo = ctk.CTkComboBox(form_frame, values=['Yükleniyor...'])
        self.course_combo.grid(row=0, column=1, sticky='ew', pady=8)

        # Soru metni
        ctk.CTkLabel(form_frame, text='Soru:*', anchor='w').grid(
            row=1, column=0, sticky='nw', pady=8, padx=(0, 10))
        self.question_text = ctk.CTkTextbox(form_frame, height=80)
        self.question_text.grid(row=1, column=1, sticky='ew', pady=8)

        # Şıklar A-E
        option_labels = ['A Şıkkı:*', 'B Şıkkı:*', 'C Şıkkı:*',
                         'D Şıkkı:*', 'E Şıkkı:']
        option_keys = ['option_a', 'option_b', 'option_c', 'option_d', 'option_e']
        self.option_entries = {}
        for i, (lbl, key) in enumerate(zip(option_labels, option_keys)):
            ctk.CTkLabel(form_frame, text=lbl, anchor='w').grid(
                row=2 + i, column=0, sticky='w', pady=5, padx=(0, 10))
            entry = ctk.CTkEntry(form_frame, placeholder_text=f'{key[-1].upper()} şıkkı')
            entry.grid(row=2 + i, column=1, sticky='ew', pady=5)
            self.option_entries[key] = entry

        # Doğru cevap
        ctk.CTkLabel(form_frame, text='Doğru Cevap:*', anchor='w').grid(
            row=7, column=0, sticky='w', pady=8, padx=(0, 10))
        self.correct_answer = ctk.CTkComboBox(
            form_frame, values=['A', 'B', 'C', 'D', 'E'])
        self.correct_answer.grid(row=7, column=1, sticky='ew', pady=8)
        self.correct_answer.set('A')

        # Zorluk
        ctk.CTkLabel(form_frame, text='Zorluk:', anchor='w').grid(
            row=8, column=0, sticky='w', pady=8, padx=(0, 10))
        self.difficulty = ctk.CTkComboBox(
            form_frame, values=['easy', 'medium', 'hard'])
        self.difficulty.grid(row=8, column=1, sticky='ew', pady=8)
        self.difficulty.set('medium')

        # Konu
        ctk.CTkLabel(form_frame, text='Konu:', anchor='w').grid(
            row=9, column=0, sticky='w', pady=8, padx=(0, 10))
        self.topic_entry = ctk.CTkEntry(form_frame, placeholder_text='Konusu...')
        self.topic_entry.grid(row=9, column=1, sticky='ew', pady=8)

        # Etiketler
        ctk.CTkLabel(form_frame, text='Etiketler:', anchor='w').grid(
            row=10, column=0, sticky='w', pady=8, padx=(0, 10))
        self.tags_entry = ctk.CTkEntry(
            form_frame, placeholder_text='Virgülle ayırın...')
        self.tags_entry.grid(row=10, column=1, sticky='ew', pady=8)

        # Görsel bölümü
        self.create_image_section()

        # Butonlar
        btn_frame = ctk.CTkFrame(self.detail_frame, fg_color='transparent')
        btn_frame.grid(row=3, column=0, sticky='ew', padx=15, pady=(10, 15))

        self.btn_save = ctk.CTkButton(
            btn_frame, text='💾 Kaydet', command=self.save_question, height=40)
        self.btn_save.pack(side='left', padx=5, fill='x', expand=True)

        self.btn_delete = ctk.CTkButton(
            btn_frame, text='🗑️ Sil', command=self.delete_question, height=40,
            fg_color='#d32f2f', hover_color='#b71c1c')
        self.btn_delete.pack(side='left', padx=5, fill='x', expand=True)

        self.btn_clear = ctk.CTkButton(
            btn_frame, text='🔄 Temizle', command=self.clear_form, height=40,
            fg_color='gray', hover_color='darkgray')
        self.btn_clear.pack(side='left', padx=5, fill='x', expand=True)

    def create_image_section(self):
        """Görsel yükleme bölümü"""
        img_frame = ctk.CTkFrame(self.detail_frame)
        img_frame.grid(row=2, column=0, sticky='ew', padx=15, pady=10)
        img_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            img_frame, text='🖼️ Görsel Yönetimi',
            font=config.FONTS.get('subheading', ('Segoe UI', 12, 'bold'))
        ).grid(row=0, column=0, pady=10, padx=10, sticky='w')

        # Soru görseli
        ctk.CTkLabel(img_frame, text='Soru görseli:', anchor='w').grid(
            row=1, column=0, sticky='w', padx=10)
        self.btn_import_from_image = ctk.CTkButton(
            img_frame, text='📸 Görsel Seç / OCR',
            command=self.select_image, width=160)
        self.btn_import_from_image.grid(row=1, column=1, padx=10, pady=5)

        self.image_label_lbl = ctk.CTkLabel(
            img_frame, text='Görsel seçilmedi', text_color='gray', anchor='w')
        self.image_label_lbl = ctk.CTkLabel(
            img_frame, text='Görsel seçilmedi', text_color='gray')
        self.image_label_lbl.grid(row=2, column=0, columnspan=2, padx=10, sticky='w')

    def select_image(self):
        """Görsel seç ve OCR ile içe aktar"""
        filepath = filedialog.askopenfilename(
            title='Soru Görseli Seç',
            filetypes=[('Resim dosyaları', '*.png *.jpg *.jpeg *.bmp *.gif *.tiff')]
        )
        if not filepath:
            return

        self.image_paths['question'] = filepath
        self.update_image_label()

        # OCR ile metni çıkar
        try:
            ocr = OCRHelper()
            extracted = ocr.extract_question_and_options(filepath)
            if extracted:
                self.import_question_from_image(extracted)
        except Exception as e:
            logger.warning(f'OCR başarısız: {e}')

    def crop_image(self):
        """Görsel kırpma dialogu"""
        if not self.image_paths.get('question'):
            messagebox.showwarning('Uyarı', 'Önce bir görsel seçin!')
            return
        try:
            dialog = CropDialog(self, self.image_paths['question'])
            dialog.wait_window()
        except Exception as e:
            logger.error(f'Kırpma hatası: {e}')

    def import_question_from_image(self, extracted_data):
        """OCR ile çıkarılan veriyi forma doldur"""
        if not extracted_data:
            return

        if 'question' in extracted_data and extracted_data['question']:
            self.question_text.delete('1.0', 'end')
            self.question_text.insert('1.0', extracted_data['question'])

        option_keys = ['option_a', 'option_b', 'option_c', 'option_d', 'option_e']
        option_names = ['A', 'B', 'C', 'D', 'E']
        for key, name in zip(option_keys, option_names):
            text_key = f'option_{name.lower()}'
            if text_key in extracted_data and extracted_data[text_key]:
                if key in self.option_entries:
                    self.option_entries[key].delete(0, 'end')
                    self.option_entries[key].insert(0, extracted_data[text_key])

    def split_question_and_options(self, text):
        """Metin içinden soru ve şıkları ayır"""
        if not text:
            return {}, text

        options = {}
        lines = text.split('\n')
        question_lines = []
        option_pattern = re.compile(r'^([A-Ea-e])[.)]\s*(.*)')

        for line in lines:
            match = option_pattern.match(line.strip())
            if match:
                letter = match.group(1).upper()
                content = match.group(2).strip()
                options[f'option_{letter.lower()}'] = content
            else:
                question_lines.append(line)

        question = '\n'.join(question_lines).strip()
        return options, question

    def clear_image(self):
        """Görseli temizle"""
        self.image_paths = {k: None for k in self.image_paths}
        self.update_image_label()

    def update_image_label(self):
        """Görsel durumunu güncelle"""
        if self.image_paths.get('question'):
            filename = Path(self.image_paths['question']).name
            self.image_label_lbl.configure(
                text=f'✅ {filename}', text_color='#4caf50')
        else:
            self.image_label_lbl.configure(
                text='Görsel seçilmedi', text_color='gray')

    def import_questions(self):
        """Excel/CSV'den toplu soru içe aktar"""
        filepath = filedialog.askopenfilename(
            title='Soru Dosyası Seç',
            filetypes=[
                ('Excel dosyaları', '*.xlsx *.xls'),
                ('CSV dosyaları', '*.csv'),
                ('Tüm dosyalar', '*.*')
            ]
        )
        if not filepath:
            return

        try:
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath, encoding='utf-8')
            else:
                df = pd.read_excel(filepath)

            required_cols = ['question', 'option_a', 'option_b', 'option_c',
                             'option_d', 'correct_answer']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                messagebox.showerror(
                    'Hata',
                    f'Dosyada eksik sütunlar:\n{", ".join(missing)}\n\n'
                    f'Gerekli sütunlar: {", ".join(required_cols)}'
                )
                return

            added = 0
            skipped = 0
            errors = []

            with db_manager.session_scope() as session:
                # İlk ders
                default_course = session.query(Course).filter_by(
                    is_active=True).first()
                if not default_course:
                    messagebox.showwarning('Uyarı', 'Önce en az bir ders ekleyin!')
                    return

                for idx, row in df.iterrows():
                    try:
                        # Ders kodu varsa bul
                        course = default_course
                        if 'course_code' in df.columns and pd.notna(row['course_code']):
                            found = session.query(Course).filter_by(
                                code=str(row['course_code'])).first()
                            if found:
                                course = found

                        question = Question(
                            course_id=course.id,
                            question_text=str(row['question']),
                            option_a=str(row['option_a']),
                            option_b=str(row['option_b']),
                            option_c=str(row['option_c']),
                            option_d=str(row['option_d']),
                            option_e=str(row.get('option_e', '')) if pd.notna(
                                row.get('option_e', '')) else '',
                            correct_answer=str(row['correct_answer']).upper(),
                            difficulty=str(row.get('difficulty', 'medium')).lower(),
                            topic=str(row.get('topic', '')) if pd.notna(
                                row.get('topic', '')) else '',
                            tags=str(row.get('tags', '')) if pd.notna(
                                row.get('tags', '')) else '',
                            is_active=True
                        )
                        session.add(question)
                        added += 1
                    except Exception as e:
                        errors.append(f'Satır {idx + 2}: {str(e)[:80]}')
                        skipped += 1

            self.load_data()
            msg = f'✅ {added} soru eklendi.'
            if skipped:
                msg += f'\n⚠️ {skipped} soru atlandı.'
            if errors:
                msg += f'\n\nHatalar:\n' + '\n'.join(errors[:5])
            messagebox.showinfo('İçe Aktarma Sonucu', msg)

            if self.status_callback:
                self.status_callback(f'{added} soru içe aktarıldı')

        except Exception as e:
            logger.error(f'Toplu içe aktarma hatası: {e}')
            messagebox.showerror('Hata', f'Dosya okuma hatası:\n{e}')

    def load_data(self):
        """Dersleri ve soruları yükle"""
        try:
            with db_manager.session_scope() as session:
                # Dersler
                course_objs = session.query(Course).filter_by(
                    is_active=True).order_by(Course.code).all()
                self.courses = [
                    SimpleNamespace(id=c.id, code=c.code, name=c.name)
                    for c in course_objs
                ]

                # Combo değerleri güncelle
                course_values = ['Tümü'] + [f'{c.code} - {c.name}'
                                             for c in self.courses]
                self.course_filter.configure(values=course_values)

                course_combo_vals = [f'{c.code} - {c.name}' for c in self.courses]
                if course_combo_vals:
                    self.course_combo.configure(values=course_combo_vals)
                    if not self.selected_question:
                        self.course_combo.set(course_combo_vals[0])
                else:
                    self.course_combo.configure(values=['Önce ders ekleyin'])
                    self.course_combo.set('Önce ders ekleyin')

                # Sorular
                question_objs = session.query(Question).filter_by(
                    is_active=True).order_by(Question.id.desc()).all()
                self.questions = []
                for q in question_objs:
                    course = next((c for c in self.courses if c.id == q.course_id),
                                  None)
                    self.questions.append(SimpleNamespace(
                        id=q.id,
                        course_id=q.course_id,
                        course_code=course.code if course else '?',
                        question_text=q.question_text,
                        option_a=q.option_a,
                        option_b=q.option_b,
                        option_c=q.option_c,
                        option_d=q.option_d,
                        option_e=getattr(q, 'option_e', ''),
                        correct_answer=q.correct_answer,
                        difficulty=q.difficulty,
                        topic=getattr(q, 'topic', ''),
                        tags=getattr(q, 'tags', ''),
                        image_path=getattr(q, 'image_path', None),
                        is_active=q.is_active
                    ))

            self.display_questions()
            if self.status_callback:
                self.status_callback(f'{len(self.questions)} soru yüklendi')

        except Exception as e:
            logger.error(f'Veri yükleme hatası: {e}')
            messagebox.showerror('Hata', f'Veriler yüklenirken hata:\n{e}')

    def display_questions(self, questions=None):
        """Soruları Treeview'da göster"""
        to_display = questions if questions is not None else self.questions
        self.filtered_questions = list(to_display)
        self.questions_tree.delete(*self.questions_tree.get_children())

        difficulty_map = {'easy': '😊', 'medium': '😐', 'hard': '😓'}
        for idx, q in enumerate(self.filtered_questions):
            diff_icon = difficulty_map.get(q.difficulty, '❓')
            has_image = '🖼️' if q.image_path else '-'
            preview = (q.question_text or '')[:60].replace('\n', ' ')
            if len(q.question_text or '') > 60:
                preview += '...'
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.questions_tree.insert(
                '', 'end',
                iid=str(q.id),
                values=(q.course_code, preview, diff_icon, has_image),
                tags=(tag,)
            )

    def _on_tree_select(self, event=None):
        """Treeview seçim olayı"""
        selection = self.questions_tree.selection()
        if not selection:
            return
        try:
            q_id = int(selection[0])
            question = next(
                (q for q in self.filtered_questions if q.id == q_id), None)
            if question:
                self.edit_question(question)
        except (ValueError, StopIteration):
            return

    def _sort_tree(self, col):
        """Sütuna göre sıralama"""
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False

        col_map = {
            'ders': 'course_code',
            'soru': 'question_text',
            'zorluk': 'difficulty',
            'gorsel': 'image_path'
        }
        attr = col_map.get(col)
        if attr:
            self.filtered_questions.sort(
                key=lambda q: (getattr(q, attr) or '').lower(),
                reverse=self._sort_rev
            )
        self.display_questions(self.filtered_questions)

    def filter_questions(self, value=None):
        """Filtrele"""
        search = self.search_entry.get().lower()
        course_filter = self.course_filter.get()

        filtered = self.questions

        # Ders filtresi
        if course_filter and course_filter != 'Tümü':
            code = course_filter.split(' - ')[0]
            filtered = [q for q in filtered if q.course_code == code]

        # Arama filtresi
        if search:
            filtered = [
                q for q in filtered
                if search in (q.question_text or '').lower()
                or search in (q.course_code or '').lower()
                or (q.topic and search in q.topic.lower())
            ]

        self.display_questions(filtered)

    def new_question(self):
        """Yeni soru formu"""
        self.clear_form()
        self.question_text.focus()

    def edit_question(self, question):
        """Soruyu düzenleme formuna yükle"""
        self.selected_question = question

        # Ders seç
        course = next((c for c in self.courses if c.id == question.course_id), None)
        if course:
            self.course_combo.set(f'{course.code} - {course.name}')

        # Soru metni
        self.question_text.delete('1.0', 'end')
        self.question_text.insert('1.0', question.question_text or '')

        # Şıklar
        for key in ['option_a', 'option_b', 'option_c', 'option_d', 'option_e']:
            if key in self.option_entries:
                self.option_entries[key].delete(0, 'end')
                self.option_entries[key].insert(0, getattr(question, key, '') or '')

        # Diğer
        self.correct_answer.set(question.correct_answer or 'A')
        self.difficulty.set(question.difficulty or 'medium')

        self.topic_entry.delete(0, 'end')
        self.topic_entry.insert(0, question.topic or '')

        self.tags_entry.delete(0, 'end')
        self.tags_entry.insert(0, question.tags or '')

        # Görsel
        if question.image_path:
            self.image_paths['question'] = question.image_path
        else:
            self.image_paths['question'] = None
        self.update_image_label()

    def save_question(self):
        """Soruyu kaydet"""
        # Ders bul
        course_text = self.course_combo.get()
        if not course_text or course_text in ('Önce ders ekleyin', 'Yükleniyor...'):
            messagebox.showwarning('Uyarı', 'Lütfen bir ders seçin!')
            return

        course_code = course_text.split(' - ')[0]
        course = next((c for c in self.courses if c.code == course_code), None)
        if not course:
            messagebox.showwarning('Uyarı', 'Geçerli bir ders seçin!')
            return

        question_text = self.question_text.get('1.0', 'end').strip()
        if not question_text:
            messagebox.showwarning('Uyarı', 'Soru metni boş olamaz!')
            return

        option_a = self.option_entries['option_a'].get().strip()
        option_b = self.option_entries['option_b'].get().strip()

        if not option_a or not option_b:
            messagebox.showwarning('Uyarı', 'En az A ve B şıkları zorunludur!')
            return

        try:
            with db_manager.session_scope() as session:
                if self.selected_question:
                    q = session.query(Question).filter_by(
                        id=self.selected_question.id).first()
                    if not q:
                        raise Exception('Soru bulunamadı!')
                    msg = f'Soru güncellendi (ID: {q.id})'
                else:
                    q = Question()
                    session.add(q)
                    msg = 'Yeni soru eklendi'

                q.course_id = course.id
                q.question_text = question_text
                q.option_a = option_a
                q.option_b = option_b
                q.option_c = self.option_entries['option_c'].get().strip()
                q.option_d = self.option_entries['option_d'].get().strip()
                q.option_e = self.option_entries['option_e'].get().strip()
                q.correct_answer = self.correct_answer.get()
                q.difficulty = self.difficulty.get()
                q.topic = self.topic_entry.get().strip()
                q.tags = self.tags_entry.get().strip()
                q.image_path = self.image_paths.get('question')
                q.is_active = True

            self.load_data()
            self.clear_form()
            if self.status_callback:
                self.status_callback(msg)
            messagebox.showinfo('Başarı', msg)

        except Exception as e:
            logger.error(f'Soru kaydetme hatası: {e}')
            messagebox.showerror('Hata', f'Soru kaydedilemedi:\n{e}')

    def delete_question(self):
        """Seçili soruyu sil"""
        if not self.selected_question:
            messagebox.showwarning('Uyarı', 'Lütfen bir soru seçin!')
            return

        if not messagebox.askyesno('Onay', 'Bu soruyu silmek istediğinizden emin misiniz?'):
            return

        try:
            with db_manager.session_scope() as session:
                q = session.query(Question).filter_by(
                    id=self.selected_question.id).first()
                if q:
                    q.is_active = False
                    msg = f'Soru silindi (ID: {q.id})'

            self.load_data()
            self.clear_form()
            if self.status_callback:
                self.status_callback(msg)
            messagebox.showinfo('Başarı', msg)

        except Exception as e:
            logger.error(f'Soru silme hatası: {e}')
            messagebox.showerror('Hata', f'Soru silinemedi:\n{e}')

    def clear_form(self):
        """Formu temizle"""
        self.selected_question = None
        self.question_text.delete('1.0', 'end')
        for entry in self.option_entries.values():
            entry.delete(0, 'end')
        self.correct_answer.set('A')
        self.difficulty.set('medium')
        self.topic_entry.delete(0, 'end')
        self.tags_entry.delete(0, 'end')
        self.clear_image()
