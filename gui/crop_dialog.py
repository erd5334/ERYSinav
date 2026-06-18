"""
Görsel kırpma (crop) arayüzü penceresi
"""
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os
import logging
from pathlib import Path
import config

logger = logging.getLogger(__name__)

class CropDialog(ctk.CTkToplevel):
    """Görseli fare yardımıyla dikdörtgen çizerek kırpma modal diyaloğu"""
    
    def __init__(self, parent, image_path, title="Resmi Kırp"):
        super().__init__(parent)
        
        self.image_path = image_path
        self.title(title)
        
        self.transient(parent)
        self.grab_set()
        
        self.geometry("850x650")
        self.resizable(False, False)
        
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 850) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 650) // 2
        self.geometry(f"+{x}+{y}")
        
        self.result_path = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.rect_id = None
        
        try:
            self.orig_image = Image.open(image_path)
            self.orig_width, self.orig_height = self.orig_image.size
            
            self.create_layout()
            self.display_image()
            
            self.protocol('WM_DELETE_WINDOW', self.on_cancel)
            self.wait_window(self)
            
        except Exception as e:
            logger.error(f'Kırpma için resim yüklenemedi: {e}')
            self.destroy()

    def create_layout(self):
        info_label = ctk.CTkLabel(
            self,
            text='Resim üzerinde sürükleyip bırakarak kırpmak istediğiniz alanı seçin.',
            font=config.FONTS['body']
        )
        info_label.pack(pady=10)
        
        self.canvas_frame = ctk.CTkFrame(
            self,
            width=720,
            height=470,
            fg_color='gray20'
        )
        self.canvas_frame.pack(padx=20, pady=5, fill='both', expand=True)
        
        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg='#212121',
            highlightthickness=0,
            cursor='cross'
        )
        self.canvas.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.canvas.bind('<ButtonPress-1>', self.on_button_press)
        self.canvas.bind('<B1-Motion>', self.on_move_press)
        self.canvas.bind('<ButtonRelease-1>', self.on_button_release)
        
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(pady=15, fill='x')
        
        self.btn_crop = ctk.CTkButton(
            btn_frame,
            text='✂️ Seçilen Alanı Kırp',
            command=self.on_crop,
            width=180,
            height=40,
            fg_color=config.COLORS['success'],
            hover_color='#278c60'
        )
        self.btn_crop.pack(side='left', padx=(200, 10), expand=True)
        
        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text='❌ İptal',
            command=self.on_cancel,
            width=180,
            height=40,
            fg_color='gray',
            hover_color='darkgray'
        )
        self.btn_cancel.pack(side='left', padx=(10, 200), expand=True)

    def display_image(self):
        canvas_w = 800
        canvas_h = 450
        
        ratio = min(canvas_w / self.orig_width, canvas_h / self.orig_height)
        self.disp_width = int(self.orig_width * ratio)
        self.disp_height = int(self.orig_height * ratio)
        
        resized = self.orig_image.resize((self.disp_width, self.disp_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        
        self.canvas.config(width=self.disp_width, height=self.disp_height)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)
        
        self.scale_x = self.orig_width / self.disp_width
        self.scale_y = self.orig_height / self.disp_height

    def on_button_press(self, event):
        self.start_x = max(0, min(event.x, self.disp_width))
        self.start_y = max(0, min(event.y, self.disp_height))
        
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    def on_move_press(self, event):
        cur_x = max(0, min(event.x, self.disp_width))
        cur_y = max(0, min(event.y, self.disp_height))
        
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)
        else:
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, cur_x, cur_y,
                outline='red', width=2, dash=(4, 4)
            )

    def on_button_release(self, event):
        self.end_x = max(0, min(event.x, self.disp_width))
        self.end_y = max(0, min(event.y, self.disp_height))

    def on_crop(self):
        if (self.start_x is None or self.end_x is None or
            abs(self.start_x - self.end_x) < 5 or
            abs(self.start_y - self.end_y) < 5):
            tk.messagebox.showwarning('Uyarı', 'Lütfen kırpmak için resim üzerinde bir alanı sürükleyerek seçin!')
            return
            
        try:
            x1 = int(min(self.start_x, self.end_x) * self.scale_x)
            y1 = int(min(self.start_y, self.end_y) * self.scale_y)
            x2 = int(max(self.start_x, self.end_x) * self.scale_x)
            y2 = int(max(self.start_y, self.end_y) * self.scale_y)
            
            cropped = self.orig_image.crop((x1, y1, x2, y2))
            
            temp_dir = config.DATA_DIR / 'temp'
            temp_dir.mkdir(exist_ok=True)
            
            orig_suffix = Path(self.image_path).suffix or '.png'
            temp_path = temp_dir / f"cropped_temp_{os.urandom(4).hex()}{orig_suffix}"
            
            cropped.save(temp_path)
            self.result_path = str(temp_path)
            
            logger.info(f'Resim kırpıldı ve kaydedildi: {self.result_path}')
            self.grab_release()
            self.destroy()
            
        except Exception as e:
            logger.error(f'Kırpma işlemi hatası: {e}')
            tk.messagebox.showerror('Hata', f'Kırpma işlemi sırasında hata oluştu:\n{e}')

    def on_cancel(self):
        self.result_path = None
        self.grab_release()
        self.destroy()
