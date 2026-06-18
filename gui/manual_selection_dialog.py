"""
Soru bankasından el ile tek tek soru seçerek sınav oluşturmak için kullanılan diyalog penceresi.
"""
import customtkinter as ctk
from tkinter import messagebox
from database import db_manager
from database.models import Question
import config
from pathlib import Path

class ManualSelectionDialog(ctk.CTkToplevel):
    """Soru Bankasından El İle Soru Seçme Diyaloğu"""
    
    def __init__(self, parent, course_id, allowed_types, selected_question_ids=None):
        super().__init__(parent)
        
        self.parent = parent
        self.course_id = course_id
        self.allowed_types = allowed_types
        self.selected_ids = set(selected_question_ids or [])
        
        self.title("Manuel Soru Seçimi")
        self.transient(parent)
        self.grab_set()
        
        width = 1100
        height = 780
        self.geometry(f"{width}x{height}")
        self.minsize(950, 600)
        
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"+{x}+{y}")
        
        self.result = None  # Geriye dönen seçilmiş soru listesi
        self.all_questions = []
        self.question_widgets = []
        
        self.load_questions_from_db()
        self.create_layout()
        self.apply_filters()
        
        self.protocol('WM_DELETE_WINDOW', self.on_cancel)
        self.wait_window(self)

    def load_questions_from_db(self):
        """Derse ait soruları veritabanından çek"""
        try:
            with db_manager.session_scope() as session:
                q_objs = session.query(Question).filter(
                    Question.course_id == self.course_id,
                    Question.is_active == True,
                    Question.question_type.in_(self.allowed_types)
                ).order_by(Question.id).all()
                
                # SQLAlchemy nesnelerini oturum dışında kullanabilmek için sözlüğe çevir
                self.all_questions = []
                for q in q_objs:
                    self.all_questions.append({
                        'id': q.id,
                        'question_text': q.question_text or '',
                        'question_type': q.question_type or 'Genel',
                        'difficulty': q.difficulty or 'Orta',
                        'topic': q.topic or '',
                        'tags': q.tags or '',
                        'correct_answer': q.correct_answer or 'A',
                        'option_a': q.option_a or '',
                        'option_b': q.option_b or '',
                        'option_c': q.option_c or '',
                        'option_d': q.option_d or '',
                        'option_e': q.option_e or '',
                        'question_image_path': q.question_image_path or q.image_path or None,
                        'option_a_image_path': q.option_a_image_path or None,
                        'option_b_image_path': q.option_b_image_path or None,
                        'option_c_image_path': q.option_c_image_path or None,
                        'option_d_image_path': q.option_d_image_path or None,
                        'option_e_image_path': q.option_e_image_path or None,
                    })
        except Exception as e:
            messagebox.showerror("Hata", f"Sorular veritabanından yüklenirken hata oluştu:\n{e}")
            self.all_questions = []

    def create_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # ÜST FİLTRELEME ALANI
        filter_frame = ctk.CTkFrame(self, corner_radius=10)
        filter_frame.grid(row=0, column=0, sticky='ew', padx=15, pady=(15, 10))
        
        # Arama
        lbl_search = ctk.CTkLabel(filter_frame, text="🔍 Ara:", font=config.FONTS['body'])
        lbl_search.grid(row=0, column=0, padx=(15, 5), pady=12, sticky='w')
        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="Soru metninde ara...", width=220)
        self.search_entry.grid(row=0, column=1, padx=5, pady=12, sticky='w')
        self.search_entry.bind('<KeyRelease>', lambda e: self.apply_filters())
        
        # Zorluk
        lbl_diff = ctk.CTkLabel(filter_frame, text="Zorluk:", font=config.FONTS['body'])
        lbl_diff.grid(row=0, column=2, padx=(15, 5), pady=12, sticky='w')
        self.diff_combo = ctk.CTkComboBox(filter_frame, values=["Tümü", "Kolay", "Orta", "Zor"], width=110, command=lambda v: self.apply_filters())
        self.diff_combo.grid(row=0, column=3, padx=5, pady=12, sticky='w')
        self.diff_combo.set("Tümü")
        
        # Tür
        lbl_type = ctk.CTkLabel(filter_frame, text="Tür:", font=config.FONTS['body'])
        lbl_type.grid(row=0, column=4, padx=(15, 5), pady=12, sticky='w')
        self.type_combo = ctk.CTkComboBox(filter_frame, values=["Tümü"] + list(self.allowed_types), width=110, command=lambda v: self.apply_filters())
        self.type_combo.grid(row=0, column=5, padx=5, pady=12, sticky='w')
        self.type_combo.set("Tümü")
        
        # Konu / Etiket
        lbl_topic = ctk.CTkLabel(filter_frame, text="Konu/Etiket:", font=config.FONTS['body'])
        lbl_topic.grid(row=0, column=6, padx=(15, 5), pady=12, sticky='w')
        self.topic_entry = ctk.CTkEntry(filter_frame, placeholder_text="Konu veya etiket...", width=160)
        self.topic_entry.grid(row=0, column=7, padx=5, pady=12, sticky='w')
        self.topic_entry.bind('<KeyRelease>', lambda e: self.apply_filters())
        
        # Temizle Butonu
        btn_clear_filters = ctk.CTkButton(
            filter_frame,
            text="🧹 Temizle",
            command=self.clear_filters,
            width=90,
            fg_color="gray",
            hover_color="darkgray"
        )
        btn_clear_filters.grid(row=0, column=8, padx=(15, 15), pady=12, sticky='e')
        
        # SORU LİSTELEME ALANI
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Ders Soru Bankası (İstediğiniz soruları seçin)")
        self.scroll_frame.grid(row=1, column=0, sticky='nsew', padx=15, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # ALT DURUM & EYLEM ALANI
        bottom_frame = ctk.CTkFrame(self, height=60, fg_color='transparent')
        bottom_frame.grid(row=2, column=0, sticky='ew', padx=15, pady=15)
        
        self.var_select_all = ctk.BooleanVar(value=False)
        self.chk_all = ctk.CTkCheckBox(
            bottom_frame,
            text='Görüntülenen Tümünü Seç / Kaldır',
            variable=self.var_select_all,
            command=self.toggle_all_visible,
            font=config.FONTS['body']
        )
        self.chk_all.pack(side='left', padx=10)
        
        self.lbl_selected_count = ctk.CTkLabel(
            bottom_frame,
            text="Seçilen Soru: 0",
            font=config.FONTS['subheading'],
            text_color=config.COLORS['primary']
        )
        self.lbl_selected_count.pack(side='left', padx=25)
        
        self.btn_cancel = ctk.CTkButton(
            bottom_frame,
            text='❌ İptal',
            command=self.on_cancel,
            fg_color='gray',
            hover_color='darkgray',
            width=120,
            height=38
        )
        self.btn_cancel.pack(side='right', padx=5)
        
        self.btn_confirm = ctk.CTkButton(
            bottom_frame,
            text='📥 Soruları Sınava Ekle',
            command=self.on_confirm,
            fg_color=config.COLORS['success'],
            hover_color='#218c5e',
            width=200,
            height=38
        )
        self.btn_confirm.pack(side='right', padx=5)

    def clear_filters(self):
        self.search_entry.delete(0, 'end')
        self.topic_entry.delete(0, 'end')
        self.diff_combo.set("Tümü")
        self.type_combo.set("Tümü")
        self.apply_filters()

    def apply_filters(self):
        """Filtrelere uyan soruları ekranda listele"""
        search_query = self.search_entry.get().strip().lower()
        diff_filter = self.diff_combo.get()
        type_filter = self.type_combo.get()
        topic_query = self.topic_entry.get().strip().lower()
        
        # Mevcut widgetları temizle
        for widget_dict in self.question_widgets:
            widget_dict['frame'].destroy()
        self.question_widgets.clear()
        
        visible_idx = 0
        for q in self.all_questions:
            # Arama filtresi
            if search_query and search_query not in q['question_text'].lower():
                continue
            # Zorluk filtresi
            if diff_filter != "Tümü" and q['difficulty'] != diff_filter:
                continue
            # Tür filtresi
            if type_filter != "Tümü" and q['question_type'] != type_filter:
                continue
            # Konu / Etiket filtresi
            if topic_query:
                combined_meta = f"{q['topic']} {q['tags']}".lower()
                if topic_query not in combined_meta:
                    continue
            
            # Bu soru filtrelere uyuyor, kart oluştur
            self.create_question_card(q, visible_idx)
            visible_idx += 1
            
        self.update_count_display()

    def create_question_card(self, q, idx):
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=8, border_width=1, border_color='#3e3e3e')
        card.grid(row=idx, column=0, sticky='ew', pady=6, padx=5)
        card.grid_columnconfigure(1, weight=1)
        
        # Sol taraf - Seçim Kutusu
        left_frame = ctk.CTkFrame(card, fg_color='transparent')
        left_frame.grid(row=0, column=0, sticky='ns', padx=10, pady=10)
        
        is_initially_selected = q['id'] in self.selected_ids
        var_select = ctk.BooleanVar(value=is_initially_selected)
        
        chk = ctk.CTkCheckBox(
            left_frame,
            text='',
            variable=var_select,
            width=20,
            command=lambda qid=q['id'], var=var_select: self.on_checkbox_toggle(qid, var)
        )
        chk.pack(pady=10)
        
        # Orta Kısım - Soru İçeriği
        mid_frame = ctk.CTkFrame(card, fg_color='transparent')
        mid_frame.grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        mid_frame.grid_columnconfigure(0, weight=1)
        
        # Row 0: Metadata Etiketleri
        meta_frame = ctk.CTkFrame(mid_frame, fg_color='transparent')
        meta_frame.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        
        # ID Etiketi
        lbl_id = ctk.CTkLabel(meta_frame, text=f"ID: #{q['id']}", font=config.FONTS['small'], text_color="gray")
        lbl_id.pack(side='left', padx=(0, 10))
        
        # Zorluk Rengi Belirleme
        diff_colors = {"Kolay": "#2fa572", "Orta": "#ed6c02", "Zor": "#d32f2f"}
        diff_color = diff_colors.get(q['difficulty'], "gray")
        
        lbl_diff_badge = ctk.CTkLabel(
            meta_frame,
            text=f" {q['difficulty']} ",
            font=config.FONTS['small'],
            fg_color=diff_color,
            text_color="white",
            corner_radius=4
        )
        lbl_diff_badge.pack(side='left', padx=5)
        
        # Tür Etiketi
        lbl_type_badge = ctk.CTkLabel(
            meta_frame,
            text=f" {q['question_type']} ",
            font=config.FONTS['small'],
            fg_color="#1f6aa5",
            text_color="white",
            corner_radius=4
        )
        lbl_type_badge.pack(side='left', padx=5)
        
        # Konu/Etiket
        meta_text = ""
        if q['topic']:
            meta_text += f"Konu: {q['topic']}"
        if q['tags']:
            sep = " | " if meta_text else ""
            meta_text += f"{sep}Etiketler: {q['tags']}"
        if meta_text:
            lbl_meta = ctk.CTkLabel(meta_frame, text=meta_text, font=config.FONTS['small'], text_color="#0288d1")
            lbl_meta.pack(side='left', padx=15)
            
        # Row 1: Soru Metni
        q_text_repr = q['question_text'] if q['question_text'] else "(Sadece Görsel İçermektedir)"
        lbl_text = ctk.CTkLabel(
            mid_frame,
            text=q_text_repr,
            font=config.FONTS['body'],
            justify='left',
            anchor='w',
            wraplength=720
        )
        lbl_text.grid(row=1, column=0, sticky='w', pady=(0, 6))
        
        # Soru Görseli Varsa Belirt
        if q['question_image_path']:
            lbl_q_img = ctk.CTkLabel(
                mid_frame,
                text=f"🖼️ Soru Görseli: {Path(q['question_image_path']).name}",
                font=config.FONTS['small'],
                text_color="#4caf50"
            )
            lbl_q_img.grid(row=2, column=0, sticky='w', pady=(0, 6))
            
        # Row 3: Şıklar
        opts_frame = ctk.CTkFrame(mid_frame, fg_color='transparent')
        opts_frame.grid(row=3, column=0, sticky='ew', pady=(4, 0))
        
        opts_present = []
        for ch in ('a', 'b', 'c', 'd', 'e'):
            val = q[f'option_{ch}']
            img = q[f'option_{ch}_image_path']
            if val or img:
                opt_str = f"{ch.upper()}) {val}"
                if img:
                    opt_str += f" 🖼️ [Görsel: {Path(img).name}]"
                
                # Doğru cevabı kalın/farklı renkte göster
                is_correct = ch.upper() == q['correct_answer'].upper()
                text_color = "#4caf50" if is_correct else None
                font_style = ('Segoe UI', 11, 'bold') if is_correct else ('Segoe UI', 11)
                
                lbl_opt = ctk.CTkLabel(
                    opts_frame,
                    text=opt_str,
                    font=font_style,
                    text_color=text_color,
                    justify='left',
                    anchor='w'
                )
                lbl_opt.pack(anchor='w', pady=1)
                
        self.question_widgets.append({
            'id': q['id'],
            'var_select': var_select,
            'frame': card
        })

    def on_checkbox_toggle(self, qid, var):
        if var.get():
            self.selected_ids.add(qid)
        else:
            self.selected_ids.discard(qid)
        self.update_count_display()

    def toggle_all_visible(self):
        val = self.var_select_all.get()
        for w in self.question_widgets:
            w['var_select'].set(val)
            if val:
                self.selected_ids.add(w['id'])
            else:
                self.selected_ids.discard(w['id'])
        self.update_count_display()

    def update_count_display(self):
        self.lbl_selected_count.configure(text=f"Seçilen Soru: {len(self.selected_ids)}")

    def on_confirm(self):
        if not self.selected_ids:
            messagebox.showwarning("Uyarı", "Lütfen en az bir soru seçin!")
            return
            
        self.result = list(self.selected_ids)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()
