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
            btn_frame, text='+ Yeni Soru', command=self.new_question, width=120)
        self.btn_new.pack(side='left', padx=5)

        self.btn_refresh = ctk.CTkButton(
            btn_frame, text='Yenile', command=self.load_data, width=90)
        self.btn_refresh.pack(side='left', padx=5)

        self.btn_ocr = ctk.CTkButton(
            btn_frame, text='Gorselden Soru Ekle',
            command=self.ocr_from_image,
            width=160,
            fg_color='#e65100', hover_color='#bf360c')
        self.btn_ocr.pack(side='left', padx=5)

        self.btn_import = ctk.CTkButton(
            btn_frame, text='Toplu Soru Ekle',
            command=self.import_questions, width=130)
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

        # Soru türü filtresi
        ctk.CTkLabel(filter_frame, text='Tür:').grid(
            row=1, column=0, sticky='w', pady=5)
        self.type_filter = ctk.CTkComboBox(
            filter_frame,
            values=['Tümü', 'Genel', 'Vize', 'Final'],
            command=self.filter_questions
        )
        self.type_filter.grid(row=1, column=1, sticky='ew', padx=(5, 0), pady=5)
        self.type_filter.set('Tümü')

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

        cols = ('ders', 'tur', 'soru', 'zorluk', 'gorsel')
        self.questions_tree = ttk.Treeview(
            list_frame, columns=cols, show='headings',
            style='Questions.Treeview', selectmode='browse'
        )

        self.questions_tree.heading('ders', text='Ders',
                                    command=lambda: self._sort_tree('ders'))
        self.questions_tree.heading('tur', text='Tür',
                                    command=lambda: self._sort_tree('tur'))
        self.questions_tree.heading('soru', text='Soru Metni',
                                    command=lambda: self._sort_tree('soru'))
        self.questions_tree.heading('zorluk', text='Zorluk',
                                    command=lambda: self._sort_tree('zorluk'))
        self.questions_tree.heading('gorsel', text='Görsel',
                                    command=lambda: self._sort_tree('gorsel'))

        self.questions_tree.column('ders', width=65, minwidth=55, stretch=False)
        self.questions_tree.column('tur', width=65, minwidth=55, stretch=False)
        self.questions_tree.column('soru', width=170, minwidth=100, stretch=True)
        self.questions_tree.column('zorluk', width=55, minwidth=45, stretch=False)
        self.questions_tree.column('gorsel', width=50, minwidth=40, stretch=False)

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

        # Soru türü
        ctk.CTkLabel(form_frame, text='Soru Türü:*', anchor='w').grid(
            row=8, column=0, sticky='w', pady=8, padx=(0, 10))
        self.question_type_combo = ctk.CTkComboBox(
            form_frame, values=['Genel', 'Vize', 'Final'])
        self.question_type_combo.grid(row=8, column=1, sticky='ew', pady=8)
        self.question_type_combo.set('Genel')

        # Zorluk
        ctk.CTkLabel(form_frame, text='Zorluk:', anchor='w').grid(
            row=9, column=0, sticky='w', pady=8, padx=(0, 10))
        self.difficulty = ctk.CTkComboBox(
            form_frame, values=['easy', 'medium', 'hard'])
        self.difficulty.grid(row=9, column=1, sticky='ew', pady=8)
        self.difficulty.set('medium')

        # Konu
        ctk.CTkLabel(form_frame, text='Konu:', anchor='w').grid(
            row=10, column=0, sticky='w', pady=8, padx=(0, 10))
        self.topic_entry = ctk.CTkEntry(form_frame, placeholder_text='Konusu...')
        self.topic_entry.grid(row=10, column=1, sticky='ew', pady=8)

        # Etiketler
        ctk.CTkLabel(form_frame, text='Etiketler:', anchor='w').grid(
            row=11, column=0, sticky='w', pady=8, padx=(0, 10))
        self.tags_entry = ctk.CTkEntry(
            form_frame, placeholder_text='Virgülle ayırın...')
        self.tags_entry.grid(row=11, column=1, sticky='ew', pady=8)

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

    # ─────────────────────────────────────────────────────────────
    # Gorsel yonetimi
    # ─────────────────────────────────────────────────────────────

    def create_image_section(self):
        """Soru ve her sik icin ayri gorsel alani (Sec/Kirp/X butonlari)"""
        img_frame = ctk.CTkScrollableFrame(self.detail_frame, height=300)
        img_frame.grid(row=2, column=0, sticky='ew', padx=15, pady=10)
        img_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            img_frame, text='Gorsel Yonetimi',
            font=config.FONTS.get('subheading', ('Segoe UI', 12, 'bold'))
        ).grid(row=0, column=0, columnspan=4, pady=(8, 4), padx=10, sticky='w')

        # (etiket, image_paths anahtarı) çiftleri
        image_rows = [
            ('Soru Resmi:', 'question'),
            ('Sik A Resmi:', 'option_a'),
            ('Sik B Resmi:', 'option_b'),
            ('Sik C Resmi:', 'option_c'),
            ('Sik D Resmi:', 'option_d'),
            ('Sik E Resmi:', 'option_e'),
        ]
        self._img_labels = {}  # key -> CTkLabel

        for row_idx, (label_text, key) in enumerate(image_rows, start=1):
            ctk.CTkLabel(img_frame, text=label_text, anchor='w', width=100).grid(
                row=row_idx, column=0, sticky='w', padx=(10, 5), pady=4)

            lbl = ctk.CTkLabel(img_frame, text='Resim secilmedi',
                               text_color='gray', anchor='w')
            lbl.grid(row=row_idx, column=1, sticky='ew', padx=5, pady=4)
            self._img_labels[key] = lbl

            # Sec butonu
            ctk.CTkButton(
                img_frame, text='Sec', width=50,
                command=lambda k=key: self._pick_image(k)
            ).grid(row=row_idx, column=2, padx=3, pady=4)

            # Kirp butonu
            ctk.CTkButton(
                img_frame, text='Kirp', width=50,
                command=lambda k=key: self._crop_image(k)
            ).grid(row=row_idx, column=3, padx=3, pady=4)

            # Sil butonu
            ctk.CTkButton(
                img_frame, text='X', width=30,
                fg_color='#c62828', hover_color='#b71c1c',
                command=lambda k=key: self._remove_image(k)
            ).grid(row=row_idx, column=4, padx=(3, 10), pady=4)

    def _pick_image(self, key: str):
        """Verilen key icin dosya secici ac"""
        filepath = filedialog.askopenfilename(
            title=f'{key} icin gorsel sec',
            filetypes=[('Resim dosyalari', '*.png *.jpg *.jpeg *.bmp *.tiff *.webp'),
                       ('Tum dosyalar', '*.*')]
        )
        if not filepath:
            return
        self.image_paths[key] = filepath
        self._update_img_label(key)

    def _crop_image(self, key: str):
        """Verilen key icin kirpma dialogu ac"""
        path = self.image_paths.get(key)
        if not path:
            messagebox.showwarning('Uyari', 'Once bir gorsel secin!')
            return
        try:
            from gui.crop_dialog import CropDialog
            dialog = CropDialog(self, path)
            dialog.wait_window()
            # CropDialog sonucu dondururse guncelle
            if hasattr(dialog, 'result_path') and dialog.result_path:
                self.image_paths[key] = dialog.result_path
                self._update_img_label(key)
        except Exception as e:
            logger.error(f'Kirpma hatasi: {e}')
            messagebox.showerror('Hata', f'Kirpma islemi basarisiz:\n{e}')

    def _remove_image(self, key: str):
        """Verilen key'in gorselini kaldir"""
        self.image_paths[key] = None
        self._update_img_label(key)

    def _update_img_label(self, key: str):
        """Tek bir gorsel etiketini guncelle"""
        lbl = self._img_labels.get(key)
        if not lbl:
            return
        path = self.image_paths.get(key)
        if path:
            lbl.configure(text=Path(path).name, text_color='#4caf50')
        else:
            lbl.configure(text='Resim secilmedi', text_color='gray')

    def clear_image(self):
        """Tum gorselleri temizle"""
        self.image_paths = {k: None for k in self.image_paths}
        for key in self._img_labels:
            self._update_img_label(key)

    # Geriye donuk uyumluluk icin
    def update_image_label(self):
        for key in self._img_labels:
            self._update_img_label(key)

    def select_image(self):
        """Sadece soru gorseli sec (geriye donuk uyumluluk)"""
        self._pick_image('question')

    # ─────────────────────────────────────────────────────────────
    # OCR
    # ─────────────────────────────────────────────────────────────

    def ocr_from_image(self):
        """Bir gorsel secip Windows OCR ile soru metnini ve siklari otomatik doldur"""
        filepath = filedialog.askopenfilename(
            title='OCR icin gorsel sec',
            filetypes=[('Resim dosyalari', '*.png *.jpg *.jpeg *.bmp *.tiff *.webp'),
                       ('Tum dosyalar', '*.*')]
        )
        if not filepath:
            return

        # Soru gorselini kaydet
        self.image_paths['question'] = filepath
        self._update_img_label('question')

        try:
            raw_text = OCRHelper.get_text_from_image(filepath)
            if not raw_text:
                messagebox.showwarning(
                    'OCR', 'Gorseldan metin alinamadi.\n'
                           'Gorselin net ve metin icermesini saglayin.')
                return

            # Soru ve siklari ayir
            options, question = self.split_question_and_options(raw_text)

            if question:
                self.question_text.delete('1.0', 'end')
                self.question_text.insert('1.0', question)

            for opt_key, text in options.items():
                if opt_key in self.option_entries:
                    self.option_entries[opt_key].delete(0, 'end')
                    self.option_entries[opt_key].insert(0, text)

            messagebox.showinfo(
                'OCR Tamamlandi',
                f'Metin basariyla aktarildi.\n'
                f'Soru: {question[:60]}...\n'
                f'Bulunan sik sayisi: {len(options)}\n\n'
                f'Lutfen bilgileri kontrol edip kaydedin.'
            )
        except Exception as e:
            logger.error(f'OCR hatasi: {e}')
            messagebox.showerror('Hata', f'OCR islemi basarisiz:\n{e}')

    def import_question_from_image(self, extracted_data):
        """OCR ile cikarilan veriyi forma doldur"""
        if not extracted_data:
            return
        if 'question' in extracted_data and extracted_data['question']:
            self.question_text.delete('1.0', 'end')
            self.question_text.insert('1.0', extracted_data['question'])
        for name in ['a', 'b', 'c', 'd', 'e']:
            key = f'option_{name}'
            if key in extracted_data and extracted_data[key]:
                if key in self.option_entries:
                    self.option_entries[key].delete(0, 'end')
                    self.option_entries[key].insert(0, extracted_data[key])

    def split_question_and_options(self, text):
        """Metin icinden soru ve siklari ayir"""
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
                options[f'option_{letter.lower()}'] = match.group(2).strip()
            else:
                question_lines.append(line)
        return options, '\n'.join(question_lines).strip()

    # ─────────────────────────────────────────────────────────────
    # Toplu soru import (Excel / CSV / Word / PDF)
    # ─────────────────────────────────────────────────────────────

    def import_questions(self):
        """Excel/CSV/Word/PDF dosyalarindan toplu soru ice aktar"""
        filepath = filedialog.askopenfilename(
            title='Soru Dosyasi Sec',
            filetypes=[
                ('Desteklenen dosyalar',
                 '*.xlsx *.xls *.csv *.docx *.doc *.pdf'),
                ('Excel dosyalari', '*.xlsx *.xls'),
                ('CSV dosyalari', '*.csv'),
                ('Word dosyalari', '*.docx *.doc'),
                ('PDF dosyalari', '*.pdf'),
                ('Tum dosyalar', '*.*')
            ]
        )
        if not filepath:
            return

        ext = Path(filepath).suffix.lower()
        try:
            if ext in ('.docx', '.doc'):
                self._import_from_word(filepath)
            elif ext == '.pdf':
                self._import_from_pdf(filepath)
            else:
                self._import_from_excel_csv(filepath)
        except Exception as e:
            logger.error(f'Toplu ice aktarma hatasi: {e}')
            messagebox.showerror('Hata', f'Dosya okuma hatasi:\n{e}')

    def _ask_import_target(self, default_q_type='Genel'):
        """
        Hangi derse ve hangi soru turune eklenecegini soran mini dialog.
        (course_id, question_type) tuple dondurur; iptal edilirse (None, None).
        """
        if not self.courses:
            messagebox.showwarning('Uyari', 'Once en az bir ders ekleyin!')
            return None, None

        win = ctk.CTkToplevel(self)
        win.title('Toplu Ekleme Ayarlari')
        win.geometry('380x220')
        win.grab_set()
        win.resizable(False, False)

        result = {'course_id': None, 'q_type': default_q_type, 'ok': False}

        ctk.CTkLabel(win, text='Ders secin:').pack(pady=(18, 4))
        course_vals = [f'{c.code} - {c.name}' for c in self.courses]
        course_combo = ctk.CTkComboBox(win, values=course_vals, width=300)
        course_combo.pack()
        course_combo.set(course_vals[0])

        ctk.CTkLabel(win, text='Soru Turu:').pack(pady=(12, 4))
        type_combo = ctk.CTkComboBox(win, values=['Genel', 'Vize', 'Final'], width=300)
        type_combo.pack()
        type_combo.set(default_q_type)

        def on_ok():
            sel = course_combo.get()
            code = sel.split(' - ')[0]
            course = next((c for c in self.courses if c.code == code), None)
            result['course_id'] = course.id if course else self.courses[0].id
            result['q_type'] = type_combo.get()
            result['ok'] = True
            win.destroy()

        def on_cancel():
            win.destroy()

        btn_row = ctk.CTkFrame(win, fg_color='transparent')
        btn_row.pack(pady=14)
        ctk.CTkButton(btn_row, text='Tamam', command=on_ok, width=120).pack(
            side='left', padx=8)
        ctk.CTkButton(btn_row, text='Iptal', command=on_cancel,
                      fg_color='gray', width=90).pack(side='left', padx=8)

        win.wait_window()
        if not result['ok']:
            return None, None
        return result['course_id'], result['q_type']

    def _import_from_word(self, filepath):
        """Word dosyasindan sorulari ice aktar"""
        from utils.document_parser import parse_docx
        questions = parse_docx(filepath)
        if not questions:
            messagebox.showwarning('Uyari', 'Dosyada parslanabilir soru bulunamadi.')
            return
        self._bulk_save_parsed(questions, filepath)

    def _import_from_pdf(self, filepath):
        """PDF dosyasindan sorulari ice aktar"""
        from utils.document_parser import parse_pdf
        questions = parse_pdf(filepath)
        if not questions:
            messagebox.showwarning('Uyari', 'PDF\'den parslanabilir soru bulunamadi.')
            return
        self._bulk_save_parsed(questions, filepath)

    def _show_preview_and_save(self, parsed_questions, source_path):
        """Toplu soru önizleme penceresini açar ve onaylanırsa veritabanına kaydeder"""
        from gui.bulk_preview_dialog import BulkPreviewDialog

        dialog = BulkPreviewDialog(self, parsed_questions, self.courses)
        if dialog.result is None:
            return

        res = dialog.result
        course = res['course']
        selected_questions = res['questions']
        difficulty_text = res['difficulty']
        topic = res['topic']
        tags = res['tags']
        question_type = res['question_type']

        diff_map = {'Kolay': 'easy', 'Orta': 'medium', 'Zor': 'hard'}
        difficulty = diff_map.get(difficulty_text, 'medium')

        total = len(selected_questions)
        added = 0
        skipped = 0

        with db_manager.session_scope() as session:
            for q in selected_questions:
                opts = q.get('options', {})
                q_text = q.get('text', '').strip()
                if not q_text:
                    skipped += 1
                    continue
                try:
                    question = Question(
                        course_id=course.id,
                        question_text=q_text,
                        option_a=opts.get('a', ''),
                        option_b=opts.get('b', ''),
                        option_c=opts.get('c', ''),
                        option_d=opts.get('d', ''),
                        option_e=opts.get('e', ''),
                        correct_answer=q.get('correct_answer', 'A').upper(),
                        difficulty=difficulty,
                        question_type=question_type,
                        topic=topic or None,
                        tags=tags or None,
                        is_active=True,
                    )
                    session.add(question)
                    added += 1
                except Exception as e:
                    skipped += 1
                    logger.warning(f'Soru kaydedilemedi: {e}')

        self.load_data()
        messagebox.showinfo(
            'İçe Aktarma Sonucu',
            f'Dosya: {Path(source_path).name}\n'
            f'Seçilen soru: {total}\n'
            f'Eklenen: {added}\n'
            f'Atlanan: {skipped}'
        )
        if self.status_callback:
            self.status_callback(f'{added} soru içe aktarıldı')

    def _bulk_save_parsed(self, parsed_questions, source_path):
        """parse_docx/parse_pdf ciktisini veritabanina kaydet"""
        self._show_preview_and_save(parsed_questions, source_path)

    def _import_from_excel_csv(self, filepath):
        """Excel / CSV'den toplu soru ice aktar"""
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
                f'Dosyada eksik sutunlar:\n{", ".join(missing)}\n\n'
                f'Gerekli sutunlar: {", ".join(required_cols)}'
            )
            return

        parsed_questions = []
        for idx, row in df.iterrows():
            opt_e = ''
            if 'option_e' in df.columns and pd.notna(row.get('option_e')):
                opt_e = str(row['option_e']).strip()

            parsed_questions.append({
                'number': str(idx + 1),
                'text': str(row.get('question', '')).strip(),
                'options': {
                    'a': str(row.get('option_a', '')).strip(),
                    'b': str(row.get('option_b', '')).strip(),
                    'c': str(row.get('option_c', '')).strip() if pd.notna(row.get('option_c')) else '',
                    'd': str(row.get('option_d', '')).strip() if pd.notna(row.get('option_d')) else '',
                    'e': opt_e,
                },
                'correct_answer': str(row.get('correct_answer', 'A')).strip().upper()
            })

        self._show_preview_and_save(parsed_questions, filepath)

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
                        question_type=getattr(q, 'question_type', 'Genel') or 'Genel',
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

        # Tür renk etiketleri
        tur_icon_map = {'Vize': '📘', 'Final': '📕', 'Genel': '📗'}
        difficulty_map = {'easy': '😊', 'medium': '😐', 'hard': '😓'}
        for idx, q in enumerate(self.filtered_questions):
            diff_icon = difficulty_map.get(q.difficulty, '❓')
            has_image = '🖼️' if q.image_path else '-'
            preview = (q.question_text or '')[:55].replace('\n', ' ')
            if len(q.question_text or '') > 55:
                preview += '...'
            q_type = getattr(q, 'question_type', 'Genel') or 'Genel'
            tur_text = f"{tur_icon_map.get(q_type, '📗')} {q_type}"
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.questions_tree.insert(
                '', 'end',
                iid=str(q.id),
                values=(q.course_code, tur_text, preview, diff_icon, has_image),
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
            'tur': 'question_type',
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
        type_filter = self.type_filter.get()

        filtered = self.questions

        # Ders filtresi
        if course_filter and course_filter != 'Tümü':
            code = course_filter.split(' - ')[0]
            filtered = [q for q in filtered if q.course_code == code]

        # Tür filtresi
        if type_filter and type_filter != 'Tümü':
            filtered = [
                q for q in filtered
                if (getattr(q, 'question_type', 'Genel') or 'Genel') == type_filter
            ]

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
        q_type = getattr(question, 'question_type', 'Genel') or 'Genel'
        self.question_type_combo.set(q_type)

        self.topic_entry.delete(0, 'end')
        self.topic_entry.insert(0, question.topic or '')

        self.tags_entry.delete(0, 'end')
        self.tags_entry.insert(0, question.tags or '')

        # Görsel
        self.image_paths['question'] = question.image_path or None
        self.image_paths['option_a'] = question.option_a_image_path or None
        self.image_paths['option_b'] = question.option_b_image_path or None
        self.image_paths['option_c'] = question.option_c_image_path or None
        self.image_paths['option_d'] = question.option_d_image_path or None
        self.image_paths['option_e'] = question.option_e_image_path or None
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
        has_q_image = bool(self.image_paths.get('question'))
        if not question_text and not has_q_image:
            messagebox.showwarning('Uyarı', 'Soru metni veya soru görseli zorunludur!')
            return

        option_a = self.option_entries['option_a'].get().strip()
        option_b = self.option_entries['option_b'].get().strip()
        has_a_image = bool(self.image_paths.get('option_a'))
        has_b_image = bool(self.image_paths.get('option_b'))

        if (not option_a and not has_a_image) or (not option_b and not has_b_image):
            messagebox.showwarning('Uyarı', 'En az A ve B şıkları (metin veya görsel olarak) zorunludur!')
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
                q.question_type = self.question_type_combo.get() or 'Genel'
                q.topic = self.topic_entry.get().strip()
                q.tags = self.tags_entry.get().strip()
                q.is_active = True

                # ID atanması için flush et
                session.flush()

                # Görselleri kaydet / kopyala
                for key in ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e']:
                    img_path = self.image_paths.get(key)
                    db_attr = 'image_path' if key == 'question' else f"{key}_image_path"
                    old_path = getattr(q, db_attr, None)

                    if img_path:
                        img_path_resolved = str(Path(img_path).resolve())
                        old_path_resolved = str(Path(old_path).resolve()) if old_path else None

                        if img_path_resolved != old_path_resolved:
                            if not img_path_resolved.startswith(str(config.IMAGES_DIR.resolve())):
                                try:
                                    saved_path = ImageHandler.save_image(
                                        source_path=img_path,
                                        course_code=course.code,
                                        question_number=str(q.id),
                                        image_type=key
                                    )
                                    setattr(q, db_attr, saved_path)
                                    self.image_paths[key] = saved_path
                                except Exception as e:
                                    logger.error(f"Görsel kaydetme hatası ({key}): {e}")
                            else:
                                setattr(q, db_attr, img_path)
                    else:
                        if old_path:
                            try:
                                ImageHandler.delete_image(old_path)
                            except Exception as e:
                                logger.warning(f"Eski görsel silinemedi: {e}")
                        setattr(q, db_attr, None)

                # question_image_path'i de eşitleyelim
                q.question_image_path = q.image_path

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
        self.question_type_combo.set('Genel')
        self.topic_entry.delete(0, 'end')
        self.tags_entry.delete(0, 'end')
        self.clear_image()
