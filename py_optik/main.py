import sys, os, cv2, numpy as np, sqlite3, csv, subprocess
from PyQt6.QtWidgets import (QApplication, QFileDialog, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QDoubleSpinBox, QMessageBox,
                             QDialog, QLineEdit, QListWidget, QListWidgetItem,
                             QPushButton, QVBoxLayout, QHBoxLayout)
from PyQt6.QtCore import Qt, QRect, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QIcon

class PDFWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    def __init__(self, pdf_path, output_dir, engine, omr_params):
        super().__init__(); self.pdf_path = pdf_path; self.output_dir = output_dir; self.engine = engine; self.omr_params = omr_params
    
    def run(self):
        images = PDFConverter.convert_to_images(self.pdf_path, self.output_dir, engine=self.engine, omr_params=self.omr_params, on_progress=(lambda p: self.progress.emit(p))); self.finished.emit(images)


from app.ui.main_window import MainWindow
from app.utils.config import ConfigManager
from app.engine.processor import OMREngine
from app.engine.pdf_converter import PDFConverter; BASE_SOL, BASE_UST, BASE_SAG, BASE_ALT = (103, 483, 1184, 1956)

class StudentSelectionDialog(QDialog):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.selected_no = ""
        self.selected_name = ""
        self.setWindowTitle("Öğrenci Eşleştir ve Seç")
        self.resize(400, 500)
        self.setStyleSheet("background-color: #222; color: white; border: 1px solid #1e88e5;")
        
        layout = QVBoxLayout(self)
        
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("İsim veya numara ile ara...")
        self.search_edit.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 5px; font-size: 14px;")
        layout.addWidget(self.search_edit)
        
        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet("background-color: #1a1a1a; color: white; border: 1px solid #555; font-size: 13px;")
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("Seç", self)
        self.btn_select.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px;")
        self.btn_cancel = QPushButton("İptal", self)
        self.btn_cancel.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; padding: 6px;")
        
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        self.search_edit.textChanged.connect(self.search_students)
        self.list_widget.itemDoubleClicked.connect(self.accept_selection)
        self.btn_select.clicked.connect(self.accept_selection)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.search_students()
        
    def search_students(self):
        self.list_widget.clear()
        txt = self.search_edit.text().strip()
        try:
            def tr_lower(s):
                if s is None:
                    return ''
                return s.replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç').lower()
            conn = sqlite3.connect(self.db_path)
            conn.create_function('TR_LOWER', 1, tr_lower)
            cur = conn.cursor()
            if txt:
                pattern = f"%{tr_lower(txt)}%"
                cur.execute("SELECT o_n, isim FROM ogrbilgi WHERE TR_LOWER(o_n) LIKE ? OR TR_LOWER(isim) LIKE ? LIMIT 100", (pattern, pattern))
            else:
                cur.execute("SELECT o_n, isim FROM ogrbilgi LIMIT 100")
            rows = cur.fetchall()
            conn.close()
            for row in rows:
                item_text = f"{row[0]} - {row[1]}"
                item = QListWidgetItem(item_text)
                self.list_widget.addItem(item)
        except Exception as e:
            print(f"Error in search_students: {e}")
            
    def accept_selection(self):
        curr = self.list_widget.currentItem()
        if curr:
            text = curr.text()
            if " - " in text:
                self.selected_no, self.selected_name = text.split(" - ", 1)
                self.accept()
            else:
                self.reject()
        else:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir öğrenci seçin.")

