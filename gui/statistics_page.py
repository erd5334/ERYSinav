"""
İstatistikler ve raporlama sayfası
"""
import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import tkinter as tk
import logging
from database import db_manager, Course, Question, Exam
from database.models import Student, StudentResult, ExamQuestion
from types import SimpleNamespace
import config

logger = logging.getLogger(__name__)


class StatisticsPage(ctk.CTkFrame):
    """İstatistik ve raporlama sayfası"""

    def __init__(self, parent, status_callback=None):
        super().__init__(parent)
        self.status_callback = status_callback
        self.exams_list = []

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_header()
        self.create_content()
        self.load_statistics()

    def create_header(self):
        """Sayfa başlığı"""
        header_frame = ctk.CTkFrame(self, fg_color='transparent')
        header_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=20)
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text='📊 İstatistikler & Ölçme Değerlendirme',
            font=config.FONTS['title']
        )
        title.grid(row=0, column=0, sticky='w')

        self.btn_refresh = ctk.CTkButton(
            header_frame,
            text='🔄 Yenile',
            command=self.load_statistics,
            width=100
        )
        self.btn_refresh.grid(row=0, column=1, sticky='e')

    def create_content(self):
        """İki sekme: Genel İstatistikler ve Sınav Analizi"""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky='nsew', padx=20, pady=(0, 20))

        self.tab_general = self.tabview.add('📊 Sistem İstatistikleri')
        self.tab_exam = self.tabview.add('✍️ Sınav Başarı Analizi')

        # Genel tab - scrollable
        self.general_scroll = ctk.CTkScrollableFrame(self.tab_general)
        self.general_scroll.pack(fill='both', expand=True)
        self.general_scroll.grid_columnconfigure((0, 1, 2), weight=1)

        self.create_general_stats(self.general_scroll)
        self.create_course_stats(self.general_scroll)
        self.create_question_stats(self.general_scroll)
        self.create_exam_stats(self.general_scroll)

        # Sınav analizi tab
        self.create_exam_analysis_tab(self.tab_exam)

    def create_general_stats(self, parent):
        """Genel istatistik kartları"""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=10, pady=10)
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            frame, text='Genel İstatistikler', font=config.FONTS['heading']
        ).grid(row=0, column=0, columnspan=4, pady=10, padx=10, sticky='w')

        self.total_courses_card = self.create_stat_card(frame, 1, 0, '📚 Toplam Ders', '0')
        self.total_questions_card = self.create_stat_card(
            frame, 1, 1, '📝 Toplam Soru', '0')
        self.total_exams_card = self.create_stat_card(frame, 1, 2, '📄 Toplam Sınav', '0')
        self.db_size_card = self.create_stat_card(frame, 1, 3, '💾 Veritabanı', '0 MB')

    def create_course_stats(self, parent):
        """Ders bazlı istatistikler"""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text='Ders Bazlı İstatistikler', font=config.FONTS['heading']
        ).grid(row=0, column=0, pady=10, padx=10, sticky='w')

        headers_frame = ctk.CTkFrame(frame, fg_color='transparent')
        headers_frame.grid(row=1, column=0, sticky='ew', padx=10)
        headers_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        headers = ['Ders Kodu', 'Ders Adı', 'Soru Sayısı', 'Sınav Sayısı']
        for col, header in enumerate(headers):
            ctk.CTkLabel(
                headers_frame, text=header, font=config.FONTS['subheading']
            ).grid(row=0, column=col, padx=5, pady=5, sticky='w')

        self.course_stats_frame = ctk.CTkFrame(frame, fg_color='transparent')
        self.course_stats_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 10))
        self.course_stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def create_question_stats(self, parent):
        """Soru istatistikleri"""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=10, pady=10)
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            frame, text='Soru İstatistikleri', font=config.FONTS['heading']
        ).grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky='w')

        self.easy_count_card = self.create_stat_card(frame, 1, 0, '😊 Kolay', '0')
        self.medium_count_card = self.create_stat_card(frame, 1, 1, '😐 Orta', '0')
        self.hard_count_card = self.create_stat_card(frame, 1, 2, '😓 Zor', '0')
        self.with_image_card = self.create_stat_card(frame, 2, 0, '🖼️ Görselli', '0')
        self.without_image_card = self.create_stat_card(
            frame, 2, 1, '📄 Görselsiz', '0')
        self.most_used_card = self.create_stat_card(
            frame, 2, 2, '⭐ En Çok Kullanılan', '-')

    def create_exam_stats(self, parent):
        """Sınav istatistikleri"""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=10, pady=10)
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            frame, text='Sınav İstatistikleri', font=config.FONTS['heading']
        ).grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky='w')

        self.vize_count_card = self.create_stat_card(frame, 1, 0, '📝 Vize', '0')
        self.final_count_card = self.create_stat_card(frame, 1, 1, '📋 Final', '0')
        self.quiz_count_card = self.create_stat_card(frame, 1, 2, '✅ Quiz', '0')

    def create_stat_card(self, parent, row, col, label, value):
        """İstatistik kartı oluştur - değer label döndürür"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')

        ctk.CTkLabel(card, text=label, font=config.FONTS.get('small', ('Segoe UI', 10))
                     ).pack(pady=(12, 2), padx=12)

        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=config.FONTS.get('heading', ('Segoe UI', 20, 'bold'))
        )
        value_label.pack(pady=(2, 12), padx=12)

        return value_label

    def create_exam_analysis_tab(self, parent):
        """Sınav başarı analizi sekmesi"""
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        # Sol panel: Sınav seçimi
        left_frame = ctk.CTkFrame(parent)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(10, 5), pady=10,
                        rowspan=2)
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_frame, text='Sınav Seç', font=config.FONTS['subheading']
        ).grid(row=0, column=0, pady=10, padx=10, sticky='w')

        self.exam_combo = ctk.CTkComboBox(
            left_frame,
            values=['Sınav seçin...'],
            command=self.on_exam_change
        )
        self.exam_combo.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))

        # Sınav listesi
        is_dark = config.THEME_MODE == 'dark'
        bg = '#2b2b2b' if is_dark else '#f0f0f0'
        fg = '#ffffff' if is_dark else '#111111'

        style = ttk.Style()
        style.theme_use('default')
        style.configure('Stats.Treeview', background=bg, foreground=fg,
                        fieldbackground=bg, borderwidth=0, rowheight=36)
        style.configure('Stats.Treeview.Heading',
                        background='#1a1a1a' if is_dark else '#dcdcdc',
                        foreground=fg, font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Stats.Treeview', background=[('selected', '#1f6aa5')],
                  foreground=[('selected', 'white')])

        cols = ('no', 'ad', 'puan', 'durum')
        self.students_tree = ttk.Treeview(
            left_frame, columns=cols, show='headings',
            style='Stats.Treeview', selectmode='browse'
        )
        self.students_tree.heading('no', text='Öğrenci No')
        self.students_tree.heading('ad', text='Ad Soyad')
        self.students_tree.heading('puan', text='Puan')
        self.students_tree.heading('durum', text='Durum')
        self.students_tree.column('no', width=90)
        self.students_tree.column('ad', width=120)
        self.students_tree.column('puan', width=60)
        self.students_tree.column('durum', width=70)

        tree_scroll = ctk.CTkScrollbar(left_frame, command=self.students_tree.yview)
        self.students_tree.configure(yscrollcommand=tree_scroll.set)

        self.students_tree.grid(row=2, column=0, sticky='nsew', padx=(10, 0),
                                pady=(0, 10))
        tree_scroll.grid(row=2, column=1, sticky='ns', pady=(0, 10), padx=(0, 5))

        # Sağ panel: Analiz sonuçları
        self.right_frame = ctk.CTkFrame(parent)
        self.right_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 10), pady=10)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.lbl_analysis_title = ctk.CTkLabel(
            self.right_frame, text='Sınav Analizi', font=config.FONTS['subheading'])
        self.lbl_analysis_title.grid(row=0, column=0, pady=10, padx=10, sticky='w')

        # Özet kartlar
        summary_frame = ctk.CTkFrame(self.right_frame, fg_color='transparent')
        summary_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))
        summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.lbl_student_count = self.create_summary_label(
            summary_frame, 0, 0, '👥 Öğrenci', '0')
        self.lbl_class_avg = self.create_summary_label(
            summary_frame, 0, 1, '📊 Sınıf Ort.', '-')
        self.lbl_highest = self.create_summary_label(
            summary_frame, 0, 2, '⬆️ En Yüksek', '-')
        self.lbl_lowest = self.create_summary_label(
            summary_frame, 1, 0, '⬇️ En Düşük', '-')

        # Soru analizi
        ctk.CTkLabel(
            self.right_frame, text='Soru Analizi', font=config.FONTS.get('subheading')
        ).grid(row=2, column=0, pady=(15, 5), padx=10, sticky='w')

        self.questions_analysis_frame = ctk.CTkScrollableFrame(
            self.right_frame, height=200)
        self.questions_analysis_frame.grid(
            row=3, column=0, sticky='nsew', padx=10, pady=(0, 10))
        self.questions_analysis_frame.grid_columnconfigure(0, weight=1)

        self.analysis_content = ctk.CTkLabel(
            self.questions_analysis_frame,
            text='Analiz için sınav seçin',
            text_color='gray'
        )
        self.analysis_content.pack(pady=20)

    def create_summary_label(self, parent, row, col, label, value):
        """Özet etiketi oluştur"""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')

        ctk.CTkLabel(frame, text=label,
                     font=config.FONTS.get('small', ('Segoe UI', 9))).pack(
            pady=(8, 2), padx=8)
        val_lbl = ctk.CTkLabel(
            frame, text=value,
            font=config.FONTS.get('subheading', ('Segoe UI', 14, 'bold')))
        val_lbl.pack(pady=(2, 8), padx=8)
        return val_lbl

    def load_statistics(self):
        """Tüm istatistikleri yükle"""
        try:
            with db_manager.session_scope() as session:
                # Genel sayılar
                total_courses = session.query(Course).filter_by(is_active=True).count()
                total_questions = session.query(Question).filter_by(is_active=True).count()
                total_exams = session.query(Exam).count()

                self.total_courses_card.configure(text=str(total_courses))
                self.total_questions_card.configure(text=str(total_questions))
                self.total_exams_card.configure(text=str(total_exams))

                # Veritabanı boyutu
                try:
                    import os
                    db_path = db_manager.db_path
                    if hasattr(db_path, '__str__'):
                        size_bytes = os.path.getsize(str(db_path))
                        size_mb = size_bytes / (1024 * 1024)
                        self.db_size_card.configure(text=f'{size_mb:.1f} MB')
                except Exception:
                    self.db_size_card.configure(text='? MB')

                # Soru istatistikleri - zorluk
                try:
                    easy = session.query(Question).filter(
                        Question.difficulty == 'easy',
                        Question.is_active == True
                    ).count()
                    medium = session.query(Question).filter(
                        Question.difficulty == 'medium',
                        Question.is_active == True
                    ).count()
                    hard = session.query(Question).filter(
                        Question.difficulty == 'hard',
                        Question.is_active == True
                    ).count()
                    with_img = session.query(Question).filter(
                        Question.image_path.isnot(None),
                        Question.is_active == True
                    ).count()
                    without_img = total_questions - with_img

                    self.easy_count_card.configure(text=str(easy))
                    self.medium_count_card.configure(text=str(medium))
                    self.hard_count_card.configure(text=str(hard))
                    self.with_image_card.configure(text=str(with_img))
                    self.without_image_card.configure(text=str(without_img))
                except Exception as e:
                    logger.warning(f'Soru zorluk istatistikleri yüklenemedi: {e}')

                # Sınav türleri
                try:
                    vize = session.query(Exam).filter(
                        Exam.exam_type.in_(['Vize', 'Ara Sınav'])
                    ).count()
                    final = session.query(Exam).filter(
                        Exam.exam_type.in_(['Final', 'Final Sınavı'])
                    ).count()
                    quiz = session.query(Exam).filter(
                        Exam.exam_type.in_(['Quiz', 'Kısa Sınav'])
                    ).count()

                    self.vize_count_card.configure(text=str(vize))
                    self.final_count_card.configure(text=str(final))
                    self.quiz_count_card.configure(text=str(quiz))
                except Exception as e:
                    logger.warning(f'Sınav türü istatistikleri yüklenemedi: {e}')

                # Ders bazlı
                self._load_course_stats(session)

                # Sınav listesi
                self._load_exam_combo(session)

            if self.status_callback:
                self.status_callback('İstatistikler güncellendi')
            logger.info('İstatistikler yüklendi')

        except Exception as e:
            logger.error(f'İstatistik yükleme hatası: {e}')
            messagebox.showerror('Hata', f'İstatistikler yüklenirken hata oluştu:\n{e}')

    def _load_course_stats(self, session):
        """Ders bazlı istatistikleri yükle"""
        # Mevcut satırları temizle
        for widget in self.course_stats_frame.winfo_children():
            widget.destroy()

        try:
            courses = session.query(Course).filter_by(is_active=True).all()
            for row_idx, course in enumerate(courses):
                q_count = session.query(Question).filter_by(
                    course_id=course.id, is_active=True).count()
                e_count = session.query(Exam).filter_by(course_id=course.id).count()

                is_alt = row_idx % 2 == 0
                row_bg = 'transparent'

                data = [course.code, course.name, str(q_count), str(e_count)]
                for col_idx, text in enumerate(data):
                    ctk.CTkLabel(
                        self.course_stats_frame, text=text
                    ).grid(row=row_idx, column=col_idx, padx=5, pady=3, sticky='w')
        except Exception as e:
            logger.error(f'Ders istatistikleri yüklenemedi: {e}')

    def _load_exam_combo(self, session):
        """Sınav analizi için combo box doldur"""
        try:
            exams = session.query(Exam).order_by(Exam.created_at.desc()).all()
            self.exams_list = []
            exam_names = []
            for exam in exams:
                self.exams_list.append(SimpleNamespace(
                    id=exam.id,
                    name=exam.exam_name,
                    course_id=exam.course_id
                ))
                exam_names.append(exam.exam_name)

            if exam_names:
                self.exam_combo.configure(values=exam_names)
                self.exam_combo.set(exam_names[0])
            else:
                self.exam_combo.configure(values=['Sınav bulunamadı'])
                self.exam_combo.set('Sınav bulunamadı')
        except Exception as e:
            logger.error(f'Sınav listesi yüklenemedi: {e}')

    def on_exam_change(self, value=None):
        """Sınav değiştiğinde analizi güncelle"""
        selected = self.exam_combo.get()
        exam = next((e for e in self.exams_list if e.name == selected), None)
        if exam:
            self.load_exam_analysis(exam.id)

    def load_exam_analysis(self, exam_id):
        """Seçili sınavın analizini yükle"""
        try:
            with db_manager.session_scope() as session:
                # Öğrenci sonuçlarını temizle
                self.students_tree.delete(*self.students_tree.get_children())

                try:
                    results = session.query(StudentResult).filter_by(
                        exam_id=exam_id).all()
                    scores = []
                    for idx, result in enumerate(results):
                        try:
                            student = session.query(Student).filter_by(
                                id=result.student_id).first()
                            student_no = student.student_no if student else '-'
                            student_name = student.full_name if student else '-'
                        except Exception:
                            student_no = '-'
                            student_name = '-'

                        score = result.score if hasattr(result, 'score') else 0
                        scores.append(score)
                        status = 'Geçti' if score >= 50 else 'Kaldı'
                        tag = 'pass' if score >= 50 else 'fail'

                        self.students_tree.insert(
                            '', 'end',
                            values=(student_no, student_name, f'{score:.1f}', status),
                            tags=(tag,)
                        )

                    self.students_tree.tag_configure('pass', foreground='#4caf50')
                    self.students_tree.tag_configure('fail', foreground='#f44336')

                    # Özet istatistikler
                    if scores:
                        avg = sum(scores) / len(scores)
                        highest = max(scores)
                        lowest = min(scores)
                        self.lbl_student_count.configure(text=str(len(scores)))
                        self.lbl_class_avg.configure(text=f'{avg:.1f}')
                        self.lbl_highest.configure(text=f'{highest:.1f}')
                        self.lbl_lowest.configure(text=f'{lowest:.1f}')
                    else:
                        self.lbl_student_count.configure(text='0')
                        self.lbl_class_avg.configure(text='-')
                        self.lbl_highest.configure(text='-')
                        self.lbl_lowest.configure(text='-')

                except Exception as e:
                    logger.warning(f'Öğrenci sonuçları yüklenemedi: {e}')
                    self.analysis_content.configure(
                        text='Öğrenci sonuç verisi bulunamadı')

        except Exception as e:
            logger.error(f'Sınav analizi yükleme hatası: {e}')
