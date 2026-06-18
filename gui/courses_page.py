"""
Ders yönetimi sayfası
"""
import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
import logging
from database import db_manager, Course
from types import SimpleNamespace
import config

logger = logging.getLogger(__name__)


class CoursesPage(ctk.CTkFrame):
    """Ders yönetim sayfası"""

    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.selected_course = None
        self.courses = []
        self.filtered_courses = []

        # Grid düzeni
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_header()
        self.create_content()
        self.load_courses()

    def create_header(self):
        """Sayfa başlığı ve buton alanı"""
        header_frame = ctk.CTkFrame(self, fg_color='transparent')
        header_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=20)
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text='📚 Ders Yönetimi',
            font=config.FONTS['title']
        )
        title.grid(row=0, column=0, sticky='w')

        btn_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
        btn_frame.grid(row=0, column=1, sticky='e')

        self.btn_new = ctk.CTkButton(
            btn_frame,
            text='➕ Yeni Ders',
            command=self.new_course,
            width=120
        )
        self.btn_new.pack(side='left', padx=5)

        self.btn_refresh = ctk.CTkButton(
            btn_frame,
            text='🔄 Yenile',
            command=self.load_courses,
            width=100
        )
        self.btn_refresh.pack(side='left', padx=5)

    def create_content(self):
        """İçerik alanı - liste ve detay panelleri"""
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky='nsew', padx=20, pady=(0, 20))
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=2)

        self.create_list_panel(content_frame)
        self.create_detail_panel(content_frame)

    def create_list_panel(self, parent):
        """Sol panel: Ders listesi ve arama"""
        list_frame = ctk.CTkFrame(parent)
        list_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Arama çubuğu
        search_frame = ctk.CTkFrame(list_frame, fg_color='transparent')
        search_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text='🔍 Ders ara...',
            height=35
        )
        self.search_entry.grid(row=0, column=0, sticky='ew')
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_courses())

        # Treeview renk ayarları
        is_dark = config.THEME_MODE == 'dark'
        bg = '#2b2b2b' if is_dark else '#f0f0f0'
        fg = '#ffffff' if is_dark else '#111111'
        sel_bg = '#1f6aa5'
        head_bg = '#1a1a1a' if is_dark else '#dcdcdc'
        head_fg = '#ffffff' if is_dark else '#111111'
        row_alt = '#333333' if is_dark else '#e8e8e8'

        # Treeview stili
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            'Courses.Treeview',
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            borderwidth=0,
            rowheight=42,
            font=('Segoe UI', 10)
        )
        style.configure(
            'Courses.Treeview.Heading',
            background=head_bg,
            foreground=head_fg,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            padding=(6, 6)
        )
        style.map('Courses.Treeview',
                  background=[('selected', sel_bg)],
                  foreground=[('selected', 'white')])
        style.map('Courses.Treeview.Heading',
                  background=[('active', '#2a5a8a')])

        # Treeview
        columns = ('kod', 'ad', 'bolum', 'ogretim_gorevlisi')
        self.courses_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            style='Courses.Treeview',
            selectmode='browse'
        )

        # Başlıklar
        self.courses_tree.heading('kod', text='Ders Kodu', anchor='w',
                                  command=lambda: self._sort_tree('kod'))
        self.courses_tree.heading('ad', text='Ders Adı', anchor='w',
                                  command=lambda: self._sort_tree('ad'))
        self.courses_tree.heading('bolum', text='Bölüm', anchor='w',
                                  command=lambda: self._sort_tree('bolum'))
        self.courses_tree.heading('ogretim_gorevlisi', text='Öğretim Görevlisi', anchor='w',
                                  command=lambda: self._sort_tree('ogretim_gorevlisi'))

        # Kolon genişlikleri
        self.courses_tree.column('kod', width=90, minwidth=70, stretch=False)
        self.courses_tree.column('ad', width=150, minwidth=100, stretch=True)
        self.courses_tree.column('bolum', width=110, minwidth=80, stretch=True)
        self.courses_tree.column('ogretim_gorevlisi', width=120, minwidth=90, stretch=True)

        # Satır renkleri
        self.courses_tree.tag_configure('odd', background=bg)
        self.courses_tree.tag_configure('even', background=row_alt)

        # Scroll
        tree_scroll = ctk.CTkScrollbar(list_frame, command=self.courses_tree.yview)
        self.courses_tree.configure(yscrollcommand=tree_scroll.set)

        self.courses_tree.grid(row=1, column=0, sticky='nsew', padx=(10, 0), pady=(0, 10))
        tree_scroll.grid(row=1, column=1, sticky='ns', pady=(0, 10), padx=(0, 8))

        self.courses_tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        self._sort_col = None
        self._sort_rev = False

    def create_detail_panel(self, parent):
        """Sağ panel: Ders detayları ve form"""
        self.detail_frame = ctk.CTkFrame(parent)
        self.detail_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        self.detail_frame.grid_columnconfigure(0, weight=1)

        detail_title = ctk.CTkLabel(
            self.detail_frame,
            text='Ders Bilgileri',
            font=config.FONTS['heading']
        )
        detail_title.grid(row=0, column=0, pady=20, padx=20, sticky='w')

        # Form alanı
        form_frame = ctk.CTkFrame(self.detail_frame, fg_color='transparent')
        form_frame.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 20))
        form_frame.grid_columnconfigure(1, weight=1)

        # Ders Kodu
        ctk.CTkLabel(form_frame, text='Ders Kodu:*', anchor='w').grid(
            row=0, column=0, sticky='w', pady=10, padx=(0, 10))
        self.code_entry = ctk.CTkEntry(form_frame, placeholder_text='örn: MAT101')
        self.code_entry.grid(row=0, column=1, sticky='ew', pady=10)

        # Ders Adı
        ctk.CTkLabel(form_frame, text='Ders Adı:*', anchor='w').grid(
            row=1, column=0, sticky='w', pady=10, padx=(0, 10))
        self.name_entry = ctk.CTkEntry(form_frame, placeholder_text='örn: Matematik I')
        self.name_entry.grid(row=1, column=1, sticky='ew', pady=10)

        # Bölüm
        ctk.CTkLabel(form_frame, text='Bölüm:', anchor='w').grid(
            row=2, column=0, sticky='w', pady=10, padx=(0, 10))
        self.department_entry = ctk.CTkEntry(
            form_frame, placeholder_text='örn: Mühendislik Fakültesi')
        self.department_entry.grid(row=2, column=1, sticky='ew', pady=10)

        # Öğretim Görevlisi
        ctk.CTkLabel(form_frame, text='Öğretim Görevlisi:', anchor='w').grid(
            row=3, column=0, sticky='w', pady=10, padx=(0, 10))
        self.instructor_entry = ctk.CTkEntry(
            form_frame, placeholder_text='örn: Prof. Dr. ...')
        self.instructor_entry.grid(row=3, column=1, sticky='ew', pady=10)

        # Aktif checkbox
        self.is_active_var = ctk.BooleanVar(value=True)
        self.is_active_check = ctk.CTkCheckBox(
            form_frame, text='Aktif', variable=self.is_active_var)
        self.is_active_check.grid(row=4, column=1, sticky='w', pady=10)

        # Butonlar
        btn_frame = ctk.CTkFrame(self.detail_frame, fg_color='transparent')
        btn_frame.grid(row=2, column=0, sticky='ew', padx=20, pady=(0, 20))

        self.btn_save = ctk.CTkButton(
            btn_frame, text='💾 Kaydet', command=self.save_course, height=40)
        self.btn_save.pack(side='left', padx=5, fill='x', expand=True)

        self.btn_delete = ctk.CTkButton(
            btn_frame, text='🗑️ Sil', command=self.delete_course, height=40,
            fg_color='#d32f2f', hover_color='#b71c1c')
        self.btn_delete.pack(side='left', padx=5, fill='x', expand=True)

        self.btn_clear = ctk.CTkButton(
            btn_frame, text='🔄 Temizle', command=self.clear_form, height=40,
            fg_color='gray', hover_color='darkgray')
        self.btn_clear.pack(side='left', padx=5, fill='x', expand=True)

        # İstatistikler
        stats_frame = ctk.CTkFrame(self.detail_frame)
        stats_frame.grid(row=3, column=0, sticky='ew', padx=20, pady=(0, 20))
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            stats_frame,
            text='📊 İstatistikler',
            font=config.FONTS['subheading']
        ).grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky='w')

        self.stat_questions = ctk.CTkLabel(stats_frame, text='Soru Sayısı: -')
        self.stat_questions.grid(row=1, column=0, pady=5, padx=10, sticky='w')

        self.stat_exams = ctk.CTkLabel(stats_frame, text='Sınav Sayısı: -')
        self.stat_exams.grid(row=1, column=1, pady=5, padx=10, sticky='w')

    def load_courses(self):
        """Dersleri veritabanından yükle"""
        try:
            with db_manager.session_scope() as session:
                course_objs = (
                    session.query(Course)
                    .filter_by(is_active=True)
                    .order_by(Course.code)
                    .all()
                )
                self.courses = []
                for c in course_objs:
                    self.courses.append(SimpleNamespace(
                        id=c.id,
                        code=c.code,
                        name=c.name,
                        department=c.department,
                        instructor=c.instructor,
                        created_at=c.created_at,
                        updated_at=c.updated_at,
                        is_active=c.is_active
                    ))
        except Exception as e:
            logger.error(f'Ders yükleme hatası: {e}')
            messagebox.showerror('Hata', f'Dersler yüklenirken hata oluştu:\n{str(e)}')
            return

        self.display_courses()

        if self.status_callback:
            self.status_callback(f'{len(self.courses)} ders yüklendi')
        logger.info(f'{len(self.courses)} ders yüklendi')

    def display_courses(self, courses=None):
        """Dersleri Treeview'da göster"""
        courses_to_display = courses if courses is not None else self.courses
        self.filtered_courses = list(courses_to_display)

        # Treeview temizle
        self.courses_tree.delete(*self.courses_tree.get_children())

        for idx, course in enumerate(self.filtered_courses):
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.courses_tree.insert(
                '', 'end',
                iid=str(course.id),
                values=(
                    course.code or '',
                    course.name or '',
                    course.department or '',
                    course.instructor or ''
                ),
                tags=(tag,)
            )

    def _on_tree_select(self, event=None):
        """Treeview seçim olayı"""
        selection = self.courses_tree.selection()
        if not selection:
            return
        try:
            course_id = int(selection[0])
            course = next(
                (c for c in self.filtered_courses if c.id == course_id),
                None
            )
            if course:
                self.edit_course(course)
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
            'kod': 'code',
            'ad': 'name',
            'bolum': 'department',
            'ogretim_gorevlisi': 'instructor'
        }
        attr = col_map.get(col)
        if attr:
            self.filtered_courses.sort(
                key=lambda c: (getattr(c, attr) or '').lower(),
                reverse=self._sort_rev
            )
        self.display_courses(self.filtered_courses)

    def filter_courses(self):
        """Arama metnine göre filtrele"""
        search_text = self.search_entry.get().lower()
        if not search_text:
            self.display_courses()
            return

        filtered = [
            c for c in self.courses
            if search_text in (c.code or '').lower()
            or search_text in (c.name or '').lower()
            or (c.instructor and search_text in c.instructor.lower())
            or (c.department and search_text in c.department.lower())
        ]
        self.display_courses(filtered)

    def new_course(self):
        """Yeni ders formu"""
        self.clear_form()
        self.code_entry.focus()

    def edit_course(self, course):
        """Mevcut dersi düzenle"""
        self.selected_course = course

        self.code_entry.delete(0, 'end')
        self.code_entry.insert(0, course.code)

        self.name_entry.delete(0, 'end')
        self.name_entry.insert(0, course.name)

        self.department_entry.delete(0, 'end')
        if course.department:
            self.department_entry.insert(0, course.department)

        self.instructor_entry.delete(0, 'end')
        if course.instructor:
            self.instructor_entry.insert(0, course.instructor)

        self.is_active_var.set(course.is_active)
        self.update_statistics(course)

    def save_course(self):
        """Ders kaydet (yeni veya güncelle)"""
        code = self.code_entry.get().strip().upper()
        name = self.name_entry.get().strip()

        if not code:
            messagebox.showwarning('Uyarı', 'Ders kodu boş olamaz!')
            self.code_entry.focus()
            return

        if not name:
            messagebox.showwarning('Uyarı', 'Ders adı boş olamaz!')
            self.name_entry.focus()
            return

        try:
            with db_manager.session_scope() as session:
                if self.selected_course:
                    # Güncelle
                    course = (
                        session.query(Course)
                        .filter_by(id=self.selected_course.id)
                        .first()
                    )
                    if not course:
                        raise Exception('Ders bulunamadı!')

                    # Kod değişti mi - çakışma kontrolü
                    if course.code != code:
                        existing = session.query(Course).filter_by(code=code).first()
                        if existing:
                            messagebox.showwarning(
                                'Uyarı', f"'{code}' kodlu ders zaten mevcut!")
                            return

                    course.code = code
                    course.name = name
                    course.department = self.department_entry.get().strip()
                    course.instructor = self.instructor_entry.get().strip()
                    course.is_active = self.is_active_var.get()
                    msg = f"'{name}' dersi güncellendi"
                else:
                    # Yeni ders - çakışma kontrolü
                    existing = session.query(Course).filter_by(code=code).first()
                    if existing:
                        messagebox.showwarning(
                            'Uyarı', f"'{code}' kodlu ders zaten mevcut!")
                        return

                    new_course = Course(
                        code=code,
                        name=name,
                        department=self.department_entry.get().strip(),
                        instructor=self.instructor_entry.get().strip(),
                        is_active=self.is_active_var.get()
                    )
                    session.add(new_course)
                    msg = f"'{name}' dersi eklendi"

            self.load_courses()
            self.clear_form()

            if self.status_callback:
                self.status_callback(msg)
            messagebox.showinfo('Başarı', msg)

        except Exception as e:
            logger.error(f'Ders kaydetme hatası: {e}')
            messagebox.showerror('Hata', f'Ders kaydedilirken hata oluştu:\n{str(e)}')

    def delete_course(self):
        """Seçili dersi sil"""
        if not self.selected_course:
            messagebox.showwarning('Uyarı', 'Lütfen bir ders seçin!')
            return

        if not messagebox.askyesno(
                'Onay',
                f"'{self.selected_course.name}' dersini silmek istediğinizden emin misiniz?\n"
                f"Bu işlem dersi ve ilişkili tüm sorular ile sınavları etkileyebilir!"):
            return

        try:
            with db_manager.session_scope() as session:
                course = session.query(Course).filter_by(
                    id=self.selected_course.id).first()
                if course:
                    course.is_active = False  # Soft delete
                    # İlişkili soruları da soft-delete yap
                    for q in course.questions:
                        q.is_active = False
                    msg = f"'{course.name}' dersi silindi"

            self.load_courses()
            self.clear_form()

            if self.status_callback:
                self.status_callback(msg)
            messagebox.showinfo('Başarı', msg)

        except Exception as e:
            logger.error(f'Ders silme hatası: {e}')
            messagebox.showerror('Hata', f'Ders silinirken hata oluştu:\n{str(e)}')

    def clear_form(self):
        """Formu temizle"""
        self.selected_course = None
        self.code_entry.delete(0, 'end')
        self.name_entry.delete(0, 'end')
        self.department_entry.delete(0, 'end')
        self.instructor_entry.delete(0, 'end')
        self.is_active_var.set(True)
        self.stat_questions.configure(text='Soru Sayısı: -')
        self.stat_exams.configure(text='Sınav Sayısı: -')

    def update_statistics(self, course):
        """Ders istatistiklerini güncelle"""
        try:
            with db_manager.session_scope() as session:
                from database import Question, Exam
                q_count = session.query(Question).filter_by(
                    course_id=course.id).count()
                e_count = session.query(Exam).filter_by(
                    course_id=course.id).count()
                self.stat_questions.configure(text=f'Soru Sayısı: {q_count}')
                self.stat_exams.configure(text=f'Sınav Sayısı: {e_count}')
        except Exception as e:
            logger.error(f'İstatistik güncelleme hatası: {e}')
            self.stat_questions.configure(text='Soru Sayısı: ?')
            self.stat_exams.configure(text='Sınav Sayısı: ?')
