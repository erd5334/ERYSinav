"""
PDF/Word belgelerinden ayrıştırılan soruları toplu olarak önizleme,
düzenleme ve ders/zorluk/konu belirleyerek veritabanına aktarma penceresi.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import config

class BulkPreviewDialog(ctk.CTkToplevel):
    """Toplu Soru Aktarma Önizleme Diyaloğu"""
    
    def __init__(self, parent, questions, courses, title="Toplu Soru Aktarma Önizleme"):
        super().__init__(parent)
        
        self.parent = parent
        self.parsed_questions = questions
        self.courses = courses
        self.title(title)
        
        self.transient(parent)
        self.grab_set()
        
        width = 1000
        height = 750
        self.geometry(f"{width}x{height}")
        self.minsize(900, 600)
        
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"+{x}+{y}")
        
        self.result = None
        self.question_widgets = []
        
        self.create_layout()
        self.load_questions()
        
        self.protocol('WM_DELETE_WINDOW', self.on_cancel)
        self.wait_window(self)

    def create_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        top_frame = ctk.CTkFrame(self, corner_radius=10)
        top_frame.grid(row=0, column=0, sticky='ew', padx=15, pady=(15, 10))
        top_frame.grid_columnconfigure(1, weight=1)
        top_frame.grid_columnconfigure(3, weight=1)
        
        lbl_course = ctk.CTkLabel(top_frame, text='Aktarılacak Ders:*', font=config.FONTS['body'])
        lbl_course.grid(row=0, column=0, padx=(15, 5), pady=12, sticky='w')
        
        course_names = [f"{c.code} - {c.name}" for c in self.courses]
        self.course_combo = ctk.CTkComboBox(top_frame, values=course_names, width=220)
        self.course_combo.grid(row=0, column=1, padx=(5, 15), pady=12, sticky='ew')
        if course_names:
            self.course_combo.set(course_names[0])
        else:
            self.course_combo.configure(values=['Ders bulunamadı!'])
            
        lbl_diff = ctk.CTkLabel(top_frame, text='Zorluk Seviyesi:', font=config.FONTS['body'])
        lbl_diff.grid(row=0, column=2, padx=(15, 5), pady=12, sticky='w')
        
        self.difficulty_combo = ctk.CTkComboBox(top_frame, values=['Kolay', 'Orta', 'Zor'], width=120)
        self.difficulty_combo.grid(row=0, column=3, padx=(5, 15), pady=12, sticky='w')
        self.difficulty_combo.set('Orta')
        
        lbl_topic = ctk.CTkLabel(top_frame, text='Konu:', font=config.FONTS['body'])
        lbl_topic.grid(row=1, column=0, padx=(15, 5), pady=(0, 12), sticky='w')
        
        self.topic_entry = ctk.CTkEntry(top_frame, placeholder_text='Örn: Limit ve Süreklilik')
        self.topic_entry.grid(row=1, column=1, padx=(5, 15), pady=(0, 12), sticky='ew')
        
        lbl_tags = ctk.CTkLabel(top_frame, text='Etiketler:', font=config.FONTS['body'])
        lbl_tags.grid(row=1, column=2, padx=(15, 5), pady=(0, 12), sticky='w')
        
        self.tags_entry = ctk.CTkEntry(top_frame, placeholder_text='Virgülle ayırın (Örn: vize, mat1)')
        self.tags_entry.grid(row=1, column=3, padx=(5, 15), pady=(0, 12), sticky='ew')
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text='Ayrıştırılan Sorular (Düzenleyebilirsiniz)')
        self.scroll_frame.grid(row=1, column=0, sticky='nsew', padx=15, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        bottom_frame = ctk.CTkFrame(self, height=60, fg_color='transparent')
        bottom_frame.grid(row=2, column=0, sticky='ew', padx=15, pady=15)
        
        self.var_select_all = ctk.BooleanVar(value=True)
        self.chk_all = ctk.CTkCheckBox(
            bottom_frame,
            text='Tümünü Seç / Kaldır',
            variable=self.var_select_all,
            command=self.toggle_all,
            font=config.FONTS['body']
        )
        self.chk_all.pack(side='left', padx=10)
        
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
            text='📥 İçe Aktar',
            command=self.on_confirm,
            fg_color=config.COLORS['success'],
            hover_color='#218c5e',
            width=180,
            height=38
        )
        self.btn_confirm.pack(side='right', padx=5)

    def load_questions(self):
        for idx, q in enumerate(self.parsed_questions):
            card = ctk.CTkFrame(
                self.scroll_frame,
                corner_radius=8,
                border_width=1,
                border_color='#3e3e3e'
            )
            card.grid(row=idx, column=0, sticky='ew', pady=6, padx=5)
            card.grid_columnconfigure(1, weight=1)
            
            left_frame = ctk.CTkFrame(card, fg_color='transparent')
            left_frame.grid(row=0, column=0, sticky='ns', padx=10, pady=10)
            
            var_select = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(
                left_frame,
                text='',
                variable=var_select,
                width=20,
                command=self.update_count
            )
            chk.pack(pady=(5, 10))
            
            lbl_no = ctk.CTkLabel(left_frame, text='Soru No:', font=config.FONTS['small'])
            lbl_no.pack(anchor='w')
            
            entry_number = ctk.CTkEntry(left_frame, width=50, justify='center')
            entry_number.pack(anchor='w', pady=2)
            entry_number.insert(0, str(q.get('number', idx + 1)))
            
            mid_frame = ctk.CTkFrame(card, fg_color='transparent')
            mid_frame.grid(row=0, column=1, sticky='ew', padx=10, pady=10)
            mid_frame.grid_columnconfigure(0, weight=1)
            
            lbl_text = ctk.CTkLabel(mid_frame, text='Soru Metni:', font=config.FONTS['small'])
            lbl_text.grid(row=0, column=0, sticky='w')
            
            txt_body = ctk.CTkTextbox(mid_frame, height=75, font=config.FONTS['body'])
            txt_body.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(2, 6))
            txt_body.insert('1.0', q.get('text', ''))
            
            opts_frame = ctk.CTkFrame(mid_frame, fg_color='transparent')
            opts_frame.grid(row=2, column=0, columnspan=2, sticky='ew')
            opts_frame.grid_columnconfigure(0, weight=1)
            opts_frame.grid_columnconfigure(1, weight=1)
            
            option_entries = {}
            option_pairs = [('a', 0, 0), ('b', 0, 1), ('c', 1, 0), ('d', 1, 1), ('e', 2, 0)]
            
            for opt_key, row, col in option_pairs:
                opt_row_frame = ctk.CTkFrame(opts_frame, fg_color='transparent')
                opt_row_frame.grid(row=row, column=col, sticky='ew', padx=3, pady=2)
                opt_row_frame.grid_columnconfigure(1, weight=1)
                
                lbl_opt = ctk.CTkLabel(
                    opt_row_frame,
                    text=f"{opt_key.upper()}:",
                    font=config.FONTS['small'],
                    width=15
                )
                lbl_opt.grid(row=0, column=0, sticky='w')
                
                entry_opt = ctk.CTkEntry(opt_row_frame, height=26, font=config.FONTS['body'])
                entry_opt.grid(row=0, column=1, sticky='ew', padx=3)
                entry_opt.insert(0, q.get('options', {}).get(opt_key, ''))
                
                option_entries[opt_key] = entry_opt
                
            right_frame = ctk.CTkFrame(card, fg_color='transparent')
            right_frame.grid(row=0, column=2, sticky='ns', padx=10, pady=10)
            
            lbl_correct = ctk.CTkLabel(right_frame, text='Doğru Cevap:', font=config.FONTS['small'])
            lbl_correct.pack(anchor='n', pady=(5, 2))
            
            combo_correct = ctk.CTkComboBox(
                right_frame,
                values=['A', 'B', 'C', 'D', 'E'],
                width=65,
                justify='center'
            )
            combo_correct.pack(anchor='n', pady=2)
            combo_correct.set(q.get('correct_answer', 'A').upper())
            
            self.question_widgets.append({
                'var_select': var_select,
                'entry_number': entry_number,
                'text_widget': txt_body,
                'option_entries': option_entries,
                'combo_correct': combo_correct
            })
            
        self.update_count()

    def toggle_all(self):
        val = self.var_select_all.get()
        for item in self.question_widgets:
            item['var_select'].set(val)
        self.update_count()

    def update_count(self, dummy=None):
        count = sum(1 for item in self.question_widgets if item['var_select'].get())
        self.btn_confirm.configure(text=f'📥 {count} Soruyu İçe Aktar')

    def on_confirm(self):
        course_text = self.course_combo.get()
        if not course_text or course_text == 'Ders bulunamadı!':
            messagebox.showwarning('Uyarı', 'Lütfen geçerli bir ders seçin!')
            return
            
        course_code = course_text.split(' - ')[0]
        course = next((c for c in self.courses if c.code == course_code), None)
        if not course:
            messagebox.showwarning('Uyarı', 'Seçilen ders bulunamadı!')
            return
            
        selected_questions = []
        for idx, item in enumerate(self.question_widgets):
            if not item['var_select'].get():
                continue
                
            q_num = item['entry_number'].get().strip()
            q_text = item['text_widget'].get('1.0', 'end-1c').strip()
            
            if not q_text:
                messagebox.showwarning('Uyarı', f'{idx + 1}. sorunun metni boş bırakılamaz!')
                return
                
            opts = {}
            for opt_key, entry in item['option_entries'].items():
                opts[opt_key] = entry.get().strip()
                
            filled = sum(1 for v in opts.values() if v)
            if filled < 2:
                messagebox.showwarning('Uyarı', f'{idx + 1}. soru ({q_num}) için en az 2 şık doldurulmalıdır!')
                return
                
            correct = item['combo_correct'].get().strip()
            
            selected_questions.append({
                'number': q_num,
                'text': q_text,
                'options': opts,
                'correct_answer': correct
            })
            
        if not selected_questions:
            messagebox.showwarning('Uyarı', 'Lütfen içe aktarmak için en az bir soru seçin!')
            return
            
        self.result = (
            course,
            selected_questions,
            self.difficulty_combo.get(),
            self.topic_entry.get().strip(),
            self.tags_entry.get().strip()
        )
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()
