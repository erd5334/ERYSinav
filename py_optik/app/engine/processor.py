import cv2
import numpy as np
import os

class OMREngine:
    def __init__(self):
        self.satirlar = []
        self.sutunlar = []

    @staticmethod
    def load_image(path, color_mode="gray"):
        """Resmi belirtilen renk filtresi moduna göre tek kanal (gri tonlamalı) olarak okur."""
        # UTF-8 Dosya yolu desteği için
        stream = open(path, "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        img_bgr = cv2.imdecode(numpyarray, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return None
            
        if color_mode == "red":
            return img_bgr[:, :, 2]  # Kırmızı kanalı (Kırmızı/Turuncu formlar için)
        elif color_mode == "green":
            return img_bgr[:, :, 1]  # Yeşil kanalı (Yeşil formlar için)
        elif color_mode == "blue":
            return img_bgr[:, :, 0]  # Mavi kanalı (Mavi formlar için)
        else:
            return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def binarize(image, threshold=127):
        """Resmi siyah-beyaza çevirir. Gelen resim zaten tek kanallı olmalı."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        return binary

    def get_coordinates(self, binary_img, sol, ust, sag, ak, syuk, sgen, x_off, y_off, black_val):
        # Güvenlik için sadece 2 boyut al
        if len(binary_img.shape) == 3:
            binary_img = cv2.cvtColor(binary_img, cv2.COLOR_BGR2GRAY)
            
        h, w = binary_img.shape[:2]
        sutunlar = []
        satirlar = []
        
        y_scan = int(ust + syuk + y_off)
        y_scan = max(0, min(h-1, y_scan))
        
        in_line = False
        p1 = 0
        for x in range(int(sol + 1.2 * sgen + x_off), min(int(sag + x_off), w)):
            if binary_img[y_scan, x] <= black_val:
                if not in_line:
                    p1 = x
                    in_line = True
            elif in_line:
                center = int((p1 + x) / 2)
                sutunlar.append(center)
                in_line = False

        x_scan = int(sol + 2 * sgen + x_off)
        x_scan = max(0, min(w-1, x_scan))
        
        in_line = False
        p1 = 0
        for y in range(int(ust + 1.5 * syuk + y_off), min(int(ak + y_off), h)):
            if binary_img[y, x_scan] <= black_val:
                if not in_line:
                    p1 = y
                    in_line = True
            elif in_line:
                center = int((p1 + y) / 2)
                satirlar.append(center)
                in_line = False

        sutunlar = self._filter_close_lines(sutunlar, sgen * 0.4)
        satirlar = self._filter_close_lines(satirlar, syuk * 0.4)
        return sutunlar, satirlar

    def _filter_close_lines(self, lines, threshold):
        if not lines: return []
        lines.sort()
        filtered = [lines[0]]
        for i in range(1, len(lines)):
            if lines[i] - filtered[-1] > threshold:
                filtered.append(lines[i])
        return filtered

    def scan_bubble(self, image, cx, cy, radius=5, threshold=170):
        # Güvenlik: ROI alırken de tek kanal olduğundan emin ol
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
        y_max, x_max = image.shape[:2]
        x1, x2 = max(0, cx - radius), min(x_max, cx + radius)
        y1, y2 = max(0, cy - radius), min(y_max, cy + radius)
        
        roi = image[y1:y2, x1:x2]
        if roi.size == 0: return False, 255
        
        avg_intensity = np.mean(roi)
        return avg_intensity < threshold, avg_intensity

    def scan_block_grid(self, binary_img, bx1, by1, bx2, by2, rows, cols, threshold=170):
        """
        Belirtilen piksel sınırları içindeki alanı satır ve sütun sayılarına göre eşit şekilde ızgaraya böler
        ve her bir kutucuğun doluluk durumunu tarar.
        """
        if len(binary_img.shape) == 3:
            binary_img = cv2.cvtColor(binary_img, cv2.COLOR_BGR2GRAY)
        h, w = binary_img.shape[:2]
        bx1 = max(0, min(w, int(bx1)))
        bx2 = max(0, min(w, int(bx2)))
        by1 = max(0, min(h, int(by1)))
        by2 = max(0, min(h, int(by2)))
        
        if rows <= 0 or cols <= 0 or bx2 <= bx1 or by2 <= by1:
            return []
            
        row_h = (by2 - by1) / rows
        col_w = (bx2 - bx1) / cols
        
        grid = []
        for r in range(rows):
            row_data = []
            cy = int(by1 + (r + 0.5) * row_h)
            for c in range(cols):
                cx = int(bx1 + (c + 0.5) * col_w)
                is_marked, val = self.scan_bubble(binary_img, cx, cy, radius=5, threshold=threshold)
                row_data.append((is_marked, val, cx, cy))
            grid.append(row_data)
        return grid

    def identify_student_no_dynamic(self, img_bgr, template, blk, thr):
        """Dinamik şablon üzerinden öğrenci numarası tespiti"""
        if not template or "blocks" not in template:
            return None
            
        std_block = None
        for b in template.get("blocks", []):
            if b.get("type") == "student_no" or "ogrenci" in b.get("name", "").lower() or "no" in b.get("name", "").lower():
                std_block = b
                break
                
        if not std_block:
            return None
            
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, blk, 255, cv2.THRESH_BINARY)
        
        bx1 = int(std_block["x1"] * w)
        by1 = int(std_block["y1"] * h)
        bx2 = int(std_block["x2"] * w)
        by2 = int(std_block["y2"] * h)
        
        rows = std_block.get("rows", 10)
        cols = std_block.get("cols", 10)
        zero_pos = std_block.get("zero_pos", "sonda") # "sonda" (1-9,0) or "başta" (0-9)
        
        grid = self.scan_block_grid(binary, bx1, by1, bx2, by2, rows, cols, threshold=thr)
        if not grid:
            return None
            
        okul_no = ""
        for c in range(cols):
            for r in range(rows):
                is_marked = grid[r][c][0]
                if is_marked:
                    if zero_pos == "başta" or "bast" in str(zero_pos).lower():
                        digit = str(r % 10)
                    else:
                        digit = str((r + 1) % 10)
                    okul_no += digit
                    break
        return okul_no if len(okul_no) > 0 else None

    def identify_student_no(self, img_bgr, d_sol, d_ust=None, d_sag=None, d_ak=None, blk=250, thr=170):
        """Hızlı öğrenci numarası tespiti (Dosya isimlendirme için, şablon veya eski koordinatları destekler)"""
        if isinstance(d_sol, dict):
            # İkinci parametre dict ise, bu şablondur!
            template = d_sol
            blk_val = d_ust if d_ust is not None else 250
            thr_val = d_sag if d_sag is not None else 170
            return self.identify_student_no_dynamic(img_bgr, template, blk_val, thr_val)
            
        # Geriye dönük eski tip koordinat uyumluluğu
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, blk, 255, cv2.THRESH_BINARY)
        syuk, sgen = (d_ak - d_ust) / 64, (d_sag - d_sol) / 44
        sut, sat = self.get_coordinates(binary, d_sol, d_ust, d_sag, d_ak, syuk, sgen, 0, 0, blk)
        
        if not sut or not sat: return None
        
        okul_no = ""
        for s in range(min(12, len(sut))):
            for r in range(min(10, len(sat))):
                if self.scan_bubble(binary, sut[s], sat[r], threshold=thr)[0]:
                    okul_no += str((r + 1) % 10)
                    break
        return okul_no if len(okul_no) > 0 else None

    def align_image(self, img_bgr, template):
        """
        Şablonun hizalama ayarlarına göre görseli döndürür, öteler ve ölçekler.
        """
        if not template or "blocks" not in template:
            return img_bgr
            
        align_mode = template.get("align_mode", "none")
        if align_mode == "none":
            return img_bgr
            
        # Hizalama bloğunu bul
        align_block = None
        for b in template.get("blocks", []):
            if b.get("type") == "align_border":
                align_block = b
                break
                
        if not align_block:
            # Hizalama bloğu yoksa hizalama yapamayız
            return img_bgr
            
        if align_mode == "border_contour":
            return self.align_by_border(img_bgr, align_block)
        elif align_mode == "timing_marks":
            return self.align_by_timing_marks(img_bgr, align_block)
            
        return img_bgr

    def align_by_border(self, img_bgr, align_block):
        """
        Görseldeki dış çerçeve konturunu bulur ve perspektif dönüşümüyle şablona hizalar.
        """
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr
        
        # Gürültüyü azaltmak için hafifçe bulanıklaştır ve ikili görsel yap
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img_bgr
            
        # Hedeflenen (tasarım) koordinatları
        ex1, ey1 = align_block["x1"] * w, align_block["y1"] * h
        ex2, ey2 = align_block["x2"] * w, align_block["y2"] * h
        expected_area = (ex2 - ex1) * (ey2 - ey1)
        expected_center = ((ex1 + ex2) / 2, (ey1 + ey2) / 2)
        
        best_cnt = None
        best_diff = float("inf")
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Çok küçük veya çok büyük konturları eliyoruz
            if area < 0.1 * expected_area or area > 5.0 * expected_area:
                continue
                
            # Kontur merkezini bul
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
            
            # Tasarım merkezi ile olan mesafe farkını bul
            dist = np.sqrt((cx - expected_center[0])**2 + (cy - expected_center[1])**2)
            
            # Alan farkı ve dikey mesafe oranına göre puanlama yap
            score = dist + abs(area - expected_area) / expected_area * 100
            
            # Yaklaşık dörtgen olması gerekiyor
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                if score < best_diff:
                    best_diff = score
                    best_cnt = approx
                    
        if best_cnt is None:
            return img_bgr
            
        # Dört köşeyi sıralayalım
        pts = best_cnt.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)] # Sol-Üst
        rect[3] = pts[np.argmax(s)] # Sağ-Alt
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)] # Sağ-Üst
        rect[2] = pts[np.argmax(diff)] # Sol-Alt
        
        # Hedef köşeler
        dst_pts = np.array([
            [ex1, ey1],
            [ex2, ey1],
            [ex1, ey2],
            [ex2, ey2]
        ], dtype="float32")
        
        try:
            M = cv2.getPerspectiveTransform(rect, dst_pts)
            warped = cv2.warpPerspective(img_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return warped
        except Exception:
            return img_bgr

    def align_by_timing_marks(self, img_bgr, align_block):
        """
        Sol kenardaki siyah kılavuz çizgilerini algılar ve 3 noktalı afine dönüşümüyle hizalar.
        """
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr
        
        # Kılavuz çizgilerinin aranacağı dikey şerit alanını belirliyoruz (15 piksel tolerans ile dar bir şerit)
        rx1 = int(max(0, align_block["x1"] * w - 15))
        rx2 = int(min(w, align_block["x2"] * w + 15))
        ry1 = int(max(0, align_block["y1"] * h - 15))
        ry2 = int(min(h, align_block["y2"] * h + 15))
        
        strip_roi = gray[ry1:ry2, rx1:rx2]
        if strip_roi.size == 0:
            return img_bgr
            
        # İkili görsel yapalım (kılavuz çizgileri siyahtır)
        _, thresh = cv2.threshold(strip_roi, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        # Kılavuz çizgilerinin beklenen boyutları
        min_w, max_w = 5, 100
        min_h, max_h = 3, 40
        
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            if min_w <= cw <= max_w and min_h <= ch <= max_h:
                # Gerçek resim koordinatlarına çeviriyoruz
                cx = rx1 + x + cw // 2
                cy = ry1 + y + ch // 2
                candidates.append((cx, cy))
                
        if len(candidates) < 3:
            return img_bgr
            
        # Gürültüyü (örneğin sağdaki harf kutularını) elemek için X koordinatına göre median filtresi uyguluyoruz
        xs = [c[0] for c in candidates]
        median_x = np.median(xs)
        centers = [c for c in candidates if abs(c[0] - median_x) <= 15]
        
        if len(centers) < 3:
            return img_bgr
            
        # Y koordinatına göre sırala
        centers.sort(key=lambda pt: pt[1])
        
        # En üstteki ve en alttaki kılavuz çizgileri
        top_x, top_y = centers[0]
        bot_x, bot_y = centers[-1]
        
        # Tasarım konumları
        design_center_x = int((align_block["x1"] + align_block["x2"]) / 2 * w)
        design_top_y = int(align_block["y1"] * h)
        design_bot_y = int(align_block["y2"] * h)
        
        src_pts = np.array([
            [top_x, top_y],
            [bot_x, bot_y],
            [top_x + w // 2, top_y]
        ], dtype="float32")
        
        dst_pts = np.array([
            [design_center_x, design_top_y],
            [design_center_x, design_bot_y],
            [design_center_x + w // 2, design_top_y]
        ], dtype="float32")
        
        try:
            M = cv2.getAffineTransform(src_pts, dst_pts)
            warped = cv2.warpAffine(img_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return warped
        except Exception:
            return img_bgr