class OptikApp:
    def __init__(self):
        self.templates = {}
        self.active_template_name = ""
        self.app = QApplication(sys.argv); self.config = ConfigManager(); self.engine = OMREngine(); self.window = MainWindow(); self.window.image_display.parent_app = self; self.window.tpl_image_display.parent_app = self; self.db_path = self.get_resource_path("testcevaplari.db3"); self.csv_output = self.get_resource_path("optik_sonuclar.csv")
        _icon_path = self.get_resource_path("icon.ico")
        if not os.path.exists(_icon_path):
            _icon_path = self.get_resource_path("icon.png")
        if os.path.exists(_icon_path):
            _app_icon = QIcon(_icon_path)
            self.app.setWindowIcon(_app_icon)
            self.window.setWindowIcon(_app_icon)
        
        self.window.btn_open_pdf.clicked.connect(self.open_pdf)
        
        self.window.btn_open_folder.clicked.connect(self.open_folder); self.window.btn_read.clicked.connect(self.read_form)
        
        self.window.btn_save.clicked.connect(self.save_result_csv); self.window.btn_report.clicked.connect(self.generate_pdf_report)
        
        self.window.btn_mass_report.clicked.connect(self.generate_mass_pdf_report)
        
        self.window.btn_t2_read.clicked.connect(self.read_answer_key)
        
        self.window.btn_t2_save.clicked.connect(self.save_answer_key); self.window.btn_t2_apply_all.clicked.connect(self.apply_all_points)
        
        self.window.btn_prev.clicked.connect(self.previous_image)
        
        self.window.btn_next.clicked.connect(self.next_image); self.window.btn_save_shortcuts.clicked.connect(self.save_shortcuts); self.load_shortcuts()
        
        self.window.file_list.currentItemChanged.connect(self.display_image_with_calib)
        
        self.window.result_table.itemChanged.connect(self.on_table_edit); self.window.edit_student_no.textChanged.connect(self.on_panel_no_change)
        self.window.btn_preview_mode.toggled.connect(self.live_refresh)
        self.window.btn_select_student.clicked.connect(self.select_student_from_db)
        
        self.window.edit_student_no.editingFinished.connect(self.rename_current_image)
        
        self.window.btn_db_add.clicked.connect(self.add_db_student); self.window.btn_db_delete.clicked.connect(self.delete_db_student)
        
        self.window.btn_db_clear.clicked.connect(self.clear_db_students); self.window.btn_db_import.clicked.connect(self.import_excel_students)
        
        self.window.edit_student_search.textChanged.connect(self.load_db_students)
        
        self.window.db_table.doubleClicked.connect(self.on_db_table_select)
        
        self.window.btn_refresh_stats.clicked.connect(self.calculate_detailed_stats)
        
        self.window.btn_export_excel.clicked.connect(self.export_excel_report); self.init_database(); self.load_db_students()
        
        for spin in (self.window.spin_x,
            self.window.spin_y,
            self.window.spin_rotate,
            self.window.spin_black,
            self.window.spin_thresh):
            spin.valueChanged.connect(self.live_refresh)
        self.current_image_path = None; self.output_dir = "temp_images"; self.last_result = None; self.display_width = 700
        self.read_zoom_factor = 1.0
        
        self.tpl_zoom_factor = 1.0
        
        self.d_sol, self.d_ust, self.d_sag, self.d_ak = (BASE_SOL, BASE_UST, BASE_SAG, BASE_ALT); last_folder = self.config.get("Ayarlar", "SonKlasor")
        if last_folder and os.path.exists(last_folder):
            self.output_dir = last_folder
        
        self.load_templates()
        self.load_images_from_folder(last_folder); self.create_excel_template()
        
        self.window.combo_templates.currentIndexChanged.connect(self.on_template_combo_changed)
        
        self.window.template_list.currentItemChanged.connect(self.on_template_list_changed)
        
        self.window.btn_new_template.clicked.connect(self.new_template)
        
        self.window.btn_delete_template.clicked.connect(self.delete_template); self.window.btn_save_tpl_settings.clicked.connect(self.save_template_settings)
        
        self.window.combo_align_mode.currentIndexChanged.connect(self.on_align_mode_changed)
        self.window.combo_color_mode.currentIndexChanged.connect(self.on_tpl_color_mode_changed)
        
        self.window.combo_analysis_exam.currentIndexChanged.connect(self.calculate_detailed_stats)
        
        self.window.list_tpl_blocks.currentItemChanged.connect(self.on_tpl_block_selected); self.window.btn_tpl_add_block.clicked.connect(self.add_tpl_block)
        
        self.window.btn_tpl_delete_block.clicked.connect(self.delete_tpl_block)
        
        self.window.btn_tpl_load_image.clicked.connect(self.load_tpl_image)
        
        self.window.btn_tpl_zoom_in.clicked.connect(self.zoom_in)
        
        self.window.btn_tpl_zoom_out.clicked.connect(self.zoom_out); self.window.btn_tpl_zoom_reset.clicked.connect(self.zoom_reset)
        
        self.window.btn_read_zoom_in.clicked.connect(self.read_zoom_in)
        self.window.btn_read_zoom_out.clicked.connect(self.read_zoom_out)
        self.window.btn_read_zoom_reset.clicked.connect(self.read_zoom_reset)
        
        self.window.edit_block_name.textChanged.connect(self.on_block_name_changed)
        
        self.window.combo_block_type.currentIndexChanged.connect(self.on_block_prop_changed); self.window.spin_block_rows.valueChanged.connect(self.on_block_prop_changed)
        
        self.window.spin_block_cols.valueChanged.connect(self.on_block_prop_changed); self.window.combo_block_zero_pos.currentIndexChanged.connect(self.on_block_prop_changed)
        
        self.window.spin_block_qstart.valueChanged.connect(self.on_block_prop_changed); self.window.spin_block_qcount.valueChanged.connect(self.on_block_prop_changed)
        
        self.window.spin_block_opt_count.valueChanged.connect(self.on_block_prop_changed)
    
    def create_excel_template(self):
        filename = "ogrenci_liste_taslagi.xlsx"
        if not os.path.exists(filename):
            try:
                import pandas as pd
                data = {"No": ["254605001", "254605002"], "Ad Soyad": ["ALİ YILMAZ", "AYŞE DEMİR"], "Birim": ["MYO", "MYO"], "Program": ["Bilgisayar Programcılığı", "Bilgisayar Programcılığı"]}
                df = pd.DataFrame(data)
                df.to_excel(filename, index=False)
                self.window.log_list.addItem(f"Şablon oluşturuldu: {filename}")
                return
            except:
                pass
    
    def get_resource_path(self, filename):
        path1 = os.path.join(os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__), filename)
        if os.path.exists(path1):
            pass
        
        return path1
        
        path2 = os.path.join(os.path.dirname(__file__), "..", filename)
        if os.path.exists(path2):
            pass
        
        return path2; return path1
    
    def load_images_from_folder(self, folder):
        if not folder or not os.path.exists(folder):
            return
        valid = (".jpg", ".jpeg", ".png", ".bmp")
        images = [f for f in os.listdir(folder) if f.lower().endswith(valid)]
        self.window.file_list.clear()
        for img in sorted(images):
            self.window.file_list.addItem(img)
    def update_last_folder(self, folder):
        self.output_dir = folder; self.config.set("Ayarlar", "SonKlasor", folder); self.load_images_from_folder(folder)
    
    def open_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self.window, "PDF Seç", "", "PDF Dosyaları (*.pdf)")
        if file_path:
            omr_params = (self.templates.get(self.active_template_name, {}), self.window.spin_black.value(), self.window.spin_thresh.value())
            self.window.progress_bar.setVisible(True)
            self.window.progress_bar.setValue(0)
            self.window.btn_open_pdf.setEnabled(False)
            self.pdf_worker = PDFWorker(file_path, "temp_images", self.engine, omr_params)
            self.pdf_worker.progress.connect(self.window.progress_bar.setValue)
            self.pdf_worker.finished.connect(self.on_pdf_finished)
            self.pdf_worker.start()
    
    def on_pdf_finished(self, images):
        self.window.progress_bar.setVisible(False); self.window.btn_open_pdf.setEnabled(True); self.update_last_folder(os.path.abspath("temp_images")); self.window.log_list.addItem(f"PDF Dönüştürmme Tamamlandı: {len(images)} sayfa.")
        
        self.window.log_list.scrollToBottom()
    
    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self.window, "Klasör Seç")
        if folder_path:
            self.update_last_folder(folder_path)
    
    def on_manual_rect_drawn(self, rect):
        self.window.log_list.addItem("İpucu: Blok koordinatlarını çizmek ve düzenlemek için 'ŞABLON EDİTÖRÜ' sekmesini kullanın."); self.window.log_list.scrollToBottom()
    
    def get_active_editing_template_name(self):
        item = self.window.template_list.currentItem()
        if item:
            return item.text().strip()
        return ""
    
    def on_tpl_rect_drawn(self, rect):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates: return
        
        sel_item = self.window.list_tpl_blocks.currentItem()
        if not sel_item:
            self.window.log_list.addItem("Lütfen çizim yapmadan önce sağdan bir blok seçin.")
            self.window.log_list.scrollToBottom()
            return
            
        block_name = sel_item.text()
        tpl = self.templates[tpl_name]
        
        block = None
        for b in tpl.get("blocks", []):
            if b["name"] == block_name:
                block = b
                break
                
        if not block: return
        
        pixmap = self.window.tpl_image_display.pixmap()
        if not pixmap: return
        
        pix_w = pixmap.width()
        pix_h = pixmap.height()
        lbl_w = self.window.tpl_image_display.width()
        lbl_h = self.window.tpl_image_display.height()
        
        offset_x = (lbl_w - pix_w) // 2 if lbl_w > pix_w else 0
        offset_y = 0
        
        rx = rect.x() - offset_x
        ry = rect.y() - offset_y
        rw = rect.width()
        rh = rect.height()
        
        px1 = max(0.0, min(float(pix_w), float(rx)))
        py1 = max(0.0, min(float(pix_h), float(ry)))
        px2 = max(0.0, min(float(pix_w), float(rx + rw)))
        py2 = max(0.0, min(float(pix_h), float(ry + rh)))
        
        block["x1"] = px1 / pix_w
        block["y1"] = py1 / pix_h
        block["x2"] = px2 / pix_w
        block["y2"] = py2 / pix_h
        
        if block.get("type") == "align_border":
            try:
                img_path = self.current_image_path
                if img_path and os.path.exists(img_path):
                    color_mode = tpl.get("color_mode", "gray")
                    img_gray = self.engine.load_image(img_path, color_mode=color_mode)
                    if img_gray is not None:
                        h, w = img_gray.shape[:2]
                        rx1 = int(block["x1"] * w)
                        ry1 = int(block["y1"] * h)
                        rx2 = int(block["x2"] * w)
                        ry2 = int(block["y2"] * h)
                        
                        search_x1 = max(0, rx1 - 15)
                        search_x2 = min(w, rx2 + 15)
                        search_y1 = max(0, ry1 - 15)
                        search_y2 = min(h, ry2 + 15)
                        
                        strip_roi = img_gray[search_y1:search_y2, search_x1:search_x2]
                        _, thresh = cv2.threshold(strip_roi, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
                        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        candidates = []
                        for cnt in contours:
                            x, y, cw, ch = cv2.boundingRect(cnt)
                            cx = search_x1 + x + cw // 2
                            cy = search_y1 + y + ch // 2
                            candidates.append((cx, cy))
                            
                        if len(candidates) >= 3:
                            xs = [c[0] for c in candidates]
                            median_x = np.median(xs)
                            centers = [c for c in candidates if abs(c[0] - median_x) <= 15]
                            centers.sort(key=lambda pt: pt[1])
                            
                            if len(centers) >= 3:
                                top_x, top_y = centers[0]
                                bot_x, bot_y = centers[-1]
                                block["y1"] = float(top_y) / h
                                block["y2"] = float(bot_y) / h
                                block["x1"] = float(median_x - 20) / w
                                block["x2"] = float(median_x + 20) / w
                                self.window.log_list.addItem("Kılavuz çizgiler algılandı. Hizalama bloğu otomatik uyarlandı.")
            except Exception as e:
                print(f"Auto-snap error: {e}")
                
        self.window.lbl_block_coords.setText(f"Konum: ({block['x1']:.3f}, {block['y1']:.3f}) - ({block['x2']:.3f}, {block['y2']:.3f})")
        self.refresh_tpl_editor_view()
        
        if block.get("type") == "header_area" and self.current_image_path and os.path.exists(self.current_image_path):
            img_bgr = cv2.imdecode(np.fromfile(self.current_image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img_bgr is not None:
                self.update_student_info_preview(img_bgr)
    def display_image_with_calib(self, current, previous):
        if not current:
            pass
        
        self.window.spin_x.blockSignals(True); self.window.spin_x.setValue(0); self.window.spin_x.blockSignals(False); self.window.spin_y.blockSignals(True)
        
        self.window.spin_y.setValue(0)
        
        self.window.spin_y.blockSignals(False); self.window.spin_rotate.blockSignals(True)
        
        self.window.spin_rotate.setValue(0.0)
        
        self.window.spin_rotate.blockSignals(False); self.window.spin_black.blockSignals(True); self.window.spin_black.setValue(180)
        
        self.window.spin_black.blockSignals(False)
        
        self.window.spin_thresh.blockSignals(True); self.window.spin_thresh.setValue(170); self.window.spin_thresh.blockSignals(False)
        
        self.current_image_path = os.path.join(self.output_dir, current.text())
        
        img_bgr = cv2.imdecode(np.fromfile(self.current_image_path, dtype=np.uint8), cv2.IMREAD_COLOR); deskewed = PDFConverter.deskew(img_bgr)
        if deskewed is not img_bgr:
            ext = os.path.splitext(self.current_image_path)[1]
            is_success, buffer = cv2.imencode(ext, deskewed)
            if is_success:
                with open(self.current_image_path, "wb") as f:
                    f.write(buffer.tobytes())
        img_bgr = deskewed; self.update_student_info_preview(img_bgr); self.live_refresh()
        
        self.refresh_tpl_editor_view()
    
    def update_student_info_preview(self, img_bgr):
        if not hasattr(self, "active_template_name") or not self.active_template_name or not hasattr(self, "templates"):
            return
        tpl = self.templates.get(self.active_template_name, {})
        header_block = None
        for b in tpl.get("blocks", []):
            if b.get("type") == "header_area":
                header_block = b
                break
                
        h, w = img_bgr.shape[:2]
        pix = self.cv2_to_pixmap(img_bgr)
        
        if header_block:
            bx1 = int(header_block["x1"] * w)
            by1 = int(header_block["y1"] * h)
            bx2 = int(header_block["x2"] * w)
            by2 = int(header_block["y2"] * h)
            bx1 = max(0, min(w, bx1))
            by1 = max(0, min(h, by1))
            bx2 = max(0, min(w, bx2))
            by2 = max(0, min(h, by2))
            if bx2 > bx1 and by2 > by1:
                info_rect = QRect(bx1, by1, bx2 - bx1, by2 - by1)
            else:
                info_rect = QRect(0, int(0.01 * h), w, int(0.14 * h))
        else:
            info_rect = QRect(0, int(0.01 * h), w, int(0.14 * h))
            
        snippet = pix.copy(info_rect)
        lbl_w = self.window.student_info_preview.width()
        lbl_h = self.window.student_info_preview.height()
        if lbl_w <= 100: lbl_w = 320
        if lbl_h <= 100: lbl_h = 450
        
        scaled_snippet = snippet.scaled(lbl_w, lbl_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.window.student_info_preview.setPixmap(scaled_snippet)
    def cv2_to_pixmap(self, img):
        if len(img.shape) == 3:
            h, w, c = img.shape
            qimg = QImage(img.data, w, h, w * c, QImage.Format.Format_BGR888)
        else:
            h, w = img.shape
            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
        return QPixmap.fromImage(qimg)
    
    def apply_manual_rotate(self, img, angle):
        if angle == 0:
            return img
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    
    def live_refresh(self, _val=None, debug_points=None):
        if not self.current_image_path:
            return
            
        tpl = self.templates.get(self.active_template_name, {})
        img_bgr = cv2.imdecode(np.fromfile(self.current_image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_bgr is None:
            return
        img_bgr = self.engine.align_image(img_bgr, tpl)
        
        color_mode = tpl.get("color_mode", "gray")
        if color_mode == "red":
            r_chan = img_bgr[:, :, 2]
            img_bgr = cv2.merge([r_chan, r_chan, r_chan])
        elif color_mode == "green":
            g_chan = img_bgr[:, :, 1]
            img_bgr = cv2.merge([g_chan, g_chan, g_chan])
        elif color_mode == "blue":
            b_chan = img_bgr[:, :, 0]
            img_bgr = cv2.merge([b_chan, b_chan, b_chan])
            
        angle = self.window.spin_rotate.value()
        x_off = self.window.spin_x.value()
        y_off = self.window.spin_y.value()
        blk = self.window.spin_black.value()
        
        img_rot = self.apply_manual_rotate(img_bgr, angle)
        h, w = img_rot.shape[:2]
        
        # Real-time bubble scanning feedback setup
        img_gray_temp = cv2.cvtColor(img_rot, cv2.COLOR_BGR2GRAY)
        _, binary_temp = cv2.threshold(img_gray_temp, blk, 255, cv2.THRESH_BINARY)
        thr = self.window.spin_thresh.value()
        
        if hasattr(self.window, 'btn_preview_mode') and self.window.btn_preview_mode.isChecked():
            img_rot = cv2.cvtColor(binary_temp, cv2.COLOR_GRAY2BGR)
        
        blocks = tpl.get("blocks", [])
        
        for b in blocks:
            bx1 = int(b["x1"] * w + x_off)
            by1 = int(b["y1"] * h + y_off)
            bx2 = int(b["x2"] * w + x_off)
            by2 = int(b["y2"] * h + y_off)
            b_type = b.get("type", "answers")
            
            if b_type == "student_no":
                color = (255, 0, 0)
                name_lbl = "Ogr No"
            elif b_type == "booklet":
                color = (0, 255, 0)
                name_lbl = "Kitapcik"
            elif b_type == "align_border":
                color = (0, 165, 255)
                name_lbl = "Cerceve Alani"
            elif b_type == "header_area":
                color = (255, 0, 255)
                name_lbl = b.get("name", "Isim Alani")
            else:
                color = (0, 255, 255)
                name_lbl = b.get("name", "Cevaplar")
                
            cv2.rectangle(img_rot, (bx1, by1), (bx2, by2), color, 3)
            cv2.putText(img_rot, name_lbl, (bx1, max(20, by1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            rows = b.get("rows", 10)
            cols = b.get("cols", 5)
            if b_type in ("align_border", "header_area"):
                continue
            if not (rows > 0 and cols > 0 and bx2 > bx1 and by2 > by1):
                continue
                
            row_h = (by2 - by1) / rows
            col_w = (bx2 - bx1) / cols
            for r in range(rows):
                cy = int(by1 + (r + 0.5) * row_h)
                for c in range(cols):
                    cx = int(bx1 + (c + 0.5) * col_w)
                    is_marked, _ = self.engine.scan_bubble(binary_temp, cx, cy, radius=5, threshold=thr)
                    if is_marked:
                        cv2.circle(img_rot, (cx, cy), 6, (113, 204, 46), -1)
                    else:
                        cv2.circle(img_rot, (cx, cy), 6, (60, 76, 231), 2)
                    
        if debug_points:
            for pt in debug_points:
                cv2.circle(img_rot, (int(pt[0]), int(pt[1])), 8, (0, 0, 255), -1)
                
        pix = self.cv2_to_pixmap(img_rot)
        scaled_pix = pix.scaledToWidth(int(self.display_width * self.read_zoom_factor), Qt.TransformationMode.SmoothTransformation)
        self.window.image_display.setPixmap(scaled_pix)
        self.window.image_display.setFixedSize(scaled_pix.size())
        self.window.t2_image_display.setPixmap(scaled_pix)
        self.window.t2_image_display.setFixedSize(scaled_pix.size())
    def _prepare_binary_image(self):
        if not self.current_image_path:
            return None
        tpl = self.templates.get(self.active_template_name, {})
        color_mode = tpl.get("color_mode", "gray")
        img_gray = self.engine.load_image(self.current_image_path, color_mode=color_mode)
        img_gray = self.engine.align_image(img_gray, tpl)
        img_rot = self.apply_manual_rotate(img_gray, self.window.spin_rotate.value())
        thr = self.window.spin_thresh.value()
        blk = self.window.spin_black.value()
        y_off = self.window.spin_y.value()
        x_off = self.window.spin_x.value()
        _, binary = cv2.threshold(img_rot, blk, 255, cv2.THRESH_BINARY)
        h, w = binary.shape[:2]
        return binary, w, h, x_off, y_off, thr, tpl

    def read_answer_key(self):
        res = self._prepare_binary_image()
        if res is None:
            return
        binary, w, h, x_off, y_off, thr, tpl = res
        blocks = tpl.get("blocks", [])
        tpts = []
        tg = "1"
        bk_block = None
        for b in blocks:
            if b.get("type") == "booklet":
                bk_block = b
                break
                
        if bk_block:
            bx1 = bk_block["x1"] * w + x_off
            by1 = bk_block["y1"] * h + y_off
            bx2 = bk_block["x2"] * w + x_off
            by2 = bk_block["y2"] * h + y_off
            rows = bk_block.get("rows", 1)
            cols = bk_block.get("cols", 5)
            grid = self.engine.scan_block_grid(binary, bx1, by1, bx2, by2, rows, cols, threshold=thr)
            found = False
            for r in range(rows):
                for c in range(cols):
                    is_marked, val, cx, cy = grid[r][c]
                    if is_marked:
                        tg = str(c + 1)
                        tpts.append((cx, cy))
                        found = True
                        break
                if found: break
                
        self.window.t2_lbl_group.setText(tg)
        answers_blocks = [b for b in blocks if b.get("type") == "answers"]
        
        if not answers_blocks:
            q_count = tpl.get("soru_sayisi", 60)
            for i in range(q_count):
                self.window.t2_table.setItem(i, 1, QTableWidgetItem(""))
        else:
            for b in answers_blocks:
                ders_adi = b.get("name", "Cevap")
                table = self.t2_tables.get(ders_adi)
                if table:
                    for i in range(table.rowCount()):
                        table.setItem(i, 1, QTableWidgetItem(""))
                        
        for b in blocks:
            if b.get("type") == "answers":
                ders_adi = b.get("name", "Cevap")
                table = self.t2_tables.get(ders_adi) if answers_blocks else self.window.t2_table
                if not table:
                    continue
                bx1 = b["x1"] * w + x_off
                by1 = b["y1"] * h + y_off
                bx2 = b["x2"] * w + x_off
                by2 = b["y2"] * h + y_off
                rows = b.get("rows", 10)
                cols = b.get("cols", 5)
                
                grid = self.engine.scan_block_grid(binary, bx1, by1, bx2, by2, rows, cols, threshold=thr)
                for r in range(rows):
                    if r >= table.rowCount():
                        continue
                    marked_choices = []
                    for c in range(cols):
                        is_marked, val, cx, cy = grid[r][c]
                        if is_marked:
                            marked_choices.append((c, cx, cy))
                    if len(marked_choices) == 1:
                        c, cx, cy = marked_choices[0]
                        ans = chr(65 + c)
                        tpts.append((cx, cy))
                        table.setItem(r, 1, QTableWidgetItem(ans))
                    elif len(marked_choices) > 1:
                        tpts.extend(((cx, cy) for _, cx, cy in marked_choices))
                        table.setItem(r, 1, QTableWidgetItem("*"))
                            
        self.live_refresh(debug_points=tpts)
        self.window.log_list.addItem(f"Grup {tg} cevap modeli çıkarıldı.")
        self.window.log_list.scrollToBottom()
    def apply_all_points(self):
        val = self.window.t2_spin_all_points.value()
        tpl = self.templates.get(self.active_template_name, {})
        answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
        
        if not answers_blocks:
            q_count = tpl.get("soru_sayisi", 60)
            for i in range(q_count):
                spin = self.window.t2_table.cellWidget(i, 2)
                if spin:
                    spin.setValue(val)
        else:
            for b in answers_blocks:
                ders_adi = b.get("name", "Cevap")
                table = self.t2_tables.get(ders_adi)
                if table:
                    for i in range(table.rowCount()):
                        spin = table.cellWidget(i, 2)
                        if spin:
                            spin.setValue(val)
                            
        self.window.log_list.addItem(f"Tüm sorular {val} puan olarak güncellendi.")
        self.window.log_list.scrollToBottom()
    def previous_image(self):
        row = self.window.file_list.currentRow()
        if row > 0:
            self.window.file_list.setCurrentRow(row - 1)
    
    def next_image(self):
        row = self.window.file_list.currentRow()
        if row < self.window.file_list.count() - 1:
            self.window.file_list.setCurrentRow(row + 1)
    
    def save_answer_key(self):
        gr = self.window.t2_lbl_group.text().strip() or "1"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tpl = self.templates.get(self.active_template_name, {})
        answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
        exam_type = tpl.get("exam_type", "single")
        
        try:
            if not answers_blocks or exam_type == "single":
                filename = os.path.join(base_dir, f"cevap-{gr}.txt")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("Cevap Anahtari:|Puanlama.....:\n")
                    f.write(f"{gr}|0\n")
                    q_count = tpl.get("soru_sayisi", 60)
                    for i in range(q_count):
                        ans_item = self.window.t2_table.item(i, 1)
                        ans = ans_item.text().strip() if ans_item else ""
                        spin = self.window.t2_table.cellWidget(i, 2)
                        pt = spin.value() if spin else 1.0
                        f.write(f"{ans}|{pt}\n")
                self.window.log_list.addItem(f"KAYDEDİLDİ: {filename}")
                self.window.log_list.scrollToBottom()
            else:
                for b in answers_blocks:
                    ders_adi = b.get("name", "Cevap")
                    table = self.t2_tables.get(ders_adi)
                    if not table:
                        continue
                    filename = os.path.join(base_dir, f"cevap-{gr}-{ders_adi}.txt")
                    q_count = b.get("q_count", 10)
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write("Cevap Anahtari:|Puanlama.....:\n")
                        f.write(f"{gr}|0\n")
                        for i in range(q_count):
                            ans_item = table.item(i, 1)
                            ans = ans_item.text().strip() if ans_item else ""
                            spin = table.cellWidget(i, 2)
                            pt = spin.value() if spin else 1.0
                            f.write(f"{ans}|{pt}\n")
                    self.window.log_list.addItem(f"KAYDEDİLDİ: {filename}")
                self.window.log_list.scrollToBottom()
            QMessageBox.information(self.window, "Başarılı", "Cevap anahtarı başarıyla kaydedildi!")
        except Exception as e:
            self.window.log_list.addItem(f"Kayıt Hatası: {str(e)}")
            self.window.log_list.scrollToBottom()
            print(f"Hata: {e}")
            QMessageBox.critical(self.window, "Hata", f"Cevap anahtarı kaydedilirken bir hata oluştu:\n{str(e)}")
    def read_form(self):
        res = self._prepare_binary_image()
        if res is None:
            return
        binary, w, h, x_off, y_off, thr, tpl = res
        blocks = tpl.get("blocks", [])
        tpts = []
        okul_no = ""
        std_block = None
        
        for b in blocks:
            if b.get("type") == "student_no":
                std_block = b
                break
                
        if std_block:
            bx1 = std_block["x1"] * w + x_off
            by1 = std_block["y1"] * h + y_off
            bx2 = std_block["x2"] * w + x_off
            by2 = std_block["y2"] * h + y_off
            rows = std_block.get("rows", 10)
            cols = std_block.get("cols", 10)
            zero_pos = std_block.get("zero_pos", "sonda")
            grid = self.engine.scan_block_grid(binary, bx1, by1, bx2, by2, rows, cols, threshold=thr)
            for c in range(cols):
                for r in range(rows):
                    is_marked, val, cx, cy = grid[r][c]
                    if is_marked:
                        if zero_pos == "başta" or "bast" in str(zero_pos).lower():
                            digit = str(r % 10)
                        else:
                            digit = str((r + 1) % 10)
                        okul_no += digit
                        tpts.append((cx, cy))
                        break
                        
        tg = "1"
        bk_block = None
        for b in blocks:
            if b.get("type") == "booklet":
                bk_block = b
                break
                
        if bk_block:
            bx1 = bk_block["x1"] * w + x_off
            by1 = bk_block["y1"] * h + y_off
            bx2 = bk_block["x2"] * w + x_off
            by2 = bk_block["y2"] * h + y_off
            rows = bk_block.get("rows", 1)
            cols = bk_block.get("cols", 5)
            grid = self.engine.scan_block_grid(binary, bx1, by1, bx2, by2, rows, cols, threshold=thr)
            found = False
            for r in range(rows):
                for c in range(cols):
                    is_marked, val, cx, cy = grid[r][c]
                    if is_marked:
                        tg = str(c + 1)
                        tpts.append((cx, cy))
                        found = True
                        break
                if found: break
                
        answers_blocks = [b for b in blocks if b.get("type") == "answers"]
        
        if not answers_blocks:
            q_count = tpl.get("soru_sayisi", 60)
            ans = [""] * q_count
            for b in blocks:
                if b.get("type") == "answers":
                    bx1 = b["x1"] * w + x_off
                    by1 = b["y1"] * h + y_off
                    bx2 = b["x2"] * w + x_off
                    by2 = b["y2"] * h + y_off
                    rows = b.get("rows", 10)
                    cols = b.get("cols", 5)
                    q_start = b.get("q_start", 1)
                    grid = self.engine.scan_block_grid(binary, bx1, by1, bx2, by2, rows, cols, threshold=thr)
                    for r in range(rows):
                        q_num = q_start + r
                        if q_num > q_count: continue
                        marked_choices = []
                        for c in range(cols):
                            is_marked, val, cx, cy = grid[r][c]
                            if is_marked:
                                marked_choices.append((c, cx, cy))
                        if len(marked_choices) == 1:
                            c, cx, cy = marked_choices[0]
                            ans[q_num - 1] = chr(65 + c)
                            tpts.append((cx, cy))
                        elif len(marked_choices) > 1:
                            ans[q_num - 1] = "*"
                            tpts.extend(((cx, cy) for _, cx, cy in marked_choices))
            total_questions = q_count
        else:
            total_questions = sum((b.get("q_count", 10) for b in answers_blocks))
            ans = [""] * total_questions
            current_offset = 0
            for b in answers_blocks:
                bx1 = b["x1"] * w + x_off
                by1 = b["y1"] * h + y_off
                bx2 = b["x2"] * w + x_off
                by2 = b["y2"] * h + y_off
                rows = b.get("rows", 10)
                cols = b.get("cols", 5)
                b_q_count = b.get("q_count", 10)
                grid = self.engine.scan_block_grid(binary, bx1, by1, bx2, by2, rows, cols, threshold=thr)
                for r in range(min(rows, b_q_count)):
                    marked_choices = []
                    for c in range(cols):
                        is_marked, val, cx, cy = grid[r][c]
                        if is_marked:
                            marked_choices.append((c, cx, cy))
                    if len(marked_choices) == 1:
                        c, cx, cy = marked_choices[0]
                        ans[current_offset + r] = chr(65 + c)
                        tpts.append((cx, cy))
                    elif len(marked_choices) > 1:
                        ans[current_offset + r] = "*"
                        tpts.extend(((cx, cy) for _, cx, cy in marked_choices))
                current_offset += b_q_count
            q_count = total_questions
            
        self.live_refresh(debug_points=tpts)
        
        name = self.get_student_name(okul_no)
        d, y, b_cnt, tp = 0, 0, 0, 0.0
        self.window.result_table.blockSignals(True)
        
        for r_idx in range(4):
            for col_idx in range(q_count + 2):
                self.window.result_table.setItem(r_idx, col_idx, QTableWidgetItem(""))
                
        ders_stats = {}
        global_key = []
        exam_type = tpl.get("exam_type", "single")
        
        if not answers_blocks or exam_type == "single":
            global_key = self.load_answer_key_detailed(tg)
            for i in range(q_count):
                sa = ans[i]
                ka, kp = (global_key[i][0], global_key[i][1]) if global_key and i < len(global_key) else ("", 1.0)
                st = "D" if sa == ka and sa != "" else "B" if sa == "" else "Y"
                if st == "D":
                    d += 1
                    tp += kp
                elif st == "Y":
                    y += 1
                else:
                    b_cnt += 1
                self.window.result_table.setItem(0, i + 2, QTableWidgetItem(ka))
                self.window.result_table.setItem(1, i + 2, QTableWidgetItem(sa))
                self.window.result_table.setItem(3, i + 2, QTableWidgetItem(st))
        else:
            current_offset = 0
            for b in answers_blocks:
                dname = b.get("name", "Cevap")
                b_q_count = b.get("q_count", 10)
                b_key = self.load_answer_key_detailed(tg, dname)
                if not b_key:
                    b_key = [("", 1.0)] * b_q_count
                global_key.extend(b_key)
                
                dd, yy, bb, pp = 0, 0, 0, 0.0
                for r in range(b_q_count):
                    idx = current_offset + r
                    sa = ans[idx]
                    ka, kp = (b_key[r][0], b_key[r][1]) if r < len(b_key) else ("", 1.0)
                    st = "D" if sa == ka and sa != "" else "B" if sa == "" else "Y"
                    if st == "D":
                        dd += 1
                        pp += kp
                        d += 1
                        tp += kp
                    elif st == "Y":
                        yy += 1
                        y += 1
                    else:
                        bb += 1
                        b_cnt += 1
                    self.window.result_table.setItem(0, idx + 2, QTableWidgetItem(ka))
                    self.window.result_table.setItem(1, idx + 2, QTableWidgetItem(sa))
                    self.window.result_table.setItem(3, idx + 2, QTableWidgetItem(st))
                net = dd - (yy / 4.0)
                ders_stats[dname] = {"D": dd, "Y": yy, "B": bb, "Net": net, "Puan": pp}
                current_offset += b_q_count
                
        self.window.edit_student_no.blockSignals(True)
        self.window.edit_student_no.setText(okul_no)
        self.window.edit_student_no.blockSignals(False)
        self.window.lbl_student_name.setText(f"İsim: {name}")
        
        score_info = f"Puan: {tp:.1f} | "
        if exam_type == "multi":
            for dname, stat in ders_stats.items():
                score_info += f"{dname}: {stat['D']}D {stat['Y']}Y ({stat['Net']:.2f} Net) | "
        else:
            score_info += f"({d}D {y}Y {b_cnt}B)"
        self.window.lbl_score.setText(score_info)
        
        if name in ("İsim bulunamadı", "Bulunamadı", ""):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(200, self.select_student_from_db)
            
        self.window.result_table.setItem(1, 0, QTableWidgetItem(f"{okul_no} - {name}"))
        self.window.result_table.setItem(1, 1, QTableWidgetItem(tg))
        self.window.result_table.setItem(2, 1, QTableWidgetItem(tg))
        self.window.result_table.blockSignals(False)
        
        self.last_result = {
            "No": okul_no,
            "Isim": name,
            "Grup": tg,
            "Cevaplar": ans,
            "Key": global_key,
            "D": d,
            "Y": y,
            "B": b_cnt,
            "Puan": tp,
            "Dersler": ders_stats
        }
        self.window.log_list.addItem(f"Analiz Tamam: {okul_no}")
        self.window.log_list.scrollToBottom()
        self.rename_current_image()
    def generate_pdf_report(self):
        if not self.last_result:
            pass
        
        try:
            from fpdf import FPDF
            avg = 0
            if os.path.exists(self.csv_output):
                with open(self.csv_output, mode="r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f, delimiter=";")
                    next(reader)
                    scores = [float(row[3]) for row in reader if len(row) > 3]
                    if scores:
                        avg = sum(scores) / len(scores)
            pdf = FPDF()
            self._add_report_page(pdf, self.last_result, avg)
            student_no = str(self.last_result.get("No", "0")).strip()
            student_no = student_no or "bilinmeyen"
            rep_path = f"karne_{student_no}.pdf"
            pdf.output(rep_path)
            os.startfile(rep_path)
            return
            row = None
        except PermissionError:
            self.window.log_list.addItem("PDF Hatası: Karne dosyası açık! Lütfen açık olan PDF dosyasını kapatıp tekrar deneyin.")
            self.window.log_list.scrollToBottom()
    
    def generate_mass_pdf_report(self):
        if not os.path.exists(self.csv_output):
            self.window.log_list.addItem("Hata: Önce sonuçları kaydedip CSV oluşturmalısınız!")
            self.window.log_list.scrollToBottom()
            return
        try:
            from fpdf import FPDF
            pdf = FPDF()
            avg = 0
            rows = []
            with open(self.csv_output, mode="r", encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter=";")
                next(reader)
                rows = list(reader)
            if not rows:
                self.window.log_list.addItem("CSV'de veri bulunamadı.")
                self.window.log_list.scrollToBottom()
                return
            scores = [float(row[3]) for row in rows if len(row) > 3]
            if scores:
                avg = sum(scores) / len(scores)
                
            tpl = self.templates.get(self.active_template_name, {})
            answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
            exam_type = tpl.get("exam_type", "single")
            
            def get_full_key_for_mass(gr_id):
                if not answers_blocks or exam_type == "single":
                    return self.load_answer_key_detailed(gr_id)
                full_key = []
                for b in answers_blocks:
                    dname = b.get("name", "Cevap")
                    b_key = self.load_answer_key_detailed(gr_id, dname)
                    if b_key:
                        full_key.extend(b_key)
                    else:
                        full_key.extend([("", 1.0)] * b.get("q_count", 10))
                return full_key
                
            count = 0
            for row in rows:
                if len(row) < 7:
                    continue
                res = {
                    "No": row[0],
                    "Isim": row[1],
                    "Grup": row[2],
                    "Puan": row[3],
                    "D": row[4],
                    "Y": row[5],
                    "B": row[6],
                    "Cevaplar": row[7:]
                }
                res["Key"] = get_full_key_for_mass(res["Grup"])
                res["Dersler"] = {}
                self._add_report_page(pdf, res, avg)
                count += 1
                
            if count > 0:
                out_path = "toplu_karneler.pdf"
                pdf.output(out_path)
                os.startfile(out_path)
                self.window.log_list.addItem(f"Toplu Karne Hazır: {count} öğrenci.")
                self.window.log_list.scrollToBottom()
            else:
                self.window.log_list.addItem("CSV'de geçerli veri bulunamadı.")
                self.window.log_list.scrollToBottom()
        except PermissionError:
            self.window.log_list.addItem("Toplu PDF Hatası: 'toplu_karneler.pdf' dosyası açık! Lütfen dosyayı kapatıp tekrar deneyin.")
            self.window.log_list.scrollToBottom()
        except Exception as child_e:
            print(f"Hata: {str(child_e)}")
            self.window.log_list.addItem(f"Toplu PDF Hatası: {str(child_e)}")
            self.window.log_list.scrollToBottom()
    def _draw_pdf_header_and_student_info(self, pdf, data, avg, cf):
        from fpdf.enums import XPos, YPos; pdf.set_fill_color(255, 255, 255); pdf.rect(0, 0, 210, 40, "F"); logo_path = self.get_resource_path("logo.png")
        if os.path.exists(logo_path):
            pass
        pdf.image(logo_path, x=10, y=5, h=30); pdf.set_text_color(30, 41, 59); pdf.set_font(cf, "B", 18); pdf.set_xy(50, 15)
        
        pdf.cell(150, 10, "SINAV SONUÇ KARNESİ", align="C")
        
        pdf.set_draw_color(30, 41, 59); pdf.set_line_width(0.5); pdf.line(10, 38, 200, 38); pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 45)
        
        pdf.set_font(cf, "B", 11)
        
        pdf.set_fill_color(248, 250, 252); pdf.rect(10, 45, 190, 35, "F"); pdf.set_draw_color(203, 213, 225); pdf.rect(10, 45, 190, 35, "D")
        
        pdf.set_xy(15, 50); pdf.cell(30, 7, "Öğrenci No:"); pdf.set_font(cf, "", 11); pdf.cell(60, 7, str(data["No"]))
        
        pdf.set_font(cf, "B", 11); pdf.cell(30, 7, "Sınıf Ort:"); pdf.set_font(cf, "", 11)
        
        pdf.cell(30, 7, f"{avg:.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.set_x(15); pdf.set_font(cf, "B", 11); pdf.cell(30, 7, "Ad Soyad:"); pdf.set_font(cf, "", 11)
        
        pdf.cell(60, 7, str(data["Isim"]))
        
        puan = float(data["Puan"]); diff = puan - avg; pdf.set_font(cf, "B", 11); pdf.cell(30, 7, "Durum:")
        if diff >= 0:
            pdf.set_text_color(22, 101, 52)
            lbl = f"Ortalamanın {diff:.2f} Puan Üstünde"
        else:
            pdf.set_text_color(153, 27, 27)
            lbl = f"Ortalamanın {abs(diff):.2f} Puan Altında"
        
        pdf.cell(100, 7, lbl, new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.set_text_color(0, 0, 0); pdf.set_x(15)
        
        pdf.set_font(cf, "B", 11); pdf.cell(30, 7, "Grup / Puan:"); pdf.set_font(cf, "", 11)
        
        pdf.cell(60, 7, f"{data["Grup"]} / {data["Puan"]} PUAN")
    
    def _draw_pdf_question_table(self, pdf, answers, key, offset, count, cf):
        from fpdf.enums import XPos, YPos
        
        # Determine layout based on question count
        max_rows = 30
        num_cols = (count + max_rows - 1) // max_rows
        if num_cols < 1:
            num_cols = 1
        
        # Adjust column widths and positions based on column count
        if num_cols == 1:
            col_w = [12, 18, 18]
            col_xs = [81.0]
        elif num_cols == 2:
            col_w = [12, 18, 18]
            col_xs = [50.0, 112.0]
        elif num_cols == 3:
            col_w = [11, 15, 15]
            col_xs = [27.0, 78.0, 129.0]
        else: # 4 or more columns
            num_cols = 4  # cap at 4 columns
            col_w = [10, 14, 14]
            col_xs = [17.0, 60.0, 103.0, 146.0]
            
        t_width = sum(col_w)
        y_bak = pdf.get_y() + 2
        
        # Draw Headers
        pdf.set_fill_color(51, 65, 85)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(cf, "B", 9)
        for col_idx in range(num_cols):
            pdf.set_xy(col_xs[col_idx], y_bak)
            pdf.cell(col_w[0], 7, "Soru", 1, align="C", fill=True)
            pdf.cell(col_w[1], 7, "Senin", 1, align="C", fill=True)
            pdf.cell(col_w[2], 7, "Doğru", 1, align="C", fill=True)
            
        y_start = y_bak + 7
        pdf.set_font(cf, "", 9)
        pdf.set_text_color(0, 0, 0)
        
        # Calculate rows in the tallest column
        rows_in_col = min(max_rows, (count + num_cols - 1) // num_cols)
        
        for r in range(rows_in_col):
            bg = r % 2 == 1
            for col_idx in range(num_cols):
                q_idx = r + col_idx * rows_in_col
                if q_idx >= count:
                    continue
                    
                pdf.set_fill_color(241, 245, 249) if bg else pdf.set_fill_color(255, 255, 255)
                pdf.set_xy(col_xs[col_idx], y_start + r * 6.5)
                
                ans_val = answers[q_idx] if q_idx < len(answers) else "-"
                key_val = key[q_idx] if key and q_idx < len(key) else ""
                
                if isinstance(key_val, (list, tuple)):
                    key_val = key_val[0]
                    
                # Draw question number
                pdf.cell(col_w[0], 6.5, str(q_idx + 1 + offset), 1, align="C", fill=True)
                
                # Check correctness (ans_val is student's answer, key_val is correct answer)
                if ans_val != key_val and ans_val != "-" and ans_val != "":
                    pdf.set_text_color(185, 28, 28) # Red for wrong/invalid
                else:
                    pdf.set_text_color(0, 0, 0)
                    
                pdf.set_font(cf, "B", 9)
                pdf.cell(col_w[1], 6.5, str(ans_val or "-"), 1, align="C", fill=True)
                
                # Draw correct answer
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(cf, "", 9)
                pdf.cell(col_w[2], 6.5, str(key_val or "-"), 1, align="C", fill=True)
    
    def _add_report_page(self, pdf, data, avg):
        from fpdf.enums import XPos, YPos
        if "arial" not in pdf.fonts:
            f_bold = "C:\\\\Windows\\\\Fonts\\\\arialbd.ttf"
            f_norm = "C:\\\\Windows\\\\Fonts\\\\arial.ttf"
            if os.path.exists(f_norm):
                pdf.add_font("arial", "", f_norm)
                pdf.add_font("arial", "B", f_bold)
                
        cf = "arial" if "arial" in pdf.fonts else "Helvetica"
        tpl = self.templates.get(self.active_template_name, {})
        answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
        exam_type = tpl.get("exam_type", "single")
        is_multi_lesson = exam_type == "multi"
        
        q_count = len(data["Key"]) if data.get("Key") else 60
        y_val = int(data["Y"])
        d_val = int(data["D"])
        b_val = q_count - (d_val + y_val)
        
        ders_stats = {}
        if is_multi_lesson and answers_blocks:
            current_offset = 0
            for b in answers_blocks:
                dname = b.get("name", "Cevap")
                b_q_count = b.get("q_count", 10)
                dd, yy, bb, pp = 0, 0, 0, 0.0
                for r in range(b_q_count):
                    idx = current_offset + r
                    sa = data["Cevaplar"][idx] if idx < len(data["Cevaplar"]) else "-"
                    ka = ""
                    kp = 1.0
                    if data.get("Key") and idx < len(data["Key"]):
                        key_item = data["Key"][idx]
                        if isinstance(key_item, (list, tuple)):
                            ka = key_item[0]
                            if len(key_item) > 1:
                                kp = float(key_item[1])
                        elif isinstance(key_item, str):
                            ka = key_item
                            
                    if sa == ka and sa != "":
                        dd += 1
                        pp += kp
                    elif sa == "" or sa == "-":
                        bb += 1
                    else:
                        yy += 1
                net = dd - yy / 4.0
                ders_stats[dname] = {
                    "D": dd, "Y": yy, "B": bb, "Net": net, "Puan": pp,
                    "q_count": b_q_count, "offset": current_offset
                }
                current_offset += b_q_count
            data["Dersler"] = ders_stats
        elif data.get("Dersler"):
            ders_stats = data["Dersler"]
            current_offset = 0
            for b in answers_blocks:
                dname = b.get("name", "Cevap")
                if dname in ders_stats:
                    ders_stats[dname]["q_count"] = b.get("q_count", 10)
                    ders_stats[dname]["offset"] = current_offset
                current_offset += b.get("q_count", 10)
                
        if not is_multi_lesson:
            pdf.set_auto_page_break(False)
            pdf.add_page()
            self._draw_pdf_header_and_student_info(pdf, data, avg, cf)
            pdf.set_font(cf, "B", 11)
            pdf.set_text_color(30, 58, 138)
            pdf.set_xy(10, 85)
            pdf.cell(190, 10, f"TOPLAM: {q_count} Soru | {d_val} Doğru | {y_val} Yanlış | {b_val} Boş", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            self._draw_pdf_question_table(pdf, data["Cevaplar"], data["Key"], 0, q_count, cf)
        else:
            pdf.set_auto_page_break(False)
            pdf.add_page()
            self._draw_pdf_header_and_student_info(pdf, data, avg, cf)
            pdf.set_font(cf, "B", 11)
            pdf.set_text_color(30, 58, 138)
            pdf.set_xy(10, 85)
            pdf.cell(190, 10, f"TOPLAM: {q_count} Soru | {d_val} Doğru | {y_val} Yanlış | {b_val} Boş", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
            pdf.cell(190, 8, "DERS BAZLI BAŞARI DETAYLARI", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
            
            pdf.set_fill_color(51, 65, 85)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font(cf, "B", 9)
            headers = ["Ders Adı", "Soru Sayısı", "Doğru", "Yanlış", "Boş", "Net", "Puan"]
            widths = [50, 25, 20, 20, 20, 25, 30]
            
            pdf.set_x((210 - sum(widths)) / 2)
            for h_idx, h_name in enumerate(headers):
                pdf.cell(widths[h_idx], 8, h_name, 1, align="C", fill=True)
            pdf.ln(8)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(cf, "", 9)
            row_idx = 0
            for dname, stat in ders_stats.items():
                bg = row_idx % 2 == 1
                pdf.set_fill_color(241, 245, 249) if bg else pdf.set_fill_color(255, 255, 255)
                pdf.set_x((210 - sum(widths)) / 2)
                pdf.cell(widths[0], 7.5, dname, 1, align="C", fill=True)
                pdf.cell(widths[1], 7.5, str(stat.get("q_count", 10)), 1, align="C", fill=True)
                pdf.cell(widths[2], 7.5, str(stat["D"]), 1, align="C", fill=True)
                pdf.cell(widths[3], 7.5, str(stat["Y"]), 1, align="C", fill=True)
                pdf.cell(widths[4], 7.5, str(stat["B"]), 1, align="C", fill=True)
                pdf.cell(widths[5], 7.5, f"{stat['Net']:.2f}", 1, align="C", fill=True)
                pdf.cell(widths[6], 7.5, f"{stat['Puan']:.1f}", 1, align="C", fill=True)
                pdf.ln(7.5)
                row_idx += 1
                
            for dname, stat in ders_stats.items():
                pdf.add_page()
                self._draw_pdf_header_and_student_info(pdf, data, avg, cf)
                pdf.set_font(cf, "B", 12)
                pdf.set_text_color(30, 58, 138)
                pdf.set_xy(10, 85)
                pdf.cell(190, 8, f"{dname.upper()} DERSİ SORU ANALİZİ", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font(cf, "", 9)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(190, 6, f"Toplam Soru: {stat.get('q_count', 10)} | Doğru: {stat['D']} | Yanlış: {stat['Y']} | Boş: {stat['B']} | Net: {stat['Net']:.2f} | Puan: {stat['Puan']:.1f}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(0, 0, 0)
                
                offset = stat.get("offset", 0)
                count = stat.get("q_count", 10)
                lesson_ans = data["Cevaplar"][offset:offset + count]
                lesson_key = data["Key"][offset:offset + count]
                self._draw_pdf_question_table(pdf, lesson_ans, lesson_key, offset, count, cf)
    def save_result_csv(self):
        if not self.last_result:
            return
            
        cur_name = self.window.lbl_student_name.text().replace("İsim: ", "").replace("İsim bulunamadı", "Bulunamadı").strip()
        cur_no = self.window.edit_student_no.text().strip()
        
        try:
            write_headers = not os.path.exists(self.csv_output) or os.path.getsize(self.csv_output) == 0
            with open(self.csv_output, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                if write_headers:
                    tpl = self.templates.get(self.active_template_name, {})
                    exam_type = tpl.get("exam_type", "single")
                    answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
                    q_headers = []
                    if exam_type == "multi" and answers_blocks:
                        for b in answers_blocks:
                            dname = b.get("name", "Cevap")
                            q_start = b.get("q_start", 1)
                            for i in range(b.get("q_count", 10)):
                                q_headers.append(f"{dname} {q_start + i}")
                    else:
                        q_count = len(self.last_result.get("Cevaplar", []))
                        q_headers = [str(i + 1) for i in range(q_count)]
                    writer.writerow(["Numara", "İsim", "Grup", "Puan", "Doğru", "Yanlış", "Boş"] + q_headers)
                writer.writerow([cur_no, cur_name, self.last_result["Grup"],
                                 self.last_result["Puan"], self.last_result["D"],
                                 self.last_result["Y"], self.last_result["B"]] + self.last_result["Cevaplar"])
            self.window.log_list.addItem(f"CSV Kaydedildi: {cur_no}")
            self.window.log_list.scrollToBottom()
        except Exception as e:
            self.window.log_list.addItem(f"Hata: {str(e)}")
            self.window.log_list.scrollToBottom()
    def on_panel_no_change(self, text):
        if text.isdigit():
            name = self.get_student_name(text)
            self.window.lbl_student_name.setText(f"İsim: {name}")
    
    def rename_current_image(self):
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            return
        
        new_no = self.window.edit_student_no.text().strip()
        if not new_no:
            return
        
        old_dir = os.path.dirname(self.current_image_path)
        ext = os.path.splitext(self.current_image_path)[1]
        new_filename = f"{new_no}{ext}"
        new_path = os.path.join(old_dir, new_filename)
        
        if os.path.abspath(self.current_image_path) == os.path.abspath(new_path):
            return
        try:
            os.rename(self.current_image_path, new_path)
            self.window.file_list.blockSignals(True)
            item = self.window.file_list.currentItem()
            if item:
                item.setText(new_filename)
            self.window.file_list.blockSignals(False)
            self.current_image_path = new_path
            self.window.log_list.addItem(f"Dosya Yeniden Adlandırıldı: {new_filename}")
            self.window.log_list.scrollToBottom()
        except Exception as e:
            self.window.log_list.addItem(f"Yeniden adlandırma hatası: {e}")
    
    def on_table_edit(self, item):
        if not hasattr(self, "last_result") or not self.last_result:
            return
            
        row = item.row()
        col = item.column()
        
        # 1. Student ID Edit (Row 1, Col 0)
        if row == 1 and col == 0:
            val = item.text().strip()
            no = val.split("-")[0].strip() if "-" in val else val
            if no != self.last_result.get("No", ""):
                self.window.edit_student_no.blockSignals(True)
                self.window.edit_student_no.setText(no)
                self.window.edit_student_no.blockSignals(False)
                
                name = self.get_student_name(no)
                self.window.lbl_student_name.setText(f"İsim: {name}")
                
                self.last_result["No"] = no
                self.last_result["Isim"] = name
                
                self.window.result_table.blockSignals(True)
                item.setText(f"{no} - {name}")
                self.window.result_table.blockSignals(False)
                
                self.rename_current_image()
            return
            
        # 2. Booklet Group Edit (Row 1 Col 1 or Row 2 Col 1)
        if (row == 1 or row == 2) and col == 1:
            val = item.text().strip().upper()
            if val and val != self.last_result.get("Grup", ""):
                self.last_result["Grup"] = val
                
                self.window.result_table.blockSignals(True)
                self.window.result_table.setItem(1, 1, QTableWidgetItem(val))
                self.window.result_table.setItem(2, 1, QTableWidgetItem(val))
                self.window.result_table.blockSignals(False)
                
                self.recalculate_last_result(reload_key=True)
            return
            
        # 3. Student Answer Edit (Row 1, Col >= 2)
        if row == 1 and col >= 2:
            q_idx = col - 2
            val = item.text().strip().upper()
            
            answers = self.last_result.get("Cevaplar", [])
            if q_idx < len(answers):
                if answers[q_idx] != val:
                    answers[q_idx] = val
                    self.recalculate_last_result(reload_key=False)
            return

    def recalculate_last_result(self, reload_key=False):
        if not hasattr(self, "last_result") or not self.last_result:
            return
            
        tpl = self.templates.get(self.active_template_name, {})
        answers_blocks = tpl.get("answers_blocks", [])
        exam_type = tpl.get("exam_type", "single")
        tg = self.last_result["Grup"]
        
        ans = self.last_result["Cevaplar"]
        q_count = len(ans)
        
        if reload_key:
            global_key = []
            if not answers_blocks or exam_type == "single":
                global_key = self.load_answer_key_detailed(tg)
            else:
                current_offset = 0
                for b in answers_blocks:
                    dname = b.get("name", "Cevap")
                    b_q_count = b.get("q_count", 10)
                    b_key = self.load_answer_key_detailed(tg, dname)
                    if not b_key:
                        b_key = [("", 1.0)] * b_q_count
                    global_key.extend(b_key)
                    current_offset += b_q_count
                    
            if len(global_key) < q_count:
                global_key.extend([("", 1.0)] * (q_count - len(global_key)))
            elif len(global_key) > q_count:
                global_key = global_key[:q_count]
                
            self.last_result["Key"] = global_key
            
        global_key = self.last_result["Key"]
        d, y, b_cnt, tp = 0, 0, 0, 0.0
        ders_stats = {}
        
        self.window.result_table.blockSignals(True)
        if not answers_blocks or exam_type == "single":
            for i in range(q_count):
                sa = ans[i]
                ka, kp = (global_key[i][0], global_key[i][1]) if i < len(global_key) else ("", 1.0)
                st = "D" if sa == ka and sa != "" else "B" if sa == "" else "Y"
                if st == "D":
                    d += 1
                    tp += kp
                elif st == "Y":
                    y += 1
                else:
                    b_cnt += 1
                self.window.result_table.setItem(0, i + 2, QTableWidgetItem(ka))
                self.window.result_table.setItem(1, i + 2, QTableWidgetItem(sa))
                self.window.result_table.setItem(3, i + 2, QTableWidgetItem(st))
        else:
            current_offset = 0
            for b in answers_blocks:
                dname = b.get("name", "Cevap")
                b_q_count = b.get("q_count", 10)
                
                dd, yy, bb, pp = 0, 0, 0, 0.0
                for r in range(b_q_count):
                    idx = current_offset + r
                    if idx >= q_count:
                        break
                    sa = ans[idx]
                    ka, kp = (global_key[idx][0], global_key[idx][1]) if idx < len(global_key) else ("", 1.0)
                    st = "D" if sa == ka and sa != "" else "B" if sa == "" else "Y"
                    if st == "D":
                        dd += 1
                        pp += kp
                        d += 1
                        tp += kp
                    elif st == "Y":
                        yy += 1
                        y += 1
                    else:
                        bb += 1
                        b_cnt += 1
                    self.window.result_table.setItem(0, idx + 2, QTableWidgetItem(ka))
                    self.window.result_table.setItem(1, idx + 2, QTableWidgetItem(sa))
                    self.window.result_table.setItem(3, idx + 2, QTableWidgetItem(st))
                net = dd - (yy / 4.0)
                ders_stats[dname] = {"D": dd, "Y": yy, "B": bb, "Net": net, "Puan": pp}
                current_offset += b_q_count
        self.window.result_table.blockSignals(False)
        
        # Update labels
        score_info = f"Puan: {tp:.1f} | "
        if exam_type == "multi":
            for dname, stat in ders_stats.items():
                score_info += f"{dname}: {stat['D']}D {stat['Y']}Y ({stat['Net']:.2f} Net) | "
        else:
            score_info += f"({d}D {y}Y {b_cnt}B)"
        self.window.lbl_score.setText(score_info)
        
        self.last_result.update({
            "D": d,
            "Y": y,
            "B": b_cnt,
            "Puan": tp,
            "Dersler": ders_stats
        })

    def select_student_from_db(self):
        dialog = StudentSelectionDialog(self.db_path, parent=self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            no = dialog.selected_no
            name = dialog.selected_name
            
            self.window.edit_student_no.blockSignals(True)
            self.window.edit_student_no.setText(no)
            self.window.edit_student_no.blockSignals(False)
            
            self.window.lbl_student_name.setText(f"İsim: {name}")
            
            self.window.result_table.blockSignals(True)
            self.window.result_table.setItem(1, 0, QTableWidgetItem(f"{no} - {name}"))
            self.window.result_table.blockSignals(False)
            
            if hasattr(self, "last_result") and self.last_result:
                self.last_result["No"] = no
                self.last_result["Isim"] = name
                
            self.rename_current_image()
    
    def get_student_name(self, no):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('SELECT isim FROM ogrbilgi WHERE "o_n" = ?', (str(no).strip(),))
            res = cur.fetchone()
            conn.close()
            if res:
                return res[0]
        except Exception as e:
            print(f"Database error in get_student_name: {e}")
        return "Bulunamadı"
    
    def load_answer_key_detailed(self, gr, ders_adi=None):
        try:
            if ders_adi:
                filename = self.get_resource_path(f"cevap-{gr}-{ders_adi}.txt")
                if not os.path.exists(filename):
                    filename = self.get_resource_path(f"cevap-{gr}.txt")
            else:
                filename = self.get_resource_path(f"cevap-{gr}.txt")
            if not os.path.exists(filename):
                filename = self.get_resource_path(f"cevap{gr}.txt")
                
            if os.path.exists(filename):
                keys = []
                with open(filename, "r", encoding="latin-1") as f:
                    for line in f.readlines()[2:]:
                        p = line.split("|")
                        if len(p) >= 2:
                            keys.append((p[0].strip(), float(p[1].strip() or 0.0)))
                return keys
            return []
        except:
            return []
    def load_saved_answer_keys(self):
        gr = self.window.t2_lbl_group.text().strip() or "1"
        tpl = self.templates.get(self.active_template_name, {})
        answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
        exam_type = tpl.get("exam_type", "single")
        
        if not answers_blocks or exam_type == "single":
            key = self.load_answer_key_detailed(gr)
            if key:
                for i in range(min(len(key), self.window.t2_table.rowCount())):
                    self.window.t2_table.setItem(i, 1, QTableWidgetItem(key[i][0]))
                    spin = self.window.t2_table.cellWidget(i, 2)
                    if spin:
                        spin.setValue(key[i][1])
            return
        else:
            current_idx = 0
            for b in answers_blocks:
                ders_adi = b.get("name", "Cevap")
                table = self.t2_tables.get(ders_adi)
                if not table:
                    continue
                key = self.load_answer_key_detailed(gr, ders_adi)
                if key:
                    for i in range(min(len(key), table.rowCount())):
                        table.setItem(i, 1, QTableWidgetItem(key[i][0]))
                        spin = table.cellWidget(i, 2)
                        if spin:
                            spin.setValue(key[i][1])
    def save_shortcuts(self):
        import json
        
        data = {
            "prev": self.window.edit_key_prev.text().upper(),
            "next": self.window.edit_key_next.text().upper(),
            "read": self.window.edit_key_read.text().upper(),
            "save": self.window.edit_key_save.text().upper(),
            "focus": self.window.edit_key_focus.text().upper(),
            "x_dec": self.window.edit_key_x_dec.text().upper(),
            "x_inc": self.window.edit_key_x_inc.text().upper(),
            "y_dec": self.window.edit_key_y_dec.text().upper(),
            "y_inc": self.window.edit_key_y_inc.text().upper(),
            "rot_dec": self.window.edit_key_rot_dec.text().upper(),
            "rot_inc": self.window.edit_key_rot_inc.text().upper(),
            "blk_dec": self.window.edit_key_blk_dec.text().upper(),
            "blk_inc": self.window.edit_key_blk_inc.text().upper(),
            "thr_dec": self.window.edit_key_thr_dec.text().upper(),
            "thr_inc": self.window.edit_key_thr_inc.text().upper()
        }
        
        with open("shortcuts.json", "w") as f:
            json.dump(data, f)
        self.window.log_list.addItem("Kısayollar kaydedildi.")
    
    def load_shortcuts(self):
        try:
            import json
            if os.path.exists("shortcuts.json"):
                try:
                    with open("shortcuts.json", "r") as f:
                        data = json.load(f)
                        self.window.edit_key_prev.setText(data.get("prev", "Z"))
                        self.window.edit_key_next.setText(data.get("next", "X"))
                        self.window.edit_key_read.setText(data.get("read", "C"))
                        self.window.edit_key_save.setText(data.get("save", "V"))
                        self.window.edit_key_focus.setText(data.get("focus", "B"))
                        self.window.edit_key_x_dec.setText(data.get("x_dec", "J"))
                        self.window.edit_key_x_inc.setText(data.get("x_inc", "L"))
                        self.window.edit_key_y_dec.setText(data.get("y_dec", "I"))
                        self.window.edit_key_y_inc.setText(data.get("y_inc", "K"))
                        self.window.edit_key_rot_dec.setText(data.get("rot_dec", "U"))
                        self.window.edit_key_rot_inc.setText(data.get("rot_inc", "O"))
                        self.window.edit_key_blk_dec.setText(data.get("blk_dec", "N"))
                        self.window.edit_key_blk_inc.setText(data.get("blk_inc", "M"))
                        self.window.edit_key_thr_dec.setText(data.get("thr_dec", "G"))
                        self.window.edit_key_thr_inc.setText(data.get("thr_inc", "H"))
                except Exception as e:
                    print(f"Error loading shortcuts: {e}")
        except:
            pass
    def init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("\n                CREATE TABLE IF NOT EXISTS ogrbilgi (\n                    o_n VARCHAR(12) PRIMARY KEY DEFAULT '0',\n                    isim VARCHAR(20) DEFAULT '0',\n                    birim VARCHAR(20) DEFAULT '0',\n                    program VARCHAR(25) DEFAULT '0'\n                )\n            ")
            conn.commit()
            conn.close()
        except:
            pass
    
    def load_db_students(self):
        try:
            def tr_lower(s):
                if s is None:
                    return ''
                return s.replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç').lower()
            txt = self.window.edit_student_search.text().strip()
            conn = sqlite3.connect(self.db_path)
            conn.create_function('TR_LOWER', 1, tr_lower)
            cur = conn.cursor()
            if txt:
                pattern = f"%{tr_lower(txt)}%"
                cur.execute("SELECT * FROM ogrbilgi WHERE TR_LOWER(o_n) LIKE ? OR TR_LOWER(isim) LIKE ?", (pattern, pattern))
            else:
                cur.execute("SELECT * FROM ogrbilgi")
            rows = cur.fetchall()
            conn.close()
            self.window.db_table.setRowCount(0)
            for r_idx, row in enumerate(rows):
                self.window.db_table.insertRow(r_idx)
                for c_idx, val in enumerate(row):
                    self.window.db_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
        except:
            pass
    
    def on_db_table_select(self):
        row = self.window.db_table.currentRow()
        if row >= 0:
            self.window.edit_db_no.setText(self.window.db_table.item(row, 0).text())
            self.window.edit_db_name.setText(self.window.db_table.item(row, 1).text())
            self.window.edit_db_birim.setText(self.window.db_table.item(row, 2).text())
            self.window.edit_db_prog.setText(self.window.db_table.item(row, 3).text())
    
    def add_db_student(self):
        name = self.window.edit_db_name.text().strip(); no = self.window.edit_db_no.text().strip()
        
        prog = self.window.edit_db_prog.text().strip(); birim = self.window.edit_db_birim.text().strip()
        if not no or name:
            pass
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO ogrbilgi (o_n, isim, birim, program) VALUES (?, ?, ?, ?)", (no, name, birim, prog))
            conn.commit()
            conn.close()
            self.load_db_students()
            self.window.log_list.addItem(f"DB Güncellendi: {name}")
            self.window.log_list.scrollToBottom()
        except:
            pass
    
    def delete_db_student(self):
        row = self.window.db_table.currentRow()
        if row < 0:
            return
        
        no = self.window.db_table.item(row, 0).text()
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM ogrbilgi WHERE o_n = ?", (no,))
            conn.commit()
            conn.close()
            self.load_db_students()
            self.window.log_list.addItem(f"Öğrenci Silindi: {no}")
            self.window.log_list.scrollToBottom()
        except Exception as e:
            print(f"Error deleting student: {e}")
    
    def clear_db_students(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM ogrbilgi")
            conn.commit()
            conn.close()
            self.load_db_students()
            self.window.log_list.addItem("VERİTABANI TEMİZLENDİ.")
            self.window.log_list.scrollToBottom()
        except:
            pass
    
    def import_excel_students(self):
        path, _ = QFileDialog.getOpenFileName(self.window, "Excel Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if not path:
            pass
        try:
            import pandas as pd
            df = pd.read_excel(path).astype(str)
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            for _, row in df.iterrows():
                cur.execute("INSERT OR REPLACE INTO ogrbilgi (o_n, isim, birim, program) VALUES (?, ?, ?, ?)", 
                            (row.iloc[0], row.iloc[1], row.iloc[2] if len(row)>2 else "", row.iloc[3] if len(row)>3 else ""))
            conn.commit()
            conn.close()
            self.load_db_students()
            self.window.log_list.addItem(f"Excel'den {len(df)} öğrenci aktarıldı.")
            self.window.log_list.scrollToBottom()
        except:
            pass
    
    def calculate_detailed_stats(self):
        selected_exam = self.window.combo_analysis_exam.currentText()
        if not selected_exam:
            self.window.log_list.addItem("Analiz edilecek sınav seçilmedi.")
            return
            
        csv_path = self.get_resource_path(f"sonuclar_{selected_exam}.csv")
        if not os.path.exists(csv_path):
            self.window.log_list.addItem(f"Analiz edilecek veri bulunamadı ({selected_exam} için CSV yok).")
            self.window.lbl_stat_avg.setText("0.0")
            self.window.lbl_stat_max.setText("0.0")
            self.window.lbl_stat_min.setText("0.0")
            self.window.lbl_stat_count.setText("0")
            self.window.analysis_table.setRowCount(0)
            self.window.distractor_table.setRowCount(0)
            self.window.lbl_analysis_chart.setText("Grafik için veri bulunamadı.")
            return
            
        try:
            with open(csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter=";")
                next(reader)
                rows = list(reader)
            if not rows:
                self.window.lbl_stat_avg.setText("0.0")
                self.window.lbl_stat_max.setText("0.0")
                self.window.lbl_stat_min.setText("0.0")
                self.window.lbl_stat_count.setText("0")
                return
                
            scores = [float(row[3]) for row in rows]
            avg_val = sum(scores) / len(scores)
            max_val = max(scores)
            min_val = min(scores)
            count = len(rows)
            
            self.window.lbl_stat_avg.setText(f"{avg_val:.1f}")
            self.window.lbl_stat_max.setText(f"{max_val:.1f}")
            self.window.lbl_stat_min.setText(f"{min_val:.1f}")
            self.window.lbl_stat_count.setText(str(count))
            
            q_success = {}
            q_total_counts = {}
            q_choices = {}
            cached_keys = {}
            tpl = self.templates.get(selected_exam, {})
            answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
            exam_type = tpl.get("exam_type", "single")
            
            def get_full_key(gr_id):
                if not answers_blocks or exam_type == "single":
                    return self.load_answer_key_detailed(gr_id)
                full_key = []
                for b in answers_blocks:
                    dname = b.get("name", "Cevap")
                    b_key = self.load_answer_key_detailed(gr_id, dname)
                    if b_key:
                        full_key.extend(b_key)
                    else:
                        full_key.extend([("", 1.0)] * b.get("q_count", 10))
                return full_key
                
            q_names = []
            if not answers_blocks:
                ans_cols = len(rows[0]) - 7 if rows else 60
                q_names = [f"Soru {i + 1}" for i in range(ans_cols)]
            else:
                for b in answers_blocks:
                    dname = b.get("name", "Cevap")
                    q_start = b.get("q_start", 1)
                    for i in range(b.get("q_count", 10)):
                        if exam_type == "single":
                            q_names.append(f"Soru {q_start + i}")
                        else:
                            q_names.append(f"{dname} {q_start + i}")
                            
            for row in rows:
                gr = row[2]
                if gr not in cached_keys:
                    cached_keys[gr] = get_full_key(gr)
                key = cached_keys[gr]
                if not key:
                    continue
                ans_list = row[7:]
                for i, correct_tuple in enumerate(key):
                    correct_ans = correct_tuple[0]
                    student_ans = ans_list[i].strip().upper() if i < len(ans_list) else ""
                    if student_ans == "-":
                        student_ans = ""
                    if student_ans == correct_ans and student_ans != "":
                        q_success[i] = q_success.get(i, 0) + 1
                    q_total_counts[i] = q_total_counts.get(i, 0) + 1
                    if i not in q_choices:
                        q_choices[i] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "": 0}
                    if student_ans in q_choices[i]:
                        q_choices[i][student_ans] += 1
                    else:
                        q_choices[i][""] += 1
                        
            self.window.analysis_table.setRowCount(0)
            sorted_questions = sorted(q_total_counts.keys())
            for r_idx, q_idx in enumerate(sorted_questions):
                corrects = q_success.get(q_idx, 0)
                totals = q_total_counts[q_idx]
                ratio = (corrects / totals * 100.0) if totals > 0 else 0
                status = "Kolay" if ratio > 70 else "Orta" if ratio > 40 else "Zor"
                s_color = "#4caf50" if status == "Kolay" else "#ffc107" if status == "Orta" else "#f44336"
                
                self.window.analysis_table.insertRow(r_idx)
                q_name = q_names[q_idx] if q_idx < len(q_names) else f"Soru {q_idx + 1}"
                self.window.analysis_table.setItem(r_idx, 0, QTableWidgetItem(q_name))
                self.window.analysis_table.setItem(r_idx, 1, QTableWidgetItem(f"{corrects} / {totals}"))
                self.window.analysis_table.setItem(r_idx, 2, QTableWidgetItem(f"%{ratio:.1f}"))
                s_item = QTableWidgetItem(status)
                s_item.setForeground(QColor(s_color))
                self.window.analysis_table.setItem(r_idx, 3, s_item)
                
            self.window.distractor_table.setRowCount(0)
            for r_idx, q_idx in enumerate(sorted_questions):
                choices = q_choices.get(q_idx, {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "": 0})
                q_name = q_names[q_idx] if q_idx < len(q_names) else f"Soru {q_idx + 1}"
                c_ans = ""
                gr_keys = list(cached_keys.values())
                if gr_keys and q_idx < len(gr_keys[0]):
                    c_ans = gr_keys[0][q_idx][0]
                self.window.distractor_table.insertRow(r_idx)
                self.window.distractor_table.setItem(r_idx, 0, QTableWidgetItem(q_name))
                self.window.distractor_table.setItem(r_idx, 1, QTableWidgetItem(str(choices["A"])))
                self.window.distractor_table.setItem(r_idx, 2, QTableWidgetItem(str(choices["B"])))
                self.window.distractor_table.setItem(r_idx, 3, QTableWidgetItem(str(choices["C"])))
                self.window.distractor_table.setItem(r_idx, 4, QTableWidgetItem(str(choices["D"])))
                self.window.distractor_table.setItem(r_idx, 5, QTableWidgetItem(str(choices["E"])))
                self.window.distractor_table.setItem(r_idx, 6, QTableWidgetItem(str(choices[""])))
                self.window.distractor_table.setItem(r_idx, 7, QTableWidgetItem(c_ans))
                
            import matplotlib.pyplot as plt
            plt.figure(figsize=(6, 4), facecolor="#1a1a1a")
            ax = plt.axes()
            ax.set_facecolor("#252526")
            ax.hist(scores, bins=min(10, max(2, len(scores))), color="#1e88e5", edgecolor="#1a1a1a", alpha=0.9)
            ax.set_title("Sınav Puan Dağılımı", fontsize=11, fontweight="bold", color="#ffffff", pad=10)
            ax.set_xlabel("Puan", fontsize=9, color="#d0d0d0")
            ax.set_ylabel("Öğrenci Sayısı", fontsize=9, color="#d0d0d0")
            ax.tick_params(colors="#d0d0d0", labelsize=8)
            ax.grid(axis="y", linestyle="--", alpha=0.3, color="#555555")
            for spine in ax.spines.values():
                spine.set_color("#333333")
            plt.tight_layout()
            chart_dir = self.get_resource_path("temp_images")
            os.makedirs(chart_dir, exist_ok=True)
            chart_path = os.path.join(chart_dir, f"chart_{selected_exam}.png")
            plt.savefig(chart_path, dpi=150, facecolor="#1a1a1a")
            plt.close()
            self.window.lbl_analysis_chart.setPixmap(QPixmap(chart_path))
            self.window.log_list.addItem("İstatistiksel ve çeldirici analiz tamamlandı.")
            self.window.log_list.scrollToBottom()
        except Exception as e:
            self.window.log_list.addItem(f"Analiz Hatası: {str(e)}")
            self.window.log_list.scrollToBottom()
    def export_excel_report(self):
        selected_exam = self.window.combo_analysis_exam.currentText()
        if not selected_exam:
            self.window.log_list.addItem("Lütfen önce analiz edilecek sınavı seçin.")
            self.window.log_list.scrollToBottom()
            return
            
        csv_path = self.get_resource_path(f"sonuclar_{selected_exam}.csv")
        if not os.path.exists(csv_path):
            self.window.log_list.addItem(f"Dışa aktarılacak veri bulunamadı ({selected_exam} için CSV yok).")
            self.window.log_list.scrollToBottom()
            return
            
        try:
            import pandas as pd
            df_csv = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")
            if df_csv.empty:
                self.window.log_list.addItem("CSV dosyasında veri bulunamadı.")
                self.window.log_list.scrollToBottom()
                return
                
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(self.window, "Excel Raporunu Kaydet", f"{selected_exam}_Analiz_Raporu.xlsx", "Excel Dosyaları (*.xlsx)")
            if not file_path:
                return
                
            tpl = self.templates.get(selected_exam, {})
            answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
            exam_type = tpl.get("exam_type", "single")
            
            q_names = []
            if not answers_blocks:
                ans_cols = len(df_csv.columns) - 7
                q_names = [f"Soru {i + 1}" for i in range(ans_cols)]
            else:
                for b in answers_blocks:
                    dname = b.get("name", "Cevap")
                    q_start = b.get("q_start", 1)
                    for i in range(b.get("q_count", 10)):
                        if exam_type == "single":
                            q_names.append(f"Soru {q_start + i}")
                        else:
                            q_names.append(f"{dname} {q_start + i}")
                            
            csv_cols = list(df_csv.columns)
            for i, q_name in enumerate(q_names):
                col_idx = 7 + i
                if col_idx < len(csv_cols):
                    csv_cols[col_idx] = q_name
            df_csv.columns = csv_cols
            
            q_success = {}
            q_total = {}
            q_choices = {}
            cached_keys = {}
            
            def get_full_key(gr_id):
                if not answers_blocks or exam_type == "single":
                    return self.load_answer_key_detailed(gr_id)
                full_key = []
                for b in answers_blocks:
                    dname = b.get("name", "Cevap")
                    b_key = self.load_answer_key_detailed(gr_id, dname)
                    if b_key:
                        full_key.extend(b_key)
                    else:
                        full_key.extend([("", 1.0)] * b.get("q_count", 10))
                return full_key
                
            for _, row in df_csv.iterrows():
                gr = str(row["Grup"])
                if gr not in cached_keys:
                    cached_keys[gr] = get_full_key(gr)
                key = cached_keys[gr]
                if not key:
                    continue
                for idx, correct_tuple in enumerate(key):
                    correct_ans = correct_tuple[0]
                    student_ans = ""
                    if 7 + idx < len(row):
                        student_ans = str(row.iloc[7 + idx]).strip().upper()
                    if student_ans == "-" or student_ans == "NAN" or student_ans == "nan":
                        student_ans = ""
                    if student_ans == correct_ans and student_ans != "":
                        q_success[idx] = q_success.get(idx, 0) + 1
                    q_total[idx] = q_total.get(idx, 0) + 1
                    if idx not in q_choices:
                        q_choices[idx] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "": 0}
                    if student_ans in q_choices[idx]:
                        q_choices[idx][student_ans] += 1
                    else:
                        q_choices[idx][""] += 1
                        
            q_rows = []
            for idx in sorted(q_total.keys()):
                corrects = q_success.get(idx, 0)
                totals = q_total[idx]
                ratio = (corrects / totals * 100.0) if totals > 0 else 0
                status = "Kolay" if ratio > 70 else "Orta" if ratio > 40 else "Zor"
                q_name = q_names[idx] if idx < len(q_names) else f"Soru {idx + 1}"
                q_rows.append({
                    "Soru No": q_name,
                    "Doğru Sayısı": corrects,
                    "Toplam Katılımcı": totals,
                    "Başarı Oranı (%)": round(ratio, 1),
                    "Zorluk Derecesi": status
                })
            df_q_analysis = pd.DataFrame(q_rows)
            
            c_rows = []
            for idx in sorted(q_total.keys()):
                choices = q_choices.get(idx, {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "": 0})
                q_name = q_names[idx] if idx < len(q_names) else f"Soru {idx + 1}"
                c_ans = ""
                gr_keys = list(cached_keys.values())
                if gr_keys and len(gr_keys) > 0:
                    first_key = gr_keys[0]
                    if idx < len(first_key):
                        c_ans = first_key[idx][0]
                c_rows.append({
                    "Soru No": q_name,
                    "A Seçeneği (Adet)": choices["A"],
                    "B Seçeneği (Adet)": choices["B"],
                    "C Seçeneği (Adet)": choices["C"],
                    "D Seçeneği (Adet)": choices["D"],
                    "E Seçeneği (Adet)": choices["E"],
                    "Boş Bırakan (Adet)": choices[""],
                    "Doğru Cevap": c_ans
                })
            df_distractors = pd.DataFrame(c_rows)
            
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                df_csv.to_excel(writer, sheet_name="Öğrenci Sonuçları", index=False)
                df_q_analysis.to_excel(writer, sheet_name="Soru Analizi", index=False)
                df_distractors.to_excel(writer, sheet_name="Çeldirici Analizi", index=False)
                
            self.window.log_list.addItem(f"EXCEL RAPORU OLUŞTURULDU: {file_path}")
            self.window.log_list.scrollToBottom()
            os.startfile(file_path)
        except Exception as e:
            self.window.log_list.addItem(f"Excel Aktarma Hatası: {str(e)}")
            self.window.log_list.scrollToBottom()
    def load_templates(self):
        try:
            import json
            self.templates_file = self.get_resource_path("sablonlar.json")
            self.templates = {}
            if os.path.exists(self.templates_file):
                try:
                    with open(self.templates_file, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                    for name, data in raw_data.items():
                        if "blocks" in data and len(data["blocks"]) > 0 and "type" in data["blocks"][0]:
                            self.templates[name] = data
                            continue
                        print(f"Migrating old template: {name}")
                        migrated = {"blocks": []}
                        sol = data.get("sol", 103)
                        ust = data.get("ust", 483)
                        sag = data.get("sag", 1184)
                        alt = data.get("alt", 1956)
                        grid_rows = data.get("grid_rows", 64)
                        grid_cols = data.get("grid_cols", 44)
                        sik_sayisi = data.get("sik_sayisi", 5)
                        H = 2000.0
                        W = 1400.0
                        sgen = (sag - sol) / grid_cols
                        syuk = (alt - ust) / grid_rows
                        std = data.get("ogrenci_no", {})
                        if std:
                            sc = std.get("col_start", 0)
                            scc = std.get("col_count", 12)
                            sr = std.get("row_start", 0)
                            src = std.get("row_count", 10)
                            bx1 = sol + sc * sgen
                            bx2 = sol + (sc + scc) * sgen
                            by1 = ust + sr * syuk
                            by2 = ust + (sr + src) * syuk
                        migrated["blocks"].append({"name": "Öğrenci No", "type": "student_no", "x1": max(0.0, min(1.0, bx1 / W)), "y1": max(0.0, min(1.0, by1 / H)), "x2": max(0.0, min(1.0, bx2 / W)),
    
    "y2": max(0.0, min(1.0, by2 / H)),
    
    "rows": src, "cols": scc, "zero_pos": "sonda"})
                        bk = data.get("kitapcik", {})
                        if bk:
                            sc = bk.get("col_start", 14)
                            scc = bk.get("col_count", 5)
                            sr = bk.get("row_start", 0)
                            src = bk.get("row_count", 1)
                            bx1 = sol + sc * sgen
                            bx2 = sol + (sc + scc) * sgen
                            by1 = ust + sr * syuk
                            by2 = ust + (sr + src) * syuk
                        migrated["blocks"].append({"name": "Kitapçık Grubu", "type": "booklet", "x1": max(0.0, min(1.0, bx1 / W)),
    
    "y1": max(0.0, min(1.0, by1 / H)),
    
    "x2": max(0.0, min(1.0, bx2 / W)),
    
    "y2": max(0.0, min(1.0, by2 / H)),
    
    "rows": src, "cols": scc})
                        for idx, b in enumerate(data.get("bloklar", [])):
                            qstart = b.get("q_start", 1)
                            qcount = b.get("q_count", 0)
                            col_start = b.get("col_start", 0)
                            row_start = b.get("row_start", 0)
                            bx1 = sol + col_start * sgen
                            bx2 = sol + (col_start + sik_sayisi) * sgen
                            by1 = ust + row_start * syuk
                            by2 = ust + (row_start + qcount) * syuk
                            migrated["blocks"].append({"name": f"Cevaplar {qstart}-{qstart + qcount - 1}", "type": "answers", "x1": max(0.0, min(1.0, bx1 / W)), "y1": max(0.0, min(1.0, by1 / H)),
    
    "x2": max(0.0, min(1.0, bx2 / W)),
    
    "y2": max(0.0, min(1.0, by2 / H)),
    
    "rows": qcount, "cols": sik_sayisi, "q_start": qstart,
    
    "q_count": qcount, "opt_count": sik_sayisi})
                        open(self.templates_file, "r", encoding="utf-8")
                        self.templates[name] = migrated
                    if not self.templates:
                        self.templates = {"Varsayılan 60 Soruluk Form (3 Sütun)": {"blocks": [{"name": "Öğrenci No", "type": "student_no", "x1": 0.067, "y1": 0.237, "x2": 0.28, "y2": 0.354, "rows": 10, "cols": 12, "zero_pos": "sonda"},
    {"name": "Kitapçık Grubu", "type": "booklet",
    
    "x1": 0.315, "y1": 0.237, "x2": 0.404, "y2": 0.249, "rows": 1, "cols": 5},
    {"name": "Cevaplar 1-17", "type": "answers", "x1": 0.067, "y1": 0.377, "x2": 0.156, "y2": 0.575, "rows": 17, "cols": 5, "q_start": 1, "q_count": 17, "opt_count": 5},
    {"name": "Cevaplar 18-34", "type": "answers", "x1": 0.191, "y1": 0.377, "x2": 0.28, "y2": 0.575, "rows": 17, "cols": 5, "q_start": 18, "q_count": 17, "opt_count": 5},
    {"name": "Cevaplar 35-60", "type": "answers", "x1": 0.315, "y1": 0.272, "x2": 0.404, "y2": 0.575, "rows": 26, "cols": 5, "q_start": 35, "q_count": 26, "opt_count": 5}]}}
                    self.save_templates_to_file()
                    self.update_template_ui_lists()
                except:
                    pass
        except Exception as e:
            print(f"Şablon yükleme/göç hatası: {e}")
    
    def save_templates_to_file(self):
        import json
        try:
            with open(self.templates_file, "w", encoding="utf-8") as f:
                json.dump(self.templates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Şablon kaydetme hatası: {e}")
    def update_template_ui_lists(self):
        self.window.combo_templates.blockSignals(True); self.window.combo_templates.clear(); self.window.combo_templates.addItems(sorted(self.templates.keys()))
        
        self.window.combo_templates.blockSignals(False)
        
        self.window.combo_analysis_exam.blockSignals(True); self.window.combo_analysis_exam.clear()
        
        self.window.combo_analysis_exam.addItems(sorted(self.templates.keys())); self.window.combo_analysis_exam.blockSignals(False); self.window.template_list.blockSignals(True)
        
        self.window.template_list.clear()
        
        self.window.template_list.addItems(sorted(self.templates.keys())); self.window.template_list.blockSignals(False)
        last_tpl = self.config.get("Ayarlar", "SonSablon", sorted(self.templates.keys())[0])
        if last_tpl in self.templates:
            index = self.window.combo_templates.findText(last_tpl)
            if index >= 0:
                pass
            self.window.combo_templates.setCurrentIndex(index)
            idx_analysis = self.window.combo_analysis_exam.findText(last_tpl)
            if idx_analysis >= 0:
                self.window.combo_analysis_exam.blockSignals(True)
                self.window.combo_analysis_exam.setCurrentIndex(idx_analysis)
            self.window.combo_analysis_exam.blockSignals(False)
            self.apply_template(last_tpl)
    
    def apply_template(self, tpl_name):
        if tpl_name not in self.templates:
            return
            
        self.active_template_name = tpl_name
        self.csv_output = self.get_resource_path(f"sonuclar_{tpl_name}.csv")
        self.config.set("Ayarlar", "SonSablon", tpl_name)
        tpl = self.templates[tpl_name]
        
        exam_types = ["single", "multi"]
        exam_type = tpl.get("exam_type", "single")
        if exam_type in exam_types:
            e_idx = exam_types.index(exam_type)
            self.window.combo_exam_type.blockSignals(True)
            self.window.combo_exam_type.setCurrentIndex(e_idx)
            self.window.combo_exam_type.blockSignals(False)
            
        align_modes = ["none", "border_contour", "timing_marks"]
        mode = tpl.get("align_mode", "none")
        if mode in align_modes:
            idx = align_modes.index(mode)
            self.window.combo_align_mode.blockSignals(True)
            self.window.combo_align_mode.setCurrentIndex(idx)
            self.window.combo_align_mode.blockSignals(False)
            
        color_modes = ["gray", "red", "green", "blue"]
        c_mode = tpl.get("color_mode", "gray")
        if c_mode in color_modes:
            c_idx = color_modes.index(c_mode)
            self.window.combo_color_mode.blockSignals(True)
            self.window.combo_color_mode.setCurrentIndex(c_idx)
            self.window.combo_color_mode.blockSignals(False)
            
        self.window.t2_tabs.clear()
        self.t2_tables = {}
        answers_blocks = [b for b in tpl.get("blocks", []) if b.get("type") == "answers"]
        
        if not answers_blocks:
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Soru", "Şık", "Puan"])
            table.setRowCount(60)
            h = table.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(0, 60)
            h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            for i in range(60):
                it = QTableWidgetItem(f"S. {i + 1}")
                it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                table.setItem(i, 0, it)
                table.setItem(i, 1, QTableWidgetItem(""))
                spin = QDoubleSpinBox()
                spin.setRange(0, 100)
                spin.setValue(1.0)
                table.setCellWidget(i, 2, spin)
            self.window.t2_tabs.addTab(table, "Genel")
            self.t2_tables["Genel"] = table
            self.window.t2_table = table
            q_count = 60
            total_cols = q_count + 2
            headers = ["Numara & İsim", "Kitapçık"] + [str(i + 1) for i in range(q_count)]
        else:
            q_count = 0
            for b in answers_blocks:
                ders_adi = b.get("name", "Cevap")
                b_q_count = b.get("q_count", 10)
                q_start = b.get("q_start", 1)
                q_count = max(q_count, q_start + b_q_count - 1)
                table = QTableWidget()
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Soru", "Şık", "Puan"])
                table.setRowCount(b_q_count)
                h = table.horizontalHeader()
                h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(0, 60)
                h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
                for i in range(b_q_count):
                    q_num = q_start + i
                    it = QTableWidgetItem(f"S. {q_num}")
                    it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    table.setItem(i, 0, it)
                    table.setItem(i, 1, QTableWidgetItem(""))
                    spin = QDoubleSpinBox()
                    spin.setRange(0, 100)
                    spin.setValue(1.0)
                    table.setCellWidget(i, 2, spin)
                self.window.t2_tabs.addTab(table, ders_adi)
                self.t2_tables[ders_adi] = table
            first_ders = answers_blocks[0].get("name", "Cevap")
            self.window.t2_table = self.t2_tables[first_ders]
            
            headers = ["Numara & İsim", "Kitapçık"]
            for b in answers_blocks:
                ders_adi = b.get("name", "Cevap")
                b_q_count = b.get("q_count", 10)
                q_start = b.get("q_start", 1)
                is_generic = "cevap" in ders_adi.lower() or "soru" in ders_adi.lower() or "answer" in ders_adi.lower()
                for i in range(b_q_count):
                    q_num = q_start + i
                    if is_generic:
                        headers.append(str(q_num))
                    else:
                        headers.append(f"{ders_adi} {q_num}")
            total_cols = len(headers)
            
        self.window.result_table.setColumnCount(total_cols)
        self.window.result_table.setHorizontalHeaderLabels(headers)
        self.window.result_table.setColumnWidth(0, 200)
        for i in range(1, total_cols):
            self.window.result_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            
        self.load_saved_answer_keys()
        self.live_refresh()
        
        if self.current_image_path and os.path.exists(self.current_image_path):
            img_bgr = cv2.imdecode(np.fromfile(self.current_image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img_bgr is not None:
                self.update_student_info_preview(img_bgr)
    def on_template_combo_changed(self):
        name = self.window.combo_templates.currentText()
        if name:
            self.apply_template(name)
    
    def on_template_list_changed(self):
        item = self.window.template_list.currentItem()
        if not item:
            pass
        
        name = item.text(); tpl = self.templates.get(name, {}); self.window.edit_tpl_name.setText(name); self.update_block_list_ui(tpl); exam_types = ["single", "multi"]; exam_type = tpl.get("exam_type", "single")
        if exam_type in exam_types:
            e_idx = exam_types.index(exam_type)
            self.window.combo_exam_type.blockSignals(True)
            self.window.combo_exam_type.setCurrentIndex(e_idx)
        self.window.combo_exam_type.blockSignals(False); align_modes = ["none", "border_contour", "timing_marks"]
        
        mode = tpl.get("align_mode", "none")
        if mode in align_modes:
            idx = align_modes.index(mode)
            self.window.combo_align_mode.blockSignals(True)
            self.window.combo_align_mode.setCurrentIndex(idx)
        
        self.window.combo_align_mode.blockSignals(False); color_modes = ["gray", "red", "green", "blue"]; c_mode = tpl.get("color_mode", "gray")
        if c_mode in color_modes:
            c_idx = color_modes.index(c_mode)
            self.window.combo_color_mode.blockSignals(True)
            self.window.combo_color_mode.setCurrentIndex(c_idx)
        
        self.window.combo_color_mode.blockSignals(False)
        if tpl.get("blocks"):
            pass
        self.window.list_tpl_blocks.setCurrentRow(0); self.refresh_tpl_editor_view()
    
    def new_template(self):
        import random; name = f"Yeni Şablon {random.randint(100, 999)}"
        self.templates[name] = {"blocks": [{"name": "Öğrenci No", "type": "student_no", "x1": 0.2, "y1": 0.2, "x2": 0.4, "y2": 0.4, "rows": 10, "cols": 12, "zero_pos": "sonda"}]}
        
        self.save_templates_to_file(); self.update_template_ui_lists(); index = self.window.template_list.findItems(name, Qt.MatchFlag.MatchExactly)
        if index:
            self.window.template_list.setCurrentItem(index[0])
    
    def delete_template(self):
        item = self.window.template_list.currentItem()
        if not item:
            pass
        
        name = item.text()
        if len(self.templates) <= 1:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self.window, "Uyarı", "En az bir adet şablon bulunmalıdır!")
        
        self.templates.pop(name); self.save_templates_to_file()
        
        self.update_template_ui_lists()
    
    def save_template_settings(self):
        name = self.window.edit_tpl_name.text().strip()
        if not name:
            return
        
        item = self.window.template_list.currentItem()
        old_name = item.text().strip() if item else name
        
        tpl = self.templates.get(old_name, {})
        if not tpl:
            tpl = {"blocks": []}
            
        align_modes = ["none", "border_contour", "timing_marks"]
        tpl["align_mode"] = align_modes[self.window.combo_align_mode.currentIndex()]
        
        color_modes = ["gray", "red", "green", "blue"]
        tpl["color_mode"] = color_modes[self.window.combo_color_mode.currentIndex()]
        
        exam_types = ["single", "multi"]
        tpl["exam_type"] = exam_types[self.window.combo_exam_type.currentIndex()]
        
        if old_name != name and old_name in self.templates:
            self.templates.pop(old_name)
            
        self.templates[name] = tpl
        
        self.save_templates_to_file(); self.update_template_ui_lists()
        
        index = self.window.template_list.findItems(name, Qt.MatchFlag.MatchExactly)
        if index:
            pass
        self.window.template_list.setCurrentItem(index[0]); cb_index = self.window.combo_templates.findText(name)
        
        if cb_index >= 0:
            self.window.combo_templates.setCurrentIndex(cb_index)
        self.apply_template(name)
        from PyQt6.QtWidgets import QMessageBox; QMessageBox.information(self.window, "Bilgi", "Şablon başarıyla kaydedildi!")
    
    def zoom_in(self):
        self.tpl_zoom_factor = min(4.0, (self.tpl_zoom_factor) + 0.25); self.window.lbl_tpl_zoom_level.setText(f"Zoom: %{int((self.tpl_zoom_factor) * 100)}"); self.refresh_tpl_editor_view()
    
    def zoom_out(self):
        self.tpl_zoom_factor = max(0.5, (self.tpl_zoom_factor) - 0.25); self.window.lbl_tpl_zoom_level.setText(f"Zoom: %{int((self.tpl_zoom_factor) * 100)}"); self.refresh_tpl_editor_view()
    
    def zoom_reset(self):
        self.tpl_zoom_factor = 1.0; self.window.lbl_tpl_zoom_level.setText("Zoom: %100"); self.refresh_tpl_editor_view()
        
    def read_zoom_in(self):
        self.read_zoom_factor = min(4.0, self.read_zoom_factor + 0.25)
        self.window.lbl_read_zoom_level.setText(f"Zoom: %{int(self.read_zoom_factor * 100)}")
        self.live_refresh()

    def read_zoom_out(self):
        self.read_zoom_factor = max(0.5, self.read_zoom_factor - 0.25)
        self.window.lbl_read_zoom_level.setText(f"Zoom: %{int(self.read_zoom_factor * 100)}")
        self.live_refresh()

    def read_zoom_reset(self):
        self.read_zoom_factor = 1.0
        self.window.lbl_read_zoom_level.setText("Zoom: %100")
        self.live_refresh()
    
    def refresh_tpl_editor_view(self):
        if self.current_image_path and os.path.exists(self.current_image_path):
            img_bgr = cv2.imdecode(np.fromfile(self.current_image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        else:
            img_bgr = np.ones((1000, 700, 3), dtype=np.uint8) * 40
            
        h, w = img_bgr.shape[:2]
        tpl_name = self.get_active_editing_template_name()
        
        color_mode = "gray"
        if tpl_name and tpl_name in self.templates:
            tpl = self.templates[tpl_name]
            color_mode = tpl.get("color_mode", "gray")
            
        if color_mode == "red":
            r_chan = img_bgr[:, :, 2]
            img_bgr = cv2.merge([r_chan, r_chan, r_chan])
        elif color_mode == "green":
            g_chan = img_bgr[:, :, 1]
            img_bgr = cv2.merge([g_chan, g_chan, g_chan])
        elif color_mode == "blue":
            b_chan = img_bgr[:, :, 0]
            img_bgr = cv2.merge([b_chan, b_chan, b_chan])
            
        if not tpl_name or tpl_name not in self.templates:
            pix = self.cv2_to_pixmap(img_bgr)
            zoom_w = int(self.display_width * self.tpl_zoom_factor)
            scaled = pix.scaledToWidth(zoom_w, Qt.TransformationMode.SmoothTransformation)
            self.window.tpl_image_display.setPixmap(scaled)
            self.window.tpl_image_display.setFixedSize(scaled.size())
            return
            
        tpl = self.templates[tpl_name]
        blocks = tpl.get("blocks", [])
        
        sel_item = self.window.list_tpl_blocks.currentItem()
        sel_block_name = sel_item.text() if sel_item else None
        
        for b in blocks:
            bx1 = int(b["x1"] * w)
            by1 = int(b["y1"] * h)
            bx2 = int(b["x2"] * w)
            by2 = int(b["y2"] * h)
            
            b_type = b.get("type", "answers")
            is_selected = (b.get("name") == sel_block_name)
            
            if is_selected:
                color = (0, 0, 255)
                thickness = 4
            else:
                if b_type == "student_no":
                    color = (255, 100, 100)
                elif b_type == "booklet":
                    color = (100, 255, 100)
                elif b_type == "align_border":
                    color = (0, 165, 255)
                elif b_type == "header_area":
                    color = (255, 0, 255)
                else:
                    color = (100, 255, 255)
                thickness = 2
                
            cv2.rectangle(img_bgr, (bx1, by1), (bx2, by2), color, thickness)
            cv2.putText(img_bgr, b.get("name", ""), (bx1, max(20, by1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            rows = b.get("rows", 10)
            cols = b.get("cols", 5)
            if b_type not in ("align_border", "header_area") and rows > 0 and cols > 0 and bx2 > bx1 and by2 > by1:
                row_h = (by2 - by1) / rows
                col_w = (bx2 - bx1) / cols
                
                for r in range(1, rows):
                    ly = int(by1 + r * row_h)
                    cv2.line(img_bgr, (bx1, ly), (bx2, ly), color, 1)
                for c in range(1, cols):
                    lx = int(bx1 + c * col_w)
                    cv2.line(img_bgr, (lx, by1), (lx, by2), color, 1)
                    
                for r in range(rows):
                    cy = int(by1 + (r + 0.5) * row_h)
                    for c in range(cols):
                        cx = int(bx1 + (c + 0.5) * col_w)
                        cv2.circle(img_bgr, (cx, cy), 4, color, -1)
                        
        pix = self.cv2_to_pixmap(img_bgr)
        zoom_w = int(self.display_width * self.tpl_zoom_factor)
        scaled = pix.scaledToWidth(zoom_w, Qt.TransformationMode.SmoothTransformation)
        self.window.tpl_image_display.setPixmap(scaled)
        self.window.tpl_image_display.setFixedSize(scaled.size())
    def add_tpl_block(self):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates:
            self.window.log_list.addItem("Lütfen önce bir şablon seçin veya oluşturun.")
            self.window.log_list.scrollToBottom()
            return
            
        tpl = self.templates[tpl_name]
        if "blocks" not in tpl:
            tpl["blocks"] = []
            
        import random
        block_name = f"Blok {random.randint(100, 999)}"
        new_block = {
            "name": block_name,
            "type": "answers",
            "x1": 0.2, "y1": 0.2, "x2": 0.4, "y2": 0.4,
            "rows": 10, "cols": 5,
            "q_start": 1, "q_count": 10, "opt_count": 5
        }
        tpl["blocks"].append(new_block)
        self.update_block_list_ui(tpl)
        
        items = self.window.list_tpl_blocks.findItems(block_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.window.list_tpl_blocks.setCurrentItem(items[0])
    def delete_tpl_block(self):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates: return
        
        sel_item = self.window.list_tpl_blocks.currentItem()
        if not sel_item: return
        
        block_name = sel_item.text()
        tpl = self.templates[tpl_name]
        
        tpl["blocks"] = [b for b in tpl.get("blocks", []) if b["name"] != block_name]
        self.update_block_list_ui(tpl)
        self.refresh_tpl_editor_view()
    def update_block_list_ui(self, tpl):
        self.window.list_tpl_blocks.blockSignals(True); self.window.list_tpl_blocks.clear()
        for b in tpl.get("blocks", []):
            self.window.list_tpl_blocks.addItem(b["name"])
        
        self.window.list_tpl_blocks.blockSignals(False)
    
    def on_tpl_block_selected(self):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates: return
        
        sel_item = self.window.list_tpl_blocks.currentItem()
        if not sel_item:
            self.window.prop_frame.setEnabled(False)
            return
            
        self.window.prop_frame.setEnabled(True)
        block_name = sel_item.text()
        tpl = self.templates[tpl_name]
        
        block = None
        for b in tpl.get("blocks", []):
            if b["name"] == block_name:
                block = b
                break
                
        if not block: return
        
        self.window.edit_block_name.blockSignals(True)
        self.window.combo_block_type.blockSignals(True)
        self.window.spin_block_rows.blockSignals(True)
        self.window.spin_block_cols.blockSignals(True)
        self.window.combo_block_zero_pos.blockSignals(True)
        self.window.spin_block_qstart.blockSignals(True)
        self.window.spin_block_qcount.blockSignals(True)
        self.window.spin_block_opt_count.blockSignals(True)
        
        self.window.edit_block_name.setText(block.get("name", ""))
        b_type = block.get("type", "answers")
        if b_type == "student_no":
            self.window.combo_block_type.setCurrentIndex(0)
            self.window.combo_block_zero_pos.setEnabled(True)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(True)
            self.window.spin_block_cols.setEnabled(True)
        elif b_type == "booklet":
            self.window.combo_block_type.setCurrentIndex(1)
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(True)
            self.window.spin_block_cols.setEnabled(True)
        elif b_type == "align_border":
            self.window.combo_block_type.setCurrentIndex(3)
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(False)
            self.window.spin_block_cols.setEnabled(False)
        elif b_type == "header_area":
            self.window.combo_block_type.setCurrentIndex(4)
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(False)
            self.window.spin_block_cols.setEnabled(False)
        else:
            self.window.combo_block_type.setCurrentIndex(2)
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(True)
            self.window.spin_block_qcount.setEnabled(True)
            self.window.spin_block_opt_count.setEnabled(True)
            self.window.spin_block_rows.setEnabled(True)
            self.window.spin_block_cols.setEnabled(True)
            
        self.window.spin_block_rows.setValue(block.get("rows", 10))
        self.window.spin_block_cols.setValue(block.get("cols", 5))
        zp = block.get("zero_pos", "sonda")
        if zp == "başta" or "bast" in str(zp).lower():
            self.window.combo_block_zero_pos.setCurrentIndex(1)
        else:
            self.window.combo_block_zero_pos.setCurrentIndex(0)
            
        self.window.spin_block_qstart.setValue(block.get("q_start", 1))
        self.window.spin_block_qcount.setValue(block.get("q_count", 10))
        self.window.spin_block_opt_count.setValue(block.get("opt_count", 5))
        self.window.lbl_block_coords.setText(f"Konum: ({block.get('x1', 0.0):.3f}, {block.get('y1', 0.0):.3f}) - ({block.get('x2', 0.0):.3f}, {block.get('y2', 0.0):.3f})")
        
        self.window.edit_block_name.blockSignals(False)
        self.window.combo_block_type.blockSignals(False)
        self.window.spin_block_rows.blockSignals(False)
        self.window.spin_block_cols.blockSignals(False)
        self.window.combo_block_zero_pos.blockSignals(False)
        self.window.spin_block_qstart.blockSignals(False)
        self.window.spin_block_qcount.blockSignals(False)
        self.window.spin_block_opt_count.blockSignals(False)
        self.refresh_tpl_editor_view()
    def on_block_prop_changed(self):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates: return
        
        sel_item = self.window.list_tpl_blocks.currentItem()
        if not sel_item: return
        
        block_name = sel_item.text()
        tpl = self.templates[tpl_name]
        
        block = None
        for b in tpl.get("blocks", []):
            if b["name"] == block_name:
                block = b
                break
                
        if not block: return
        
        idx = self.window.combo_block_type.currentIndex()
        if idx == 0:
            block["type"] = "student_no"
            block["zero_pos"] = "sonda" if self.window.combo_block_zero_pos.currentIndex() == 0 else "başta"
            self.window.combo_block_zero_pos.setEnabled(True)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(True)
            self.window.spin_block_cols.setEnabled(True)
        elif idx == 1:
            block["type"] = "booklet"
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(True)
            self.window.spin_block_cols.setEnabled(True)
        elif idx == 3:
            block["type"] = "align_border"
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(False)
            self.window.spin_block_cols.setEnabled(False)
        elif idx == 4:
            block["type"] = "header_area"
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(False)
            self.window.spin_block_qcount.setEnabled(False)
            self.window.spin_block_opt_count.setEnabled(False)
            self.window.spin_block_rows.setEnabled(False)
            self.window.spin_block_cols.setEnabled(False)
        else:
            block["type"] = "answers"
            self.window.combo_block_zero_pos.setEnabled(False)
            self.window.spin_block_qstart.setEnabled(True)
            self.window.spin_block_qcount.setEnabled(True)
            self.window.spin_block_opt_count.setEnabled(True)
            self.window.spin_block_rows.setEnabled(True)
            self.window.spin_block_cols.setEnabled(True)
            block["q_start"] = self.window.spin_block_qstart.value()
            block["q_count"] = self.window.spin_block_qcount.value()
            block["opt_count"] = self.window.spin_block_opt_count.value()
            self.window.spin_block_rows.blockSignals(True)
            self.window.spin_block_rows.setValue(block["q_count"])
            self.window.spin_block_rows.blockSignals(False)
            self.window.spin_block_cols.blockSignals(True)
            self.window.spin_block_cols.setValue(block["opt_count"])
            self.window.spin_block_cols.blockSignals(False)
            
        block["rows"] = self.window.spin_block_rows.value()
        block["cols"] = self.window.spin_block_cols.value()
        self.refresh_tpl_editor_view()
    def on_block_name_changed(self, text):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates: return
        
        sel_item = self.window.list_tpl_blocks.currentItem()
        if not sel_item: return
        
        old_name = sel_item.text()
        new_name = text.strip()
        if not new_name or old_name == new_name: return
        
        tpl = self.templates[tpl_name]
        for b in tpl.get("blocks", []):
            if b["name"] == new_name:
                return
                
        for b in tpl.get("blocks", []):
            if b["name"] == old_name:
                b["name"] = new_name
                break
                
        self.window.list_tpl_blocks.blockSignals(True)
        sel_item.setText(new_name)
        self.window.list_tpl_blocks.blockSignals(False)
    def on_align_mode_changed(self):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates: return
        align_modes = ["none", "border_contour", "timing_marks"]
        idx = self.window.combo_align_mode.currentIndex()
        self.templates[tpl_name]["align_mode"] = align_modes[idx]
    def on_tpl_color_mode_changed(self):
        tpl_name = self.get_active_editing_template_name()
        if not tpl_name or tpl_name not in self.templates: return
        color_modes = ["gray", "red", "green", "blue"]
        idx = self.window.combo_color_mode.currentIndex()
        if 0 <= idx < len(color_modes):
            self.templates[tpl_name]["color_mode"] = color_modes[idx]
            self.refresh_tpl_editor_view()
    def load_tpl_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self.window, "Şablon Arka Plan Resmi Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.current_image_path = file_path
            self.refresh_tpl_editor_view()
    
    def run(self):
        self.window.show(); sys.exit(self.app.exec())


if __name__ == "__main__":
    OptikApp().run()
