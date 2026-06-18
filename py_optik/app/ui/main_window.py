import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QScrollArea, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QFrame, QSlider, QProgressBar, QSpinBox, QLineEdit, QRubberBand,
                             QTabWidget, QDoubleSpinBox, QSizePolicy, QFormLayout, QComboBox, QGroupBox)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect
from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QMouseEvent

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.mouse_pos = QPoint()
        self.is_drawing = False
        self.mouse_in = False
        self.parent_app = None
        self.is_tpl_editor = False
        self.setMouseTracking(True)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.mouse_in = True
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.mouse_in = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.mouse_pos = event.pos()
            self.is_drawing = True
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        self.mouse_pos = event.pos()
        if self.is_drawing and not self.origin.isNull():
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False
            self.origin = QPoint()
            self.update()
            rect = self.rubber_band.geometry()
            if rect.width() > 10 and rect.height() > 10:
                if self.parent_app:
                    if self.is_tpl_editor:
                        self.parent_app.on_tpl_rect_drawn(rect)
                    else:
                        self.parent_app.on_manual_rect_drawn(rect)
            self.rubber_band.hide()

    def paintEvent(self, event):
        super().paintEvent(event)
        # Büyüteç sadece şablon editöründeyken, fare üzerindeyken ve çizim yapılmıyorken (sol tık sürükleme yokken) çizilecek
        if hasattr(self, "mouse_in") and self.mouse_in and self.is_tpl_editor and not self.is_drawing and self.pixmap() and not self.mouse_pos.isNull():
            from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
            pix = self.pixmap()
            
            src_w = 40
            src_h = 40
            dest_w = 120
            dest_h = 120
            
            mx = self.mouse_pos.x()
            my = self.mouse_pos.y()
            
            crop_rect = QRect(mx - src_w // 2, my - src_h // 2, src_w, src_h)
            crop_rect = crop_rect.intersected(pix.rect())
            if crop_rect.width() > 0 and crop_rect.height() > 0:
                cropped = pix.copy(crop_rect)
                magnified = cropped.scaled(dest_w, dest_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
                
                off_x = -130 if mx > 150 else 30
                off_y = -130 if my > 150 else 30
                dest_x = mx + off_x
                dest_y = my + off_y
                
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.save()
                
                path = QPainterPath()
                path.addEllipse(dest_x, dest_y, dest_w, dest_h)
                painter.setClipPath(path)
                painter.drawPixmap(dest_x, dest_y, magnified)
                painter.restore()
                
                pen = QPen(QColor("#1e88e5"), 3)
                painter.setPen(pen)
                painter.drawEllipse(dest_x, dest_y, dest_w, dest_h)
                
                center_x = dest_x + dest_w // 2
                center_y = dest_y + dest_h // 2
                
                pen_cross = QPen(QColor(255, 0, 0, 180), 1)
                painter.setPen(pen_cross)
                painter.drawLine(center_x - 10, center_y, center_x + 10, center_y)
                painter.drawLine(center_x, center_y - 10, center_x, center_y + 10)
                painter.end()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optik Zeka - Optik Form Okuyucu Programı")
        self.setMinimumSize(1280, 850)
        
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.apply_theme()
        self.setup_ui()
        self.showMaximized()
        
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a1a; }
            QWidget { color: #d0d0d0; font-family: 'Segoe UI', Arial, sans-serif; }
            QListWidget { background-color: #252526; border: 1px solid #333; color: #aaa; font-size: 11px; }
            QPushButton { background-color: #333; border: 1px solid #444; color: white; padding: 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #444; border: 1px solid #1e88e5; }
            QTableWidget { background-color: #181818; gridline-color: #333; color: #ffffff; font-size: 11px; }
            QHeaderView::section { background-color: #2d2d2d; color: #1e88e5; padding: 2px; border: 1px solid #111; font-size: 10px; }
            QSpinBox, QDoubleSpinBox { 
                background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 5px; font-size: 14px; 
                min-height: 28px;
            }
            QLineEdit { background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 5px; font-size: 12px; }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        top_layout = QHBoxLayout()
        
        # 1. Sol Panel
        left_panel = QVBoxLayout()
        lbl_belge = QLabel("📄 BELGELER")
        lbl_belge.setStyleSheet("font-weight: bold; font-size: 14px; color: #1e88e5;")
        left_panel.addWidget(lbl_belge)
        self.btn_open_pdf = QPushButton("📂 PDF YÜKLE")
        self.btn_open_folder = QPushButton("📁 KLASÖR AÇ")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 4px;
                text-align: center;
                height: 15px;
                font-size: 10px;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #1e88e5;
            }
        """)
        self.file_list = QListWidget()
        left_panel.addWidget(self.btn_open_pdf)
        left_panel.addWidget(self.btn_open_folder)
        left_panel.addWidget(self.progress_bar)
        left_panel.addWidget(self.file_list)
        top_layout.addLayout(left_panel, 1)
        
        # Sekmeler
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 12px 25px; font-weight: bold; font-size: 13px; }")
        
        self.setup_read_tab()
        self.setup_template_editor_tab()
        self.setup_key_tab()
        self.setup_student_tab()
        self.setup_analysis_tab()
        self.setup_settings_tab()
        self.setup_help_tab()
        
        top_layout.addWidget(self.tabs, 5)
        main_layout.addLayout(top_layout, 5)

    def setup_analysis_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Sınav Seçim Kutusu
        exam_layout = QHBoxLayout()
        lbl_select = QLabel("📊 Analiz Edilecek Sınavı Seçin:")
        lbl_select.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e88e5;")
        exam_layout.addWidget(lbl_select)
        self.combo_analysis_exam = QComboBox()
        self.combo_analysis_exam.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 5px; font-size: 13px; min-width: 250px;")
        exam_layout.addWidget(self.combo_analysis_exam)
        exam_layout.addStretch()
        layout.addLayout(exam_layout)
        layout.addSpacing(10)
        
        # Üst Özet Kartları
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)
        
        self.card_avg, self.lbl_stat_avg = self.create_stat_card("📊 Sınıf Ortalaması", "0.0", "#1e88e5")
        self.card_max, self.lbl_stat_max = self.create_stat_card("🥇 En Yüksek Puan", "0.0", "#4caf50")
        self.card_min, self.lbl_stat_min = self.create_stat_card("📉 En Düşük Puan", "0.0", "#f44336")
        self.card_count, self.lbl_stat_count = self.create_stat_card("👥 Katılımcı", "0", "#9c27b0")
        
        for c in [self.card_avg, self.card_max, self.card_min, self.card_count]:
            cards_layout.addWidget(c)
        
        layout.addLayout(cards_layout)
        layout.addSpacing(10)
        
        # Orta Kısım: Tablolar ve Grafik
        middle_layout = QHBoxLayout()
        
        # Sol Panel: Başarı ve Çeldirici Tabloları
        tables_panel = QVBoxLayout()
        
        lbl_succ = QLabel("🎯 SORU BAŞARI ORANLARI")
        lbl_succ.setStyleSheet("font-size: 13px; font-weight: bold; color: #aaa;")
        tables_panel.addWidget(lbl_succ)
        
        self.analysis_table = QTableWidget()
        self.analysis_table.setColumnCount(4)
        self.analysis_table.setHorizontalHeaderLabels(["Soru No", "Doğru Yapılma", "Başarı (%)", "Zorluk"])
        self.analysis_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.analysis_table.setStyleSheet("font-size: 11px; color: #fff;")
        self.analysis_table.setFixedHeight(220)
        tables_panel.addWidget(self.analysis_table)
        
        lbl_dist = QLabel("📊 ÇELDİRİCİ ANALİZİ (ŞIK DAĞILIMLARI)")
        lbl_dist.setStyleSheet("font-size: 13px; font-weight: bold; color: #aaa; margin-top: 10px;")
        tables_panel.addWidget(lbl_dist)
        
        self.distractor_table = QTableWidget()
        self.distractor_table.setColumnCount(8)
        self.distractor_table.setHorizontalHeaderLabels(["Soru", "A", "B", "C", "D", "E", "Boş", "D.Cevap"])
        self.distractor_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.distractor_table.setStyleSheet("font-size: 11px; color: #fff;")
        self.distractor_table.setFixedHeight(220)
        tables_panel.addWidget(self.distractor_table)
        
        middle_layout.addLayout(tables_panel, 3)
        
        # Sağ Panel: Başarı Grafiği Görselleştirme
        chart_panel = QVBoxLayout()
        lbl_chart = QLabel("📈 SINIF BAŞARI GRAFİĞİ")
        lbl_chart.setStyleSheet("font-size: 13px; font-weight: bold; color: #aaa;")
        chart_panel.addWidget(lbl_chart)
        
        self.lbl_analysis_chart = QLabel("Grafik oluşturulması için 'Verileri Yenile' butonuna tıklayın.")
        self.lbl_analysis_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_analysis_chart.setStyleSheet("background-color: #252526; border: 1px solid #1e88e5; border-radius: 8px; color: #888; font-size: 12px;")
        self.lbl_analysis_chart.setMinimumWidth(400)
        self.lbl_analysis_chart.setScaledContents(True)
        chart_panel.addWidget(self.lbl_analysis_chart)
        
        middle_layout.addLayout(chart_panel, 2)
        
        layout.addLayout(middle_layout)
        layout.addSpacing(10)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        self.btn_refresh_stats = QPushButton("🔄 VERİLERİ YENİLE VE ANALİZ ET")
        self.btn_refresh_stats.setStyleSheet("background-color: #1e88e5; font-weight: bold; height: 40px;")
        self.btn_export_excel = QPushButton("📊 DETAYLI EXCEL RAPORU OLUŞTUR")
        self.btn_export_excel.setStyleSheet("background-color: #2e7d32; font-weight: bold; height: 40px;")
        btn_layout.addWidget(self.btn_refresh_stats)
        btn_layout.addWidget(self.btn_export_excel)
        
        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "📊 ANALİZ")

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setMinimumHeight(130)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #252526;
                border: 2px solid {color};
                border-radius: 15px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        
        l = QVBoxLayout(card)
        l.setContentsMargins(10, 20, 10, 20)
        
        t_lbl = QLabel(title)
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_lbl.setStyleSheet("font-size: 14px; color: #bbb; font-weight: bold;")
        
        v_lbl = QLabel(value)
        v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_lbl.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {color};")
        
        l.addWidget(t_lbl)
        l.addWidget(v_lbl)
        return card, v_lbl

    def setup_student_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Sol Taraf: Liste ve Arama
        left_side = QVBoxLayout()
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Ara:"))
        self.edit_student_search = QLineEdit()
        self.edit_student_search.setPlaceholderText("İsim veya numara yazın...")
        search_layout.addWidget(self.edit_student_search)
        left_side.addLayout(search_layout)
        
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)
        self.db_table.setHorizontalHeaderLabels(["No", "Ad Soyad", "Birim", "Program"])
        self.db_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.db_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_side.addWidget(self.db_table)
        
        layout.addLayout(left_side, 3)
        
        # Sağ Taraf: İşlemler
        right_side = QVBoxLayout()
        right_side.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        form_panel = QFrame()
        form_panel.setFrameShape(QFrame.Shape.StyledPanel)
        form_panel.setStyleSheet("background-color: #222; border: 1px solid #1e88e5; border-radius: 4px; padding: 10px;")
        form_layout = QVBoxLayout(form_panel)
        
        self.edit_db_no = QLineEdit(); self.edit_db_no.setPlaceholderText("254605001")
        self.edit_db_name = QLineEdit(); self.edit_db_name.setPlaceholderText("Öğrenci Adı Soyadı")
        self.edit_db_birim = QLineEdit(); self.edit_db_birim.setPlaceholderText("Birim (Örn: MYO)")
        self.edit_db_prog = QLineEdit(); self.edit_db_prog.setPlaceholderText("Program (Örn: Bilgisayar)")
        
        form_layout.addWidget(QLabel("Öğrenci No:"))
        form_layout.addWidget(self.edit_db_no)
        form_layout.addWidget(QLabel("Ad Soyad:"))
        form_layout.addWidget(self.edit_db_name)
        form_layout.addWidget(QLabel("Birim:"))
        form_layout.addWidget(self.edit_db_birim)
        form_layout.addWidget(QLabel("Program:"))
        form_layout.addWidget(self.edit_db_prog)
        
        self.btn_db_add = QPushButton("➕ ÖĞRENCİ EKLE / GÜNCELLE")
        self.btn_db_add.setStyleSheet("background-color: #1e88e5; font-weight: bold;")
        self.btn_db_delete = QPushButton("🗑️ SEÇİLİYİ SİL")
        self.btn_db_delete.setStyleSheet("background-color: #c62828;")
        
        form_layout.addSpacing(10)
        form_layout.addWidget(self.btn_db_add)
        form_layout.addWidget(self.btn_db_delete)
        
        right_side.addWidget(form_panel)
        right_side.addSpacing(20)
        
        import_panel = QFrame()
        import_panel.setFrameShape(QFrame.Shape.StyledPanel)
        import_panel.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333; padding: 10px;")
        import_layout = QVBoxLayout(import_panel)
        
        self.btn_db_import = QPushButton("📊 EXCEL'DEN AKTAR (.xlsx)")
        self.btn_db_import.setStyleSheet("background-color: #2e7d32; font-weight: bold; height: 50px;")
        self.btn_db_clear = QPushButton("🧨 TÜM LİSTEYİ TEMİZLE")
        self.btn_db_clear.setStyleSheet("background-color: #424242; font-size: 10px;")
        
        import_layout.addWidget(self.btn_db_import)
        import_layout.addSpacing(5)
        import_layout.addWidget(self.btn_db_clear)
        
        right_side.addWidget(import_panel)
        right_side.addStretch()
        
        layout.addLayout(right_side, 1)
        self.tabs.addTab(tab, "👤 ÖĞRENCİ YÖNETİMİ")

    def setup_help_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(40, 40, 40, 40)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        
        content = QWidget()
        c_layout = QVBoxLayout(content)
        
        title = QLabel("🚀 OptikZeka v1.0 Kullanım Kılavuzu")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e88e5; margin-bottom: 20px;")
        c_layout.addWidget(title)
        
        guide = """
        <h3 style='color: #4caf50;'>1. Sınav Okuma Sitemi</h3>
        <ul>
            <li><b>PDF Yükle:</b> Optik formların bulunduğu PDF dosyasını seçin. Program sayfaları otomatik olarak resme dönüştürecektir.</li>
            <li><b>Analiz (Tuş: C):</b> Mevcut sayfa üzerindeki optik işaretleri okur. Öğrenci numarası ve cevapları anında tespit eder.</li>
            <li><b>Kaydet (Tuş: V):</b> Analiz sonucunu CSV dosyasına işler ve resim adını öğrenci numarasıyla günceller.</li>
        </ul>

        <h3 style='color: #1e88e5;'>2. Cevap Anahtarı Oluşturma</h3>
        <ul>
            <li>Cevap anahtarı sekmesine geçin, bir optik form okutun veya tabloyu elinizle doldurun.</li>
            <li><b>Puanlama:</b> Her sorunun puanını belirleyin. 'Hepsine Uygula' butonuyla tüm sorulara aynı puanı verebilirsiniz.</li>
            <li>Kaydettiğinizde 'cevap-1.txt' gibi dosyalar oluşur.</li>
        </ul>

        <h3 style='color: #ff9800;'>3. Öğrenci Yönetimi (Veritabanı)</h3>
        <ul>
            <li>Öğrencileri tek tek ekleyebilir veya <b>Excel (.xlsx)</b> üzerinden toplu yükleme yapabilirsiniz.</li>
            <li>Excel dosyanızda sütunlar şu sırada olmalıdır: <b>No, Ad Soyad, Birim, Program</b></li>
        </ul>

        <h3 style='color: #9c27b0;'>4. Klavye Kısayolları (Hızlı Mod)</h3>
        <ul>
            <li><b>Z / X:</b> Önceki / Sonraki fotoğrafa geçer.</li>
            <li><b>C:</b> Analiz yap.</li>
            <li><b>V:</b> Kaydet ve geç.</li>
            <li><b>B:</b> Manuel numara düzeltmek için Öğrenci No kutusuna odaklanır.</li>
        </ul>

        <p style='margin-top: 30px; font-style: italic; color: #888;'>İpucu: Eğer okuma hatalıysa 'Siyahlık' ve 'Doluluk' sürgüleriyle ince ayar yapabilirsiniz.</p>
        """
        
        lbl = QLabel(guide)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setStyleSheet("font-size: 15px; line-height: 1.6; color: #ccc;")
        c_layout.addWidget(lbl)
        c_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "💡 YARDIM")

    def setup_read_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Üst kırpıntı kaldırıldı, sağ tarafa dikey olarak konumlandırıldı
        self.student_info_preview = QLabel("Bilgi Önizleme\n(Şablonda 'İsim/Başlık Alanı'\nçizildiğinde burada gösterilir)")
        self.student_info_preview.setMinimumWidth(320)
        self.student_info_preview.setMaximumWidth(500)
        self.student_info_preview.setStyleSheet("background-color: #222; border: 2px solid #1e88e5; border-radius: 4px; color: #888; font-size: 11px;")
        self.student_info_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.student_info_preview.setScaledContents(False)
        
        middle_layout = QHBoxLayout()
        
        # Resim Alanı (Sol Taraf) ve Yakınlaştırma Seçenekleri
        left_panel = QVBoxLayout()
        
        # Yakınlaştırma / Uzaklaştırma Butonları
        read_zoom_layout = QHBoxLayout()
        self.btn_read_zoom_out = QPushButton("🔍➖ Uzaklaştır")
        self.btn_read_zoom_out.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; font-weight: bold; padding: 5px;")
        self.btn_read_zoom_reset = QPushButton("🔄 Sıfırla (100%)")
        self.btn_read_zoom_reset.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #777; font-weight: bold; padding: 5px;")
        self.btn_read_zoom_in = QPushButton("🔍➕ Yakınlaştır")
        self.btn_read_zoom_in.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; font-weight: bold; padding: 5px;")
        self.lbl_read_zoom_level = QLabel("Zoom: %100")
        self.lbl_read_zoom_level.setStyleSheet("color: #1e88e5; font-weight: bold; margin-left: 10px;")
        
        self.btn_preview_mode = QPushButton("👁️ Eşik Maskesi")
        self.btn_preview_mode.setCheckable(True)
        self.btn_preview_mode.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #f57c00; font-weight: bold; padding: 5px;")
        self.btn_preview_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        
        for btn in [self.btn_read_zoom_out, self.btn_read_zoom_reset, self.btn_read_zoom_in, self.btn_preview_mode]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
        read_zoom_layout.addWidget(self.btn_read_zoom_out)
        read_zoom_layout.addWidget(self.btn_read_zoom_reset)
        read_zoom_layout.addWidget(self.btn_read_zoom_in)
        read_zoom_layout.addWidget(self.lbl_read_zoom_level)
        read_zoom_layout.addWidget(self.btn_preview_mode)
        read_zoom_layout.addStretch()
        
        left_panel.addLayout(read_zoom_layout)
        
        # Resim Scroll Alanı
        self.scroll_area = QScrollArea()
        self.image_display = ClickableLabel() 
        self.image_display.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.scroll_area.setWidget(self.image_display)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #1a1a1a; border: none;")
        left_panel.addWidget(self.scroll_area)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(720)
        
        middle_layout.addWidget(left_widget)
        
        # Sağ Ayarlar Paneli
        settings_panel = QVBoxLayout()
        settings_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        info_panel = QFrame()
        info_panel.setStyleSheet("background-color: #222; border: 1px solid #1e88e5; border-radius: 4px; padding: 5px;")
        info_panel.setFixedWidth(300) 
        info_layout = QVBoxLayout(info_panel)
        self.edit_student_no = QLineEdit()
        
        student_name_layout = QHBoxLayout()
        self.lbl_student_name = QLabel("---")
        self.lbl_student_name.setStyleSheet("color: #1e88e5; font-weight: bold; font-size: 13px;")
        self.btn_select_student = QPushButton("🔍 Seç")
        self.btn_select_student.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_student.setStyleSheet("background-color: #2e7d32; color: white; border: none; border-radius: 3px; font-weight: bold; padding: 2px 8px;")
        self.btn_select_student.setFixedWidth(60)
        student_name_layout.addWidget(self.lbl_student_name, 1)
        student_name_layout.addWidget(self.btn_select_student, 0)
        
        self.lbl_score = QLabel("Puan: 0.0 ( 0D 0Y 0B )")
        self.lbl_score.setStyleSheet("color: #4caf50; font-weight: bold; font-size: 14px;")
        info_layout.addWidget(QLabel("Optik Şablonu:"))
        self.combo_templates = QComboBox()
        self.combo_templates.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 3px;")
        info_layout.addWidget(self.combo_templates)
        
        info_layout.addWidget(QLabel("Öğrenci No:"))
        info_layout.addWidget(self.edit_student_no)
        info_layout.addLayout(student_name_layout)
        info_layout.addWidget(self.lbl_score)
        settings_panel.addWidget(info_panel)
        
        settings_panel.addSpacing(10)
        
        calib_container = QVBoxLayout()
        self.spin_x, lx = self.create_spin("X Kayma:", -300, 1000, 0)
        self.spin_y, ly = self.create_spin("Y Kayma:", -300, 1000, 0)
        self.spin_rotate, lr = self.create_double_spin("Eğim:", -10.0, 10.0, 0.0, 0.1)
        self.spin_black, lb = self.create_spin("Siyahlık:", 0, 500, 180)
        self.spin_thresh, lt = self.create_spin("Doluluk:", 0, 500, 170)
        for l in [lx, ly, lr, lb, lt]: calib_container.addLayout(l)
        
        calib_widget = QWidget()
        calib_widget.setFixedWidth(300)
        calib_widget.setLayout(calib_container)
        settings_panel.addWidget(calib_widget)
        
        self.log_list = QListWidget()
        self.log_list.setFixedHeight(120); self.log_list.setFixedWidth(300)
        settings_panel.addWidget(QLabel("LOG Kaydı:"))
        settings_panel.addWidget(self.log_list)
        
        middle_layout.addLayout(settings_panel)
        middle_layout.addWidget(self.student_info_preview)
        layout.addLayout(middle_layout, 4)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Önceki")
        self.btn_next = QPushButton("Sonraki ▶")
        self.btn_read = QPushButton("🔍 ANALİZ ET (OKU)")
        self.btn_save = QPushButton("💾 SONUCU KAYDET")
        self.btn_report = QPushButton("📄 KARNE (TEK)")
        self.btn_mass_report = QPushButton("📚 TOPLU KARNE")
        
        for btn in [self.btn_prev, self.btn_next, self.btn_read, self.btn_save, self.btn_report, self.btn_mass_report]:
            btn.setFixedHeight(40); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
        self.btn_prev.setStyleSheet("background-color: #424242; font-weight: bold;")
        self.btn_next.setStyleSheet("background-color: #424242; font-weight: bold;")
        self.btn_read.setStyleSheet("background-color: #1e88e5; font-weight: bold;")
        self.btn_save.setStyleSheet("background-color: #2e7d32; font-weight: bold;")
        self.btn_report.setStyleSheet("background-color: #c62828; font-weight: bold;")
        self.btn_mass_report.setStyleSheet("background-color: #6a1b9a; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_prev, 1); btn_layout.addWidget(self.btn_next, 1)
        btn_layout.addWidget(self.btn_read, 2); btn_layout.addWidget(self.btn_save, 2)
        btn_layout.addWidget(self.btn_report, 1); btn_layout.addWidget(self.btn_mass_report, 2)
        layout.addLayout(btn_layout, 0)
        
        self.result_table = QTableWidget()
        self.setup_table()
        layout.addWidget(self.result_table, 2)
        
        self.tabs.addTab(tab, "📖 SINAV OKUMA")

    def setup_key_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        self.t2_scroll_area = QScrollArea()
        self.t2_image_display = ClickableLabel()
        self.t2_image_display.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.t2_scroll_area.setWidget(self.t2_image_display)
        self.t2_scroll_area.setWidgetResizable(True)
        self.t2_scroll_area.setFixedWidth(720)
        self.t2_scroll_area.setStyleSheet("background-color: #1a1a1a; border: none;")
        layout.addWidget(self.t2_scroll_area)
        
        settings = QVBoxLayout()
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Kitapçık Grubu:"))
        self.t2_lbl_group = QLabel("1")
        self.t2_lbl_group.setStyleSheet("font-weight: bold; color: #1e88e5; font-size: 16px;")
        header_layout.addWidget(self.t2_lbl_group); header_layout.addStretch()
        settings.addLayout(header_layout)
        
        bulk_layout = QHBoxLayout()
        bulk_layout.addWidget(QLabel("Tüm Puanlar:"))
        self.t2_spin_all_points = QDoubleSpinBox()
        self.t2_spin_all_points.setRange(0, 100); self.t2_spin_all_points.setValue(1.0); self.t2_spin_all_points.setSingleStep(0.25)
        self.btn_t2_apply_all = QPushButton("Hepsine Uygula")
        self.btn_t2_apply_all.setStyleSheet("background-color: #455a64; color: white; padding: 5px;")
        bulk_layout.addWidget(self.t2_spin_all_points); bulk_layout.addWidget(self.btn_t2_apply_all)
        settings.addLayout(bulk_layout)
        
        # Çoklu dersleri desteklemek için QTabWidget ekliyoruz
        self.t2_tabs = QTabWidget()
        self.t2_tabs.setStyleSheet("QTabBar::tab { padding: 5px 15px; font-weight: bold; font-size: 11px; }")
        settings.addWidget(self.t2_tabs)
        
        # Kod uyumluluğu için dummy t2_table referansı
        self.t2_table = QTableWidget()
        
        btns = QHBoxLayout()
        self.btn_t2_read = QPushButton("🔍 CEVAPLARI OKU")
        self.btn_t2_save = QPushButton("💾 CEVAP ANAHTARI OLUŞTUR")
        self.btn_t2_read.setStyleSheet("background-color: #1e88e5; font-weight: bold;"); self.btn_t2_save.setStyleSheet("background-color: #2e7d32; font-weight: bold;")
        self.btn_t2_read.setFixedHeight(40); self.btn_t2_save.setFixedHeight(40)
        btns.addWidget(self.btn_t2_read); btns.addWidget(self.btn_t2_save)
        settings.addLayout(btns)
        
        layout.addLayout(settings)
        self.tabs.addTab(tab, "✍️ CEVAP ANAHTARI")

    def setup_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        
        lbl = QLabel("⌨️ KLAVYE KISAYOLLARI")
        lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e88e5; margin-bottom: 20px;")
        layout.addWidget(lbl)
        
        # Split into two columns: Genel Kısayollar & Kalibrasyon Kısayolları
        columns_layout = QHBoxLayout()
        
        # Column 1: Genel Kısayollar
        col1 = QGroupBox("Genel Kısayollar")
        col1.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        col1_layout = QFormLayout(col1)
        col1_layout.setSpacing(15)
        
        self.edit_key_prev = QLineEdit("Z")
        self.edit_key_next = QLineEdit("X")
        self.edit_key_read = QLineEdit("C")
        self.edit_key_save = QLineEdit("V")
        self.edit_key_focus = QLineEdit("B")
        
        st = "font-size: 16px; font-weight: bold; height: 30px; width: 50px; text-align: center; border: 2px solid #333;"
        for e in [self.edit_key_prev, self.edit_key_next, self.edit_key_read, self.edit_key_save, self.edit_key_focus]:
            e.setStyleSheet(st); e.setAlignment(Qt.AlignmentFlag.AlignCenter); e.setMaxLength(1)

        col1_layout.addRow(QLabel("Önceki Fotoğraf:"), self.edit_key_prev)
        col1_layout.addRow(QLabel("Sonraki Fotoğraf:"), self.edit_key_next)
        col1_layout.addRow(QLabel("Analiz Et (Sınav):"), self.edit_key_read)
        col1_layout.addRow(QLabel("Sonucu Kaydet:"), self.edit_key_save)
        col1_layout.addRow(QLabel("Odaklanma (Öğr. No):"), self.edit_key_focus)
        
        columns_layout.addWidget(col1)
        
        # Column 2: Kalibrasyon Kısayolları
        col2 = QGroupBox("Kalibrasyon Kısayolları (Azalt / Arttır)")
        col2.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        col2_layout = QFormLayout(col2)
        col2_layout.setSpacing(15)
        
        self.edit_key_x_dec = QLineEdit("J")
        self.edit_key_x_inc = QLineEdit("L")
        self.edit_key_y_dec = QLineEdit("I")
        self.edit_key_y_inc = QLineEdit("K")
        self.edit_key_rot_dec = QLineEdit("U")
        self.edit_key_rot_inc = QLineEdit("O")
        self.edit_key_blk_dec = QLineEdit("N")
        self.edit_key_blk_inc = QLineEdit("M")
        self.edit_key_thr_dec = QLineEdit("G")
        self.edit_key_thr_inc = QLineEdit("H")
        
        calib_edits = [
            self.edit_key_x_dec, self.edit_key_x_inc,
            self.edit_key_y_dec, self.edit_key_y_inc,
            self.edit_key_rot_dec, self.edit_key_rot_inc,
            self.edit_key_blk_dec, self.edit_key_blk_inc,
            self.edit_key_thr_dec, self.edit_key_thr_inc
        ]
        for e in calib_edits:
            e.setStyleSheet(st); e.setAlignment(Qt.AlignmentFlag.AlignCenter); e.setMaxLength(1)
            
        def make_row_layout(e1, e2):
            h_layout = QHBoxLayout()
            h_layout.addWidget(e1)
            lbl_slash = QLabel("/")
            lbl_slash.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h_layout.addWidget(lbl_slash)
            h_layout.addWidget(e2)
            h_layout.addStretch()
            return h_layout
            
        col2_layout.addRow(QLabel("X Kayma (Geri/İleri):"), make_row_layout(self.edit_key_x_dec, self.edit_key_x_inc))
        col2_layout.addRow(QLabel("Y Kayma (Yukarı/Aşağı):"), make_row_layout(self.edit_key_y_dec, self.edit_key_y_inc))
        col2_layout.addRow(QLabel("Eğim (Azalt/Arttır):"), make_row_layout(self.edit_key_rot_dec, self.edit_key_rot_inc))
        col2_layout.addRow(QLabel("Siyahlık (Azalt/Arttır):"), make_row_layout(self.edit_key_blk_dec, self.edit_key_blk_inc))
        col2_layout.addRow(QLabel("Doluluk (Azalt/Arttır):"), make_row_layout(self.edit_key_thr_dec, self.edit_key_thr_inc))
        
        columns_layout.addWidget(col2)
        layout.addLayout(columns_layout)
        
        self.btn_save_shortcuts = QPushButton("💾 KISAYOLLARI KAYDET")
        self.btn_save_shortcuts.setFixedHeight(50)
        self.btn_save_shortcuts.setStyleSheet("background-color: #2e7d32; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.btn_save_shortcuts)
        
        layout.addStretch()
        self.tabs.addTab(tab, "⚙️ AYARLAR")

    def keyPressEvent(self, event):
        focused = self.focusWidget()
        if isinstance(focused, QLineEdit) and focused is not self.edit_student_no:
             # Eğer kullanıcı başka bir yazı kutusundaysa (ayarlar vb) kısayolu engelle
             super().keyPressEvent(event)
             return

        k = event.text().upper()
        if k == self.edit_key_prev.text().upper(): self.btn_prev.click()
        elif k == self.edit_key_next.text().upper(): self.btn_next.click()
        elif k == self.edit_key_read.text().upper(): self.btn_read.click()
        elif k == self.edit_key_save.text().upper(): self.btn_save.click()
        elif k == self.edit_key_focus.text().upper():
            self.edit_student_no.setFocus()
            self.edit_student_no.selectAll()
        elif k == self.edit_key_x_dec.text().upper():
            self.spin_x.setValue(self.spin_x.value() - 1)
        elif k == self.edit_key_x_inc.text().upper():
            self.spin_x.setValue(self.spin_x.value() + 1)
        elif k == self.edit_key_y_dec.text().upper():
            self.spin_y.setValue(self.spin_y.value() - 1)
        elif k == self.edit_key_y_inc.text().upper():
            self.spin_y.setValue(self.spin_y.value() + 1)
        elif k == self.edit_key_rot_dec.text().upper():
            self.spin_rotate.setValue(self.spin_rotate.value() - 0.10)
        elif k == self.edit_key_rot_inc.text().upper():
            self.spin_rotate.setValue(self.spin_rotate.value() + 0.10)
        elif k == self.edit_key_blk_dec.text().upper():
            self.spin_black.setValue(self.spin_black.value() - 1)
        elif k == self.edit_key_blk_inc.text().upper():
            self.spin_black.setValue(self.spin_black.value() + 1)
        elif k == self.edit_key_thr_dec.text().upper():
            self.spin_thresh.setValue(self.spin_thresh.value() - 1)
        elif k == self.edit_key_thr_inc.text().upper():
            self.spin_thresh.setValue(self.spin_thresh.value() + 1)
        else:
            super().keyPressEvent(event)

    def setup_table(self):
        self.result_table.setColumnCount(62)
        headers = ["Numara & Isim", "Kitapçık"] + [str(i+1) for i in range(60)]
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(4)
        self.result_table.setVerticalHeaderLabels(["Doğru Cevap", "Senin Cevabın", "Kitapçık Grubu", "Durum"])
        h = self.result_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.result_table.setColumnWidth(0, 200)
        for i in range(1, 62): h.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

    def create_spin(self, text, min_v, max_v, def_v):
        layout = QHBoxLayout()
        lbl = QLabel(text); lbl.setFixedWidth(80)
        spin = QSpinBox(); spin.setRange(min_v, max_v); spin.setValue(def_v)
        layout.addWidget(lbl); layout.addWidget(spin)
        return spin, layout

    def create_double_spin(self, text, min_v, max_v, def_v, step):
        layout = QHBoxLayout()
        lbl = QLabel(text); lbl.setFixedWidth(80)
        spin = QDoubleSpinBox(); spin.setRange(min_v, max_v); spin.setValue(def_v); spin.setSingleStep(step)
        layout.addWidget(lbl); layout.addWidget(spin)
        return spin, layout

    def setup_template_editor_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 1. Sol taraf: Şablon Listesi ve Yeni/Sil butonları
        left_side = QVBoxLayout()
        left_side.addWidget(QLabel("📋 MEVCUT ŞABLONLAR"))
        self.template_list = QListWidget()
        left_side.addWidget(self.template_list)
        
        self.btn_new_template = QPushButton("➕ YENİ ŞABLON OLUŞTUR")
        self.btn_new_template.setStyleSheet("background-color: #1e88e5; font-weight: bold;")
        self.btn_delete_template = QPushButton("🗑️ SEÇİLİ ŞABLONU SİL")
        self.btn_delete_template.setStyleSheet("background-color: #c62828; font-weight: bold;")
        
        left_side.addWidget(self.btn_new_template)
        left_side.addWidget(self.btn_delete_template)
        layout.addLayout(left_side, 2)
        
        # 2. Orta taraf: Şablon Resmi ve Mouse ile Çizim Alanı
        middle_side = QVBoxLayout()
        middle_side.addWidget(QLabel("🖼️ ŞABLON RESMİ (Çizmek için sağdan bir blok seçip mouse sürükleyin)"))
        
        self.tpl_scroll_area = QScrollArea()
        self.tpl_image_display = ClickableLabel()
        self.tpl_image_display.is_tpl_editor = True
        self.tpl_image_display.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.tpl_scroll_area.setWidget(self.tpl_image_display)
        self.tpl_scroll_area.setWidgetResizable(True)
        self.tpl_scroll_area.setStyleSheet("background-color: #1a1a1a; border: none;")
        
        # Yakınlaştırma / Uzaklaştırma Butonları
        zoom_layout = QHBoxLayout()
        self.btn_tpl_zoom_out = QPushButton("🔍➖ Uzaklaştır")
        self.btn_tpl_zoom_out.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #ff9800; font-weight: bold; padding: 5px;")
        self.btn_tpl_zoom_reset = QPushButton("🔄 Sıfırla (100%)")
        self.btn_tpl_zoom_reset.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #777; font-weight: bold; padding: 5px;")
        self.btn_tpl_zoom_in = QPushButton("🔍➕ Yakınlaştır")
        self.btn_tpl_zoom_in.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #ff9800; font-weight: bold; padding: 5px;")
        self.lbl_tpl_zoom_level = QLabel("Zoom: %100")
        self.lbl_tpl_zoom_level.setStyleSheet("color: #ff9800; font-weight: bold; margin-left: 10px;")
        
        zoom_layout.addWidget(self.btn_tpl_zoom_out)
        zoom_layout.addWidget(self.btn_tpl_zoom_reset)
        zoom_layout.addWidget(self.btn_tpl_zoom_in)
        zoom_layout.addWidget(self.lbl_tpl_zoom_level)
        zoom_layout.addStretch()
        
        middle_side.addLayout(zoom_layout)
        middle_side.addWidget(self.tpl_scroll_area)
        
        # Resim yükleme butonu (şablon için özel resim)
        self.btn_tpl_load_image = QPushButton("🖼️ ŞABLON ARKA PLAN RESMİ YÜKLE")
        self.btn_tpl_load_image.setStyleSheet("background-color: #455a64; font-weight: bold;")
        middle_side.addWidget(self.btn_tpl_load_image)
        
        layout.addLayout(middle_side, 5)
        
        # 3. Sağ taraf: Şablon Adı, Blok Listesi ve Blok Özellikleri
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("background-color: transparent; border: none;")
        
        right_widget = QWidget()
        right_side = QVBoxLayout(right_widget)
        right_side.setContentsMargins(0, 0, 10, 0)
        
        # Şablon adı
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Şablon Adı:"))
        self.edit_tpl_name = QLineEdit()
        self.edit_tpl_name.setPlaceholderText("Şablon Adı")
        name_layout.addWidget(self.edit_tpl_name)
        right_side.addLayout(name_layout)
        
        # Blok listesi
        right_side.addWidget(QLabel("🧩 ŞABLON BLOKLARI"))
        self.list_tpl_blocks = QListWidget()
        right_side.addWidget(self.list_tpl_blocks)
        
        # Blok Ekle / Sil Butonları
        block_btn_layout = QHBoxLayout()
        self.btn_tpl_add_block = QPushButton("➕ Blok Ekle")
        self.btn_tpl_add_block.setStyleSheet("background-color: #2e7d32; color: white;")
        self.btn_tpl_delete_block = QPushButton("🗑️ Blok Sil")
        self.btn_tpl_delete_block.setStyleSheet("background-color: #c62828; color: white;")
        block_btn_layout.addWidget(self.btn_tpl_add_block)
        block_btn_layout.addWidget(self.btn_tpl_delete_block)
        right_side.addLayout(block_btn_layout)
        
        # Blok Özellikleri Formu
        self.prop_frame = QFrame()
        self.prop_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.prop_frame.setStyleSheet("QFrame { background-color: #222; border: 1px solid #1e88e5; border-radius: 4px; } QFrame QLabel { border: none; background: transparent; }")
        prop_layout = QFormLayout(self.prop_frame)
        prop_layout.setSpacing(10)
        
        prop_layout.addRow(QLabel("<b>BLOK ÖZELLİKLERİ</b>"), QLabel(""))
        
        self.edit_block_name = QLineEdit()
        self.edit_block_name.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 3px;")
        prop_layout.addRow("Blok Adı:", self.edit_block_name)
        
        self.combo_block_type = QComboBox()
        self.combo_block_type.addItems(["Öğrenci No", "Kitapçık Grubu", "Cevaplar", "Çerçeve Alanı", "İsim/Başlık Alanı"])
        self.combo_block_type.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 3px;")
        prop_layout.addRow("Blok Tipi:", self.combo_block_type)
        
        self.spin_block_rows = QSpinBox()
        self.spin_block_rows.setRange(1, 150)
        self.spin_block_rows.setValue(10)
        prop_layout.addRow("Satır Sayısı:", self.spin_block_rows)
        
        self.spin_block_cols = QSpinBox()
        self.spin_block_cols.setRange(1, 150)
        self.spin_block_cols.setValue(10)
        prop_layout.addRow("Sütun Sayısı:", self.spin_block_cols)
        
        # Öğrenci No için Sıfırın Yeri
        self.combo_block_zero_pos = QComboBox()
        self.combo_block_zero_pos.addItems(["Sonda (1-9, 0)", "Başta (0-9)"])
        self.combo_block_zero_pos.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #1e88e5; padding: 3px;")
        prop_layout.addRow("Sıfırın Yeri (Öğr. No):", self.combo_block_zero_pos)
        
        # Cevaplar için başlangıç soru no
        self.spin_block_qstart = QSpinBox()
        self.spin_block_qstart.setRange(1, 200)
        self.spin_block_qstart.setValue(1)
        prop_layout.addRow("Başlangıç Soru No:", self.spin_block_qstart)
        
        # Cevaplar için soru sayısı (bu aslında row sayısı ile aynı olacak, otomatik eşleyebiliriz)
        self.spin_block_qcount = QSpinBox()
        self.spin_block_qcount.setRange(1, 150)
        self.spin_block_qcount.setValue(20)
        prop_layout.addRow("Soru Sayısı:", self.spin_block_qcount)
        
        # Cevaplar için seçenek/şık sayısı (bu aslında col sayısı ile aynı olacak)
        self.spin_block_opt_count = QSpinBox()
        self.spin_block_opt_count.setRange(2, 10)
        self.spin_block_opt_count.setValue(5)
        prop_layout.addRow("Şık Sayısı:", self.spin_block_opt_count)
        
        # Koordinat göstergesi
        self.lbl_block_coords = QLabel("Koordinat: Çizilmedi")
        self.lbl_block_coords.setStyleSheet("font-style: italic; color: #888;")
        prop_layout.addRow("Konum:", self.lbl_block_coords)
        
        right_side.addWidget(self.prop_frame)
        
        # Hizalama Ayarları Formu
        self.align_frame = QFrame()
        self.align_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.align_frame.setStyleSheet("QFrame { background-color: #222; border: 1px solid #ff9800; border-radius: 4px; } QFrame QLabel { border: none; background: transparent; }")
        align_layout = QFormLayout(self.align_frame)
        align_layout.setSpacing(10)
        
        align_layout.addRow(QLabel("<b>ŞABLON HİZALAMA AYARLARI</b>"), QLabel(""))
        
        self.combo_exam_type = QComboBox()
        self.combo_exam_type.addItems([
            "Tek Dersli Sınav",
            "Çoklu Dersli Sınav"
        ])
        self.combo_exam_type.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #ff9800; padding: 3px;")
        align_layout.addRow("Sınav Tipi:", self.combo_exam_type)
        
        self.combo_align_mode = QComboBox()
        self.combo_align_mode.addItems([
            "Klasik (Eğiklik Düzeltme)",
            "Dış Çerçeve Konturu (Word/PDF)",
            "Kılavuz Çizgileri (LGS/YKS/YGS)"
        ])
        self.combo_align_mode.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #ff9800; padding: 3px;")
        align_layout.addRow("Hizalama Tipi:", self.combo_align_mode)
        
        self.combo_color_mode = QComboBox()
        self.combo_color_mode.addItems([
            "Standart Gri (Varsayılan)",
            "Kırmızı Filtresi (Kırmızı/Turuncu formlar)",
            "Yeşil Filtresi (Yeşil formlar)",
            "Mavi Filtresi (Mavi formlar)"
        ])
        self.combo_color_mode.setStyleSheet("background-color: #2d2d2d; color: white; border: 1px solid #ff9800; padding: 3px;")
        align_layout.addRow("Renk Filtresi (Dropout):", self.combo_color_mode)
        
        right_side.addWidget(self.align_frame)
        
        # Şablon Kaydet Butonu
        self.btn_save_tpl_settings = QPushButton("💾 ŞABLON AYARLARINI KAYDET")
        self.btn_save_tpl_settings.setStyleSheet("background-color: #2e7d32; font-weight: bold; height: 45px;")
        right_side.addWidget(self.btn_save_tpl_settings)
        
        right_scroll.setWidget(right_widget)
        layout.addWidget(right_scroll, 3)
        
        self.tabs.addTab(tab, "📐 ŞABLON EDİTÖRÜ")
